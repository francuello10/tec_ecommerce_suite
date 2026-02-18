import requests
import logging
import base64

_logger = logging.getLogger(__name__)

def enrich_product(product, mpn):
    """
    Fallback: Google Custom Search for Images & PDFs.
    Odoo v19 natively supports WebP for optimal SEO and performance.
    """
    api_key = product.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.google_cse_key')
    cx = product.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.google_cse_cx')
    
    if not api_key or not cx:
         _logger.warning("Google CSE credentials missing.")
         return False

    # 1. Image Search (WebP / PNG / JPG)
    if not product.image_1920:
        # Search without strict filetype extension to get highest quality original
        query = f"{product.product_brand_id.name} {mpn} official product image"
        url = f"https://www.googleapis.com/customsearch/v1?q={query}&cx={cx}&key={api_key}&searchType=image&num=1&imgSize=large"
        try:
            res = requests.get(url).json()
            if 'items' in res:
                img_url = res['items'][0]['link']
                # Download
                img_data = requests.get(img_url, timeout=10)
                if img_data.status_code == 200 and 'image' in img_data.headers.get('Content-Type', ''):
                    # Odoo 19 will automatically handle the storage and serve as WebP to clients
                    product.image_1920 = base64.b64encode(img_data.content)
        except Exception as e:
            _logger.error(f"Google Image Search Failed: {e}")

    # 2. PDF Datasheet Search
    if not product.product_document_ids.filtered(lambda d: d.mimetype == 'application/pdf'):
        query_pdf = f"{product.product_brand_id.name} {mpn} specifications filetype:pdf"
        url_pdf = f"https://www.googleapis.com/customsearch/v1?q={query_pdf}&cx={cx}&key={api_key}&num=1"
        try:
            res = requests.get(url_pdf).json()
            if 'items' in res:
                pdf_url = res['items'][0]['link']
                _logger.info(f"Google: Found PDF datasheet at {pdf_url}")
                pdf_res = requests.get(pdf_url, timeout=15)
                if pdf_res.status_code == 200:
                    product.env['product.document'].create({
                        'name': f"Ficha Técnica {mpn}.pdf",
                        'raw': pdf_res.content,
                        'res_model': 'product.template',
                        'res_id': product.id,
                        'shown_on_product_page': True,
                    })
        except Exception as e:
             _logger.error(f"Google PDF Search Failed: {e}")
             
    return True
