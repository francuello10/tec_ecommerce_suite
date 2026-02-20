import requests
import logging

_logger = logging.getLogger(__name__)

def enrich_product(product, mpn=None, ean=None):
    """
    Motor de Enriquecimiento: Product Open Data / Open Products Facts.
    Busca productos por EAN/UPC en bases de datos abiertas y comunitarias.
    Ideal para productos donde Icecat o BestBuy fallan.
    """
    ICP = product.env['ir.config_parameter'].sudo()
    
    use_pod = ICP.get_param('tec_catalog_enricher.use_pod', 'False') == 'True'
    if not use_pod:
        return False
        
    barcode = ean or product.barcode
    if not barcode:
        _logger.info("POD Engine: No EAN/Barcode provided, skipping.")
        return False

    url = f"https://world.openproductsfacts.org/api/v0/product/{barcode}.json"
    
    try:
        _logger.info(f"Open Product Data Sync for EAN {barcode}...")
        
        # User-Agent is recommended by OpenFacts Foundation
        headers = {'User-Agent': 'Odoo-TecEcommerceSuite/1.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return False
            
        data = response.json()
        if data.get('status') != 1:
            _logger.info(f"POD: Product {barcode} not found.")
            return False
            
        p_data = data.get('product', {})
        vals = {}
        
        name = p_data.get('product_name', '')
        # Only overwrite if we have nothing better. Usually we have a name from Air
        if name and product.name == 'New Product':
            vals['name'] = name
            
        # Description
        desc = p_data.get('generic_name', '') or p_data.get('generic_name_en', '')
        if desc:
             pod_section = f"""
                <div class="tec-pod-enrichment" style="margin-top: 30px; border-top: 2px dashed #4CAF50; padding-top: 20px;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                         <i>Fuente: Información proveída por Product Open Data / OpenProductsFacts</i>
                    </div>
                    <p class="pod-desc">{desc}</p>
                </div>
             """
             current_desc = product.tec_enriched_description or ''
             vals['tec_enriched_description'] = f"{current_desc}{pod_section}"

        if vals:
             product.write(vals)

        # Main Image (often crowd-sourced photos, good fallback)
        img_url = p_data.get('image_url')
        if img_url and not product.image_1920:
             img_res = requests.get(img_url, headers=headers, timeout=10)
             if img_res.status_code == 200:
                 import base64
                 product.image_1920 = base64.b64encode(img_res.content)
                 
        return True

    except requests.exceptions.Timeout:
        _logger.warning(f"POD Engine timeout para EAN {barcode}")
        return False
    except Exception as e:
        _logger.error(f"POD Engine Error for {barcode}: {str(e)}")
        return False
