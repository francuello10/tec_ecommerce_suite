import requests
import base64
import logging
from lxml import etree

_logger = logging.getLogger(__name__)

def enrich_product(product, mpn):
    """
    Fetches data from Open Icecat using Basic Auth.
    Parses XML with expert refinements: ORM optimization and additive logic.
    """
    ICP = product.env['ir.config_parameter'].sudo()
    username = ICP.get_param('tec_catalog_enricher.icecat_username')
    password = ICP.get_param('tec_catalog_enricher.icecat_password')
    
    if not username or not password:
        _logger.warning("Icecat credentials missing in Settings.")
        return False
        
    if not product.product_brand_id:
        return False
        
    brand_name = product.product_brand_id.name
    url = f"https://data.icecat.biz/xml_s3/xml_server3.cgi?prod_id={mpn}&vendor={brand_name}&lang=es&output=productxml"
    
    try:
        _logger.info(f"Expert Icecat Sync for {mpn} ({brand_name})...")
        response = requests.get(url, auth=(username, password), timeout=25)
        if response.status_code != 200:
            return False
            
        root = etree.fromstring(response.content)
        product_node = root.find('.//Product')
        
        # Check for Icecat API Error (False Positives like "The requested XML data-sheet is not present")
        if product_node is not None and product_node.get('ErrorMessage'):
            _logger.warning(f"Icecat error for {mpn}: {product_node.get('ErrorMessage')}")
            return False
            
        if product_node is None:
            return False

        # Data Accumulation (ORM Optimization)
        vals = {}
        gallery_images_data = []
        seen_urls = set()
        
        # 1. Product Link & ID
        icecat_id = product_node.get('ID')
        if icecat_id:
             vals['icecat_product_url'] = f"https://icecat.biz/p/product/{icecat_id}.html"

        # 2. Description (LongDesc)
        desc_node = product_node.find('.//ProductDescription')
        long_desc = ""
        if desc_node is not None:
            long_desc = desc_node.get('LongDesc') or ""
        
        # 3. Specifications Table
        specs_html = _parse_specs_to_styled_html(product_node)
        
        # Additive Description Logic: Build Icecat Section
        icecat_section = ""
        if long_desc or specs_html:
             icecat_section = f"""
                <div class="tec-icecat-enrichment" style="margin-top: 30px; border-top: 2px dashed #ccc; padding-top: 20px;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                         <i>Fuente: Información proveída por Icecat Open Catalog</i>
                    </div>
                    {f'<p class="icecat-long-desc">{long_desc.replace(chr(10), "<br/>")}</p>' if long_desc else ''}
                    {specs_html}
                </div>
             """
        
        if icecat_section:
            # We APPEND to whatever is already in tec_enriched_description (e.g. Lenovo data)
            current_desc = product.tec_enriched_description or ''
            vals['tec_enriched_description'] = f"{current_desc}{icecat_section}"

        # 4. Main Image (Additive)
        high_pic = product_node.get('HighPic')
        if high_pic and 'http' in high_pic:
            seen_urls.add(high_pic)
            img_bin = _download_image(high_pic)
            if img_bin:
                if not product.image_1920:
                    vals['image_1920'] = img_bin
                else:
                    gallery_images_data.append(('Icecat Main View', img_bin))

        # 5. Gallery Images (Deduplicated)
        gallery_node = product_node.find('ProductGallery')
        if gallery_node is not None:
            for i, pic_node in enumerate(gallery_node.findall('ProductPicture')):
                if i > 15: break # Safety limit
                pic_url = pic_node.get('Pic500x500') or pic_node.get('Pic')
                if pic_url and 'http' in pic_url and pic_url not in seen_urls:
                    seen_urls.add(pic_url)
                    img_bin = _download_image(pic_url)
                    if img_bin:
                        gallery_images_data.append((f'Icecat Gallery {i+1}', img_bin))

        # 6. Final Batched Writes (ORM Optimization)
        if vals:
            product.write(vals)
            
        if gallery_images_data:
            existing_count = len(product.tec_product_image_ids)
            for i, (name, data) in enumerate(gallery_images_data):
                product.env['tec.product.image'].create({
                    'product_tmpl_id': product.id,
                    'name': name,
                    'sequence': 50 + existing_count + i, # Higher sequence for Icecat
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
    Parses ProductFeature elements to build a styled HTML table.
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
