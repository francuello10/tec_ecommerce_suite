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
    Generates Marketing Content using Gemini AI with dynamic focus.
    """
    ICP = product.env['ir.config_parameter'].sudo()
    api_key = ICP.get_param('tec_catalog_enricher.gemini_api_key')
    model_name = ICP.get_param('tec_catalog_enricher.gemini_model') or 'gemini-1.5-flash'
    
    if not api_key:
        _logger.warning("Gemini API Key missing.")
        return False

    # 1. Config & Prompt
    custom_prompt = ICP.get_param('tec_catalog_enricher.ai_custom_prompt')
    use_image = ICP.get_param('tec_catalog_enricher.ai_input_thumbnail')

    # 2. Build Dynamic Context
    input_data = []
    if ICP.get_param('tec_catalog_enricher.ai_input_brand') and product.product_brand_id:
        input_data.append(f"Marca: {product.product_brand_id.name}")
    
    if ICP.get_param('tec_catalog_enricher.ai_input_name'):
        input_data.append(f"Nombre Original: {product.name}")
        
    if ICP.get_param('tec_catalog_enricher.ai_input_description_air') and product.air_description_raw:
        input_data.append(f"Descripción Air: {product.air_description_raw}")

    if ICP.get_param('tec_catalog_enricher.ai_input_description_enrich'):
        specs = "\n".join([f"- {line.attribute_id.name}: {', '.join(line.value_ids.mapped('name'))}" for line in product.attribute_line_ids])
        if specs:
            input_data.append(f"Especificaciones Técnicas:\n{specs}")

    if ICP.get_param('tec_catalog_enricher.ai_input_category') and product.public_categ_ids:
        input_data.append(f"Categorías: {', '.join(product.public_categ_ids.mapped('name'))}")

    context_str = "\n".join(input_data)
    final_prompt = custom_prompt.format(inputs=context_str)

    # 3. AI Execution
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        contents = [final_prompt]
        
        # Multimodal: Image support
        if use_image and product.image_1920:
            import base64
            contents.append({
                "mime_type": "image/png", # Odoo stores as PNG/JPEG
                "data": product.image_1920 # product.image_1920 is base64
            })

        response = model.generate_content(contents)
        content = response.text.strip()
        
        # Clean markdown if present
        if content.startswith('```json'):
            content = content[7:-3]
        if content.endswith('```'):
            content = content[:-3]
        
        data = json.loads(content)
        
        # 4. Backup & Apply Changes
        # Backup original name only if not already backed up
        if not product.x_original_name:
            product.x_original_name = product.name

        # Update Name (SEO Friendly)
        new_name = data.get('seo_name')
        if new_name:
            product.name = new_name

        # Update Dual Descriptions
        marketing_html = data.get('marketing_html')
        technical_html = data.get('technical_html')
        
        if marketing_html:
            product.tec_marketing_description = marketing_html
            # Fallback for old field and website
            product.tec_enriched_description = marketing_html
            if hasattr(product, 'website_description'):
                product.website_description = marketing_html
        
        if technical_html:
            product.tec_technical_description = technical_html

        return True

    except Exception as e:
        _logger.error(f"Gemini Enrichment Failed: {e}")
        
    return False
