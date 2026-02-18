import requests
import logging
from odoo import _

_logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
except ImportError:
    _logger.warning("google.generativeai library not found. AI features will be disabled.")
    genai = None

try:
    import json
except ImportError:
    pass

def enrich_marketing(product):
    """
    Generates Marketing Content using Gemini AI.
    """
    api_key = product.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.gemini_api_key')
    model_name = product.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.gemini_model') or 'gemini-1.5-flash'
    
    if not api_key:
        _logger.warning("Gemini API Key missing.")
        return False

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    # Context Construction
    specs = "\n".join([f"- {line.attribute_id.name}: {', '.join(line.value_ids.mapped('name'))}" for line in product.attribute_line_ids])
    air_specs = f"\n[IMPORTANTE] Datos Técnicos Directos del Fabricante (Air Computers):\n{product.air_description_raw}" if product.air_description_raw else ""
    
    prompt = f"""
    Actúa como un Copywriter Experto en E-commerce de Hardware al estilo MercadoLibre Argentina.
    Producto: {product.name}
    Marca: {product.product_brand_id.name}
    
    Insumos para la redacción:
    {specs}
    {air_specs}

    TAREA:
    1. Genera un 'Friendly Name' SEO (Ej: 'Notebook HP 250 G9 i5 8GB SSD').
    2. Redacta una Descripción HTML con Storytelling, Emojis y lista de beneficios. Tono cercano y tecnológico.
    3. Genera 5 'Usage Tags' (Ej: 'Gaming', 'Oficina', 'Diseño').
    
    Devuelve un JSON con claves: 'seo_name', 'description_html', 'tags'.
    Do not use markdown code blocks. Just raw JSON.
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        # Clean markdown if present
        if content.startswith('```json'):
            content = content[7:-3]
        
        data = json.loads(content)
        
        # Apply changes
        enriched_html = data.get('description_html')
        
        # 1. Save to Backend (Always Safe)
        product.tec_enriched_description = enriched_html

        # 2. Save to Website (If module installed)
        if hasattr(product, 'website_description'):
            product.website_description = enriched_html
        
        # Tags logic (requires tag model)
        # tags = data.get('tags', [])
        # ... logic to create/assign tags ...

        return True

    except Exception as e:
        _logger.error(f"Gemini Enrichment Failed: {e}")
        
    return False
