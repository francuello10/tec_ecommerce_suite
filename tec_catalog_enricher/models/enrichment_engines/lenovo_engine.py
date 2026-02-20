import requests
import logging
import time
import base64
from odoo import _

_logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    _logger.warning("BeautifulSoup library not found. Lenovo scraping will be disabled.")
    BeautifulSoup = None

def enrich_product(product, mpn):
    """
    Scrapes Lenovo PSREF for technical data using JSON APIs.
    """
    if not BeautifulSoup:
        return False
        
    time.sleep(1) # Rate limit
    
    # 1. Search API (Suggest API)
    search_url = "https://psref.lenovo.com/api/search/DefinitionFilterAndSearch/Suggest"
    t = int(time.time() * 1000)
    params = {'kw': mpn, 'SearchType': 'Model', 't': t}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://psref.lenovo.com/',
    }
    
    try:
        _logger.info(f"Expert Lenovo Sync for {mpn}...")
        response = requests.get(search_url, params=params, headers=headers, timeout=15)
        if response.status_code != 200:
            return False
            
        json_data = response.json()
        if not json_data or json_data.get('code') != 1 or not json_data.get('data'):
            return False
            
        # Select best match
        item = json_data['data'][0] 
        product_info = item.get('info', {})
        product_url = product_info.get('page')
        product_key = item.get('ProductKey')
        main_img_url_api = product_info.get('photo')
        datasheet_url = product_info.get('datasheet')
        
        if not product_url or not product_key:
            return False
            
        # Data Accumulation (ORM Optimization)
        vals = {}
        gallery_images_data = [] # Store binary image data in memory
        seen_urls = set() # URL Deduplication
        
        # Save Official URLs
        if not product.external_product_url:
            vals['external_product_url'] = product_url
        if not product.lenovo_datasheet_url and datasheet_url:
            vals['lenovo_datasheet_url'] = datasheet_url

        # 2. Fetch Specifications JSON API (Robust)
        spec_api_url = f"https://psref.lenovo.com/api/model/Info/SpecData?model_code={mpn}&show_hyphen=false"
        spec_response = requests.get(spec_api_url, headers=headers, timeout=15)
        if spec_response.status_code == 200:
            spec_json = spec_response.json()
            if spec_json.get('code') == 1 and spec_json.get('data'):
                specs_html = _build_specs_table_from_json(spec_json['data'])
                if specs_html:
                    current_desc = product.tec_enriched_description or ''
                    vals['tec_enriched_description'] = f"{current_desc}<br/>{specs_html}"

        # 3. Fetch Photos JSON API (Aggressive)
        photo_api_url = f"https://psref.lenovo.com/api/product/Photo/0?ProductKey={product_key}&model_code={mpn}"
        photo_response = requests.get(photo_api_url, headers=headers, timeout=15)
        
        # Priority 1: Main Image from Suggest API
        if main_img_url_api:
            seen_urls.add(main_img_url_api)
            img_bin = _download_image(main_img_url_api, headers=headers)
            if img_bin:
                if not product.image_1920:
                    vals['image_1920'] = img_bin
                else:
                    gallery_images_data.append(('Lenovo Main View', img_bin))

        # Priority 2: Gallery from Photo API
        if photo_response.status_code == 200:
            photo_json = photo_response.json()
            if photo_json.get('code') == 1 and photo_json.get('data'):
                for photo_item in photo_json['data']:
                    src = photo_item.get('src')
                    if not src: continue
                    normalized_url = _resolve_url(src)
                    
                    if normalized_url not in seen_urls:
                        seen_urls.add(normalized_url)
                        img_bin = _download_image(normalized_url, headers=headers)
                        if img_bin:
                            gallery_images_data.append(('Lenovo Gallery', img_bin))

        # 4. Final Batched Writes (ORM Optimization)
        if vals:
            product.write(vals)
            
        if gallery_images_data:
            existing_count = len(product.tec_product_image_ids)
            for i, (name, data) in enumerate(gallery_images_data):
                # Backend Gallery
                product.env['tec.product.image'].create({
                    'product_tmpl_id': product.id,
                    'name': name,
                    'sequence': 20 + existing_count + i,
                    'image_1920': data
                })
                # Website Gallery (Odoo Native)
                if hasattr(product, 'product_template_image_ids'):
                    product.env['product.image'].create({
                        'product_tmpl_id': product.id,
                        'name': name,
                        'sequence': 20 + existing_count + i,
                        'image_1920': data
                    })
        
        return True
            
    except Exception as e:
        _logger.error(f"Lenovo Expert Refactor Error for {mpn}: {e}")
        return False

def _resolve_url(rel_url):
    if not rel_url: return ""
    if rel_url.startswith('http'): return rel_url
    if rel_url.startswith('//'): return f"https:{rel_url}"
    return f"https://psref.lenovo.com{rel_url}"

def _download_image(url, headers=None):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return base64.b64encode(r.content)
    except Exception:
        pass
    return False

def _build_specs_table_from_json(data):
    """
    Builds a styled HTML specs table from Lenovo JSON data.
    """
    rows = []
    spec_data = data.get('SpecData', [])
    for group in spec_data:
        # Optional: Add a separator row for the title (Performance, Design, etc.)
        if group.get('title'):
             rows.append(f"""
                <tr style="background-color: #f2f2f2;">
                    <td colspan="2" style="padding: 10px; font-weight: bold; color: #333; text-transform: uppercase; border-top: 2px solid #294E95;">
                        {group['title']}
                    </td>
                </tr>
            """)
        
        key = group.get('name')
        contents = group.get('content', [])
        val = "<br/>".join(contents) if contents else ""
        
        if key and val:
            rows.append(f"""
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px; font-weight: bold; width: 35%; background-color: #fdfdfd; color: #444;">{key}</td>
                    <td style="padding: 8px; color: #666;">{val}</td>
                </tr>
            """)

    if not rows:
        return ""

    return f"""
    <div class="tec-lenovo-specs" style="margin-top: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <div style="background-color: #294E95; color: white; padding: 12px 15px; font-size: 1.1em; font-weight: bold; display: flex; align-items: center;">
            <span style="margin-right: 10px;">📋</span> Especificaciones Oficiales (Lenovo PSREF)
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px; line-height: 1.5;">
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """
