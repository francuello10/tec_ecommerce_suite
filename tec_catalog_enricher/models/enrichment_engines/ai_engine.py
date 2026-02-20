import requests
import logging
from odoo import _

_logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
except ImportError:
    _logger.warning("google.generativeai library not found. Gemini features will be disabled.")
    genai = None

try:
    import json
except ImportError:
    pass

# Keys that should NEVER be stored as dynamic product.attribute
# These are already handled by dedicated Odoo fields
ATTRIBUTE_BLACKLIST = {
    'marca', 'brand', 'fabricante', 'manufacturer',
    'sku', 'mpn', 'part number', 'part_number', 'código',
    'precio', 'price', 'cost', 'costo',
}

def enrich_marketing(product):
    """
    Generates Marketing Content using either Gemini AI or OpenAI (configurable).
    Provider is selected via 'tec_catalog_enricher.ai_provider' system parameter.
    """
    ICP = product.env['ir.config_parameter'].sudo()
    provider = ICP.get_param('tec_catalog_enricher.ai_provider', 'gemini')

    if provider == 'openai':
        return _enrich_with_openai(product, ICP)
    else:
        return _enrich_with_gemini(product, ICP)


def _build_context(product, ICP):
    """Builds the text context string from product fields, based on enabled inputs."""
    input_data = []

    if ICP.get_param('tec_catalog_enricher.ai_input_brand') and product.product_brand_id:
        input_data.append(f"Marca: {product.product_brand_id.name}")

    if ICP.get_param('tec_catalog_enricher.ai_input_name'):
        input_data.append(f"Nombre Original: {product.name}")

    if ICP.get_param('tec_catalog_enricher.ai_input_description_air') and product.air_description_raw:
        input_data.append(f"Descripción Air: {product.air_description_raw}")

    if ICP.get_param('tec_catalog_enricher.ai_input_description_enrich'):
        specs = "\n".join([
            f"- {line.attribute_id.name}: {', '.join(line.value_ids.mapped('name'))}"
            for line in product.attribute_line_ids
            if line.attribute_id.name.lower() not in ATTRIBUTE_BLACKLIST
        ])
        if specs:
            input_data.append(f"Especificaciones Técnicas:\n{specs}")

    if ICP.get_param('tec_catalog_enricher.ai_input_category') and product.public_categ_ids:
        input_data.append(f"Categorías: {', '.join(product.public_categ_ids.mapped('name'))}")

    return "\n".join(input_data)


def _apply_ai_response(product, data):
    """Applies parsed JSON response from any AI provider to the product."""
    # Backup original name only if not already backed up
    if not product.x_original_name:
        product.x_original_name = product.name

    # Update Name (SEO Friendly)
    new_name = data.get('seo_name')
    if new_name:
        product.name = new_name

    # Update Dual Descriptions
    marketing_html = data.get('marketing_description') or data.get('marketing_html')
    technical_html = data.get('technical_html')

    if marketing_html:
        product.tec_marketing_description = marketing_html
        product.tec_enriched_description = marketing_html
        if hasattr(product, 'website_description'):
            product.website_description = marketing_html

    if technical_html:
        product.tec_technical_description = technical_html

    # Process Dynamic Attributes (Faceted Search) - skipping blacklisted keys
    try:
        with product.env.cr.savepoint():
            attributes_data = data.get('attributes', {})
            if attributes_data and isinstance(attributes_data, dict):
                Attribute = product.env['product.attribute']
                AttributeValue = product.env['product.attribute.value']
                AttributeLine = product.env['product.template.attribute.line']

                for attr_name, attr_val in attributes_data.items():
                    if not attr_name or not attr_val:
                        continue

                    attr_name_clean = str(attr_name).strip()

                    # Skip any "Marca", "Brand" etc. - they belong to product_brand_id
                    if attr_name_clean.lower() in ATTRIBUTE_BLACKLIST:
                        _logger.debug(f"Skipping blacklisted attribute '{attr_name_clean}'")
                        continue

                    # Find or create attribute (no_variant = no matrix explosion)
                    attribute = Attribute.search([('name', '=ilike', attr_name_clean)], limit=1)
                    if not attribute:
                        attribute = Attribute.create({
                            'name': attr_name_clean,
                            'create_variant': 'no_variant',
                            'display_type': 'select',
                        })
                    else:
                        if attribute.create_variant != 'no_variant':
                            _logger.info(f"Skipping attribute {attr_name_clean} - generates variants.")
                            continue

                    # Find or create value
                    val_name = str(attr_val).strip()
                    value = AttributeValue.search([
                        ('name', '=ilike', val_name),
                        ('attribute_id', '=', attribute.id)
                    ], limit=1)

                    if not value:
                        value = AttributeValue.create({
                            'name': val_name,
                            'attribute_id': attribute.id
                        })

                    # Link value to product
                    existing_line = AttributeLine.search([
                        ('product_tmpl_id', '=', product.id),
                        ('attribute_id', '=', attribute.id)
                    ], limit=1)

                    if existing_line:
                        if value.id not in existing_line.value_ids.ids:
                            existing_line.write({'value_ids': [(4, value.id)]})
                    else:
                        AttributeLine.create({
                            'product_tmpl_id': product.id,
                            'attribute_id': attribute.id,
                            'value_ids': [(6, 0, [value.id])]
                        })
    except Exception as attr_e:
        _logger.error(f"Failed to process dynamic attributes for {product.name}: {attr_e}")

    return True


def _parse_ai_content(raw_text):
    """Parse JSON from AI response, stripping markdown code fences if present."""
    content = raw_text.strip()
    if content.startswith('```json'):
        content = content[7:]
    if content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    return json.loads(content.strip())


def _enrich_with_gemini(product, ICP):
    """Generates Marketing Content using Google Gemini AI."""
    if genai is None:
        _logger.warning("google.generativeai not installed. Run: pip install google-generativeai")
        return False

    api_key = ICP.get_param('tec_catalog_enricher.gemini_api_key')
    model_name = ICP.get_param('tec_catalog_enricher.gemini_model') or 'gemini-2.0-flash'

    if not api_key:
        _logger.warning("Gemini API Key missing.")
        return False

    custom_prompt = ICP.get_param('tec_catalog_enricher.ai_custom_prompt')
    use_image = ICP.get_param('tec_catalog_enricher.ai_input_thumbnail')
    context_str = _build_context(product, ICP)
    final_prompt = custom_prompt.format(inputs=context_str)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        contents = [final_prompt]
        if use_image and product.image_1920:
            import base64
            contents.append({
                "mime_type": "image/png",
                "data": product.image_1920
            })

        response = model.generate_content(contents)
        data = _parse_ai_content(response.text)
        return _apply_ai_response(product, data)

    except Exception as e:
        _logger.error(f"Gemini Enrichment Failed for '{product.name}': {e}")
        return False


def _enrich_with_openai(product, ICP):
    """Generates Marketing Content using OpenAI (GPT-4.1 Nano / GPT-4o-mini / o4-mini)."""
    api_key = ICP.get_param('tec_catalog_enricher.openai_api_key')
    model_name = ICP.get_param('tec_catalog_enricher.openai_model') or 'gpt-4.1-nano'

    if not api_key:
        _logger.warning("OpenAI API Key missing.")
        return False

    custom_prompt = ICP.get_param('tec_catalog_enricher.ai_custom_prompt')
    context_str = _build_context(product, ICP)
    final_prompt = custom_prompt.format(inputs=context_str)

    try:
        import requests as req
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': model_name,
            'messages': [
                {'role': 'system', 'content': 'You are a product enrichment assistant. Always reply with valid JSON only.'},
                {'role': 'user', 'content': final_prompt},
            ],
            'response_format': {'type': 'json_object'},
            'temperature': 0.4,
        }
        resp = req.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        raw = resp.json()['choices'][0]['message']['content']
        data = _parse_ai_content(raw)
        return _apply_ai_response(product, data)

    except Exception as e:
        _logger.error(f"OpenAI Enrichment Failed for '{product.name}': {e}")
        return False
