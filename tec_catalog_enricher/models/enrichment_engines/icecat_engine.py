import requests
import base64
import logging
from lxml import etree

_logger = logging.getLogger(__name__)

def enrich_product(product, mpn):
    """
    Orchestrator for Icecat Enrichment.
    Supports:
    1. Legacy XML (Basic Auth) - Good for simple data.
    2. Modern JSON (Token Auth) - Faster, more reliable for supported brands.
    """
    ICP = product.env['ir.config_parameter'].sudo()
    
    # Check Auth Method
    auth_method = ICP.get_param('tec_catalog_enricher.icecat_auth_method', 'basic')
    
    if auth_method == 'token':
        api_token = ICP.get_param('tec_catalog_enricher.icecat_api_token')
        content_token = ICP.get_param('tec_catalog_enricher.icecat_content_token')
        if not content_token:
            _logger.warning("Icecat Content Token missing in Settings.")
            return False
        return _enrich_product_json(product, mpn, api_token, content_token)
        
    else:
        # Fallback to XML/Basic
        username = ICP.get_param('tec_catalog_enricher.icecat_username')
        password = ICP.get_param('tec_catalog_enricher.icecat_password')
        if not username or not password:
            _logger.warning("Icecat credentials (Basic) missing.")
            return False
        return _enrich_product_xml(product, mpn, username, password)

def _enrich_product_json(product, mpn, api_token, content_token):
    """
    Fetches data from Icecat Live JSON API.
    """
    if not product.product_brand_id:
        return False

    brand_name = product.product_brand_id.name
    # Construct URL
    # https://live.icecat.biz/api?brand={brand}&part_code={mpn}&content_token={token}
    url = "https://live.icecat.biz/api"
    params = {
        'brand': brand_name,
        'part_code': mpn,
        'content_token': content_token,
        'lang': 'es'
    }
    # Some endpoints might require app_key in headers or params if using specific tiers
    headers = {}
    if api_token:
        headers['app_key'] = api_token
    
    try:
        _logger.info(f"Icecat JSON Sync for {mpn} ({brand_name})...")
        response = requests.get(url, params=params, headers=headers, timeout=25)
        
        if response.status_code != 200:
            _logger.warning(f"Icecat JSON Error {response.status_code}: {response.text[:200]}")
            return False
            
        data = response.json()
        if 'data' not in data:
            return False
            
        p_data = data['data']
        general_info = p_data.get('general_info', {})
        
        # --- 1. Product Link & ID ---
        vals = {}
        icecat_id = str(general_info.get('icecat_id', ''))
        
        # Fix for User's URL Issue: Prefer URL from API, fallback to constructed
        icecat_url = str(general_info.get('icecat_url', ''))
        if icecat_url:
             vals['icecat_product_url'] = icecat_url
        elif icecat_id and icecat_id.isdigit():
             vals['icecat_product_url'] = f"https://icecat.biz/p/product/{icecat_id}.html"
        else:
             # Fallback or Skip
             _logger.warning(f"Invalid Icecat ID for URL: {icecat_id}")
        
        # --- 2. Description & Specs ---
        # LongDesc is usually under 'general_info.description.long_desc' or similar?
        # In JSON API: 'general_info' -> 'description' -> 'long_desc' might be available directly or via 'reasons_to_buy'
        # Let's inspect typical response. Usually 'general_info' has 'summary_description' or 'long_summary_description'
        # But robust description is often in 'description' field if available.
        
        # Attempt to get description
        long_desc = ""
        # The structure varies. Let's try to find a description text.
        # Often: p_data['general_info']['description']['long_desc'] (requires checking)
        # Or: p_data['reasons_to_buy']
        
        # Using a simpler approach for now:
        # Check 'general_info' -> 'description'
        # Check 'general_info' -> 'summary_description'
        
        # Note: Icecat JSON structure is complex. 'general_info' often holds metadata.
        # Descriptive text might be in parsing 'Main Description'.
        
        # Attempt to get description with safe navigation and fallback
        general_info = p_data.get('general_info', {})
        long_desc = general_info.get('description', {}).get('long_desc')
        if not long_desc:
            long_desc = general_info.get('summary_description', {}).get('long_summary_description', '')
        
        # Ensure string
        if not isinstance(long_desc, str):
            long_desc = ""
            
        # Specs
        specs_html = _parse_json_specs_to_styled_html(p_data.get('features_groups', []))
        
        # Additive Description
        icecat_section = ""
        if long_desc or specs_html:
             icecat_section = f"""
                <div class="tec-icecat-enrichment" style="margin-top: 30px; border-top: 2px dashed #ccc; padding-top: 20px;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                         <i>Fuente: Información proveída por Icecat Open Catalog (JSON)</i>
                    </div>
                    {f'<p class="icecat-long-desc">{long_desc.replace(chr(10), "<br/>")}</p>' if long_desc else ''}
                    {specs_html}
                </div>
             """
        
        if icecat_section:
            current_desc = product.tec_enriched_description or ''
            vals['tec_enriched_description'] = f"{current_desc}{icecat_section}"
            
        # --- 3. Images ---
        seen_urls = set()
        gallery_images_data = []
        
        gallery = p_data.get('gallery', [])
        # Format: [{'ThumbUrl':..., 'Pic500x500':..., 'Pic':...}, ...]
        
        # Main Image (First in gallery or specific field)
        # JSON usually has 'Image' in general_info?
        main_img_url = general_info.get('high_pic') or general_info.get('image')
        
        if main_img_url:
            seen_urls.add(main_img_url)
            img_bin = _download_image(main_img_url)
            if img_bin:
                if not product.image_1920:
                    vals['image_1920'] = img_bin
                else:
                    gallery_images_data.append(('Icecat Main View', img_bin))
                    
        # Gallery
        for i, item in enumerate(gallery):
            if i > 15: break
            pic_url = item.get('Pic500x500') or item.get('Pic') or item.get('pic')
            if pic_url and pic_url not in seen_urls:
                seen_urls.add(pic_url)
                img_bin = _download_image(pic_url)
                if img_bin:
                    gallery_images_data.append((f'Icecat Gallery {i+1}', img_bin))
                    
        # Validate Content before saving
        if not long_desc and not specs_html and not gallery_images_data:
            _logger.warning(f"Icecat JSON Sync for {mpn}: Response yielded no meaningful data (empty desc, specs, and images).")
            return False

        # Write
        if vals:
            product.write(vals)
            
        if gallery_images_data:
            existing_count = len(product.tec_product_image_ids)
            for i, (name, data) in enumerate(gallery_images_data):
                product.env['tec.product.image'].create({
                    'product_tmpl_id': product.id,
                    'name': name,
                    'sequence': 50 + existing_count + i,
                    'image_1920': data
                })
        
        return True

    except Exception as e:
        _logger.error(f"Icecat JSON Error for {mpn}: {str(e)}")
        return False

def _enrich_product_xml(product, mpn, username, password):
    """
    Fetches data from Open Icecat using Basic Auth (Legacy XML).
    """
    if not product.product_brand_id:
        return False
        
    brand_name = product.product_brand_id.name
    url = f"https://data.icecat.biz/xml_s3/xml_server3.cgi?prod_id={mpn}&vendor={brand_name}&lang=es&output=productxml"
    
    try:
        _logger.info(f"Expert Icecat Sync (XML) for {mpn} ({brand_name})...")
        response = requests.get(url, auth=(username, password), timeout=25)
        if response.status_code != 200:
            return False
            
        root = etree.fromstring(response.content)
        product_node = root.find('.//Product')
        
        if product_node is not None and product_node.get('ErrorMessage'):
            _logger.warning(f"Icecat error for {mpn}: {product_node.get('ErrorMessage')}")
            return False
            
        if product_node is None:
            return False

        vals = {}
        gallery_images_data = []
        seen_urls = set()
        
        # 1. Product Link & ID
        icecat_id = product_node.get('ID')
        
        # Try to get official ProductPage URL from XML
        product_page_node = product_node.find('.//ProductRelated[@Category_ID="0"]/Product') # Sometimes linked? No.
        # usually it's just a constructed URL or derived.
        # Let's try to find if there is a specific URL field in common XML.
        # Actually, standard Open Icecat XML often lacks a direct "Product Page URL" field other than constructing it.
        # However, if 'ProductPage' element exists (from search results):
        product_page_url = ""
        # Inspect for ProductPage element if it exists in schema
        
        # Fallback to constructing based on ID which is reliable
        if icecat_id and icecat_id.isdigit():
             vals['icecat_product_url'] = f"https://icecat.biz/p/product/{icecat_id}.html"
        else:
             _logger.warning(f"Invalid Icecat ID (XML): {icecat_id}")

        # 2. Description (LongDesc)
        desc_node = product_node.find('.//ProductDescription')
        long_desc = ""
        if desc_node is not None:
            long_desc = desc_node.get('LongDesc') or ""
        
        # 3. Specifications Table
        specs_html = _parse_specs_to_styled_html(product_node)
        
        # Additive Description Logic
        icecat_section = ""
        if long_desc or specs_html:
             icecat_section = f"""
                <div class="tec-icecat-enrichment" style="margin-top: 30px; border-top: 2px dashed #ccc; padding-top: 20px;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                         <i>Fuente: Información proveída por Icecat Open Catalog (XML)</i>
                    </div>
                    {f'<p class="icecat-long-desc">{long_desc.replace(chr(10), "<br/>")}</p>' if long_desc else ''}
                    {specs_html}
                </div>
             """
        
        if icecat_section:
            current_desc = product.tec_enriched_description or ''
            vals['tec_enriched_description'] = f"{current_desc}{icecat_section}"

        # 4. Main Image
        high_pic = product_node.get('HighPic')
        if high_pic and 'http' in high_pic:
            seen_urls.add(high_pic)
            img_bin = _download_image(high_pic)
            if img_bin:
                if not product.image_1920:
                    vals['image_1920'] = img_bin
                else:
                    gallery_images_data.append(('Icecat Main View', img_bin))

        # 5. Gallery Images
        gallery_node = product_node.find('ProductGallery')
        if gallery_node is not None:
            for i, pic_node in enumerate(gallery_node.findall('ProductPicture')):
                if i > 15: break
                pic_url = pic_node.get('Pic500x500') or pic_node.get('Pic')
                if pic_url and 'http' in pic_url and pic_url not in seen_urls:
                    seen_urls.add(pic_url)
                    img_bin = _download_image(pic_url)
                    if img_bin:
                        gallery_images_data.append((f'Icecat Gallery {i+1}', img_bin))

        if vals:
            product.write(vals)
            
        if gallery_images_data:
            existing_count = len(product.tec_product_image_ids)
            for i, (name, data) in enumerate(gallery_images_data):
                product.env['tec.product.image'].create({
                    'product_tmpl_id': product.id,
                    'name': name,
                    'sequence': 50 + existing_count + i,
                    'image_1920': data
                })

        return True

    except Exception as e:
        _logger.error(f"Icecat Expert Error for {mpn}: {str(e)}")
        return False

def _download_image(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return base64.b64encode(r.content)
    except Exception:
        pass
    return False

def _parse_specs_to_styled_html(product_node):
    """
    Parses ProductFeature elements to build a styled HTML table (XML Source).
    """
    rows = []
    for feature in product_node.findall('.//ProductFeature'):
        value = feature.get('Presentation_Value')
        name = ""
        feat_node = feature.find('Feature')
        if feat_node is not None:
            name_node = feat_node.find('Name')
            if name_node is not None:
                name = name_node.get('Value')
        
        if name and value:
            rows.append(f"""
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 6px 10px; font-weight: bold; width: 40%; color: #333; background-color: #fcfcfc;">{name}</td>
                    <td style="padding: 6px 10px; color: #666;">{value}</td>
                </tr>
            """)
    
    if not rows:
        return ""

    return f"""
    <div class="tec-icecat-specs" style="margin-top: 15px; font-family: sans-serif; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden;">
        <div style="background-color: #f5f5f5; color: #333; padding: 8px 12px; font-size: 1em; font-weight: bold; border-bottom: 1px solid #ddd;">
            🎯 Especificaciones Icecat
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """

def _parse_json_specs_to_styled_html(features_groups):
    """
    Parses JSON features_groups to build a styled HTML table.
    """
    if not features_groups:
        return ""
        
    rows = []
    # features_groups format: [{'name': '...', 'features': [{'name': '...', 'presentation_value': '...'}, ...]}, ...]
    
    for group in features_groups:
        group_name = group.get('name', 'General')
        # Optional: Add group header
        # rows.append(f"<tr><td colspan='2'><b>{group_name}</b></td></tr>")
        
        for feature in group.get('features', []):
            name = feature.get('name', '')
            value = feature.get('presentation_value', '')
            
            if name and value:
                rows.append(f"""
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 6px 10px; font-weight: bold; width: 40%; color: #333; background-color: #fcfcfc;">{name}</td>
                        <td style="padding: 6px 10px; color: #666;">{value}</td>
                    </tr>
                """)

    if not rows:
        return ""

    return f"""
    <div class="tec-icecat-specs" style="margin-top: 15px; font-family: sans-serif; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden;">
        <div style="background-color: #f5f5f5; color: #333; padding: 8px 12px; font-size: 1em; font-weight: bold; border-bottom: 1px solid #ddd;">
            🎯 Especificaciones Icecat (JSON)
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """
