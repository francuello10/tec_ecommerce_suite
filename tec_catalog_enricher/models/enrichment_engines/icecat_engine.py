import requests
import base64
import logging
from lxml import etree

_logger = logging.getLogger(__name__)

def enrich_product(product, mpn):
    """
    Fetches data from Open Icecat using Basic Auth.
    Parses XML to extract: Description, Images, and Specifications.
    """
    ICP = product.env['ir.config_parameter'].sudo()
    username = ICP.get_param('tec_catalog_enricher.icecat_username')
    password = ICP.get_param('tec_catalog_enricher.icecat_password')
    
    if not username or not password:
        _logger.warning("Icecat credentials missing in Settings.")
        return False
        
    if not product.product_brand_id:
        _logger.warning(f"Skipping Icecat for {product.name} (No Brand set).")
        return False
        
    brand_name = product.product_brand_id.name
    
    # URL Construction for Open Icecat (XML S3)
    # lang=es for Spanish content
    url = f"https://data.icecat.biz/xml_s3/xml_server3.cgi?prod_id={mpn}&vendor={brand_name}&lang=es&output=productxml"
    
    try:
        _logger.info(f"Querying Icecat for {mpn} ({brand_name})...")
        response = requests.get(url, auth=(username, password), timeout=25)
        
        if response.status_code != 200:
            _logger.warning(f"Icecat Request Failed: {response.status_code}")
            return False
            
        # Parse XML
        # Note: Icecat returns raw XML. We use lxml.
        root = etree.fromstring(response.content)
        
        # Check for Icecat API Error (e.g. Product not found)
        # Usually checking root tag or ErrorMessage attribute
        if root.tag == 'ICECAT-interface':
            # Check inside
            product_node = root.find('Product')
            if product_node is not None:
                err = product_node.get('ErrorMessage')
                if err:
                    _logger.warning(f"Icecat API Error for {mpn}: {err}")
                    return False
            else:
                 # Sometimes it returns empty interface
                 pass
        
        # Depending on structure, Product is usually a child of ICECAT-interface or root
        product_node = root.find('.//Product')
        if product_node is None:
            _logger.warning(f"No Product node found in Icecat XML for {mpn}")
            return False

        vals = {}
        
        # 1. Description (LongDesc)
        # Path: Product -> ProductDescription -> @LongDesc
        desc_node = product_node.find('ProductDescription')
        if desc_node is not None:
            long_desc = desc_node.get('LongDesc')
            if long_desc:
                # Basic formatting: Convert newlines to breaks if needed, usually it's plain text
                vals['tec_enriched_description'] = f"<p>{long_desc.replace(chr(10), '<br/>')}</p>"
            
            # Try to get a direct link if available in the description node or elsewhere
            # Icecat usually has a "URL" attribute in some nodes or we construct it.
            # Standard Icecat URL: https://icecat.biz/p/vendor/mpn/product-info.html
            # But simpler: https://icecat.biz/rest/product-pdf?mpn={mpn}&brand={brand_name} (often works for PDF)
            # Better: Store the search URL or the one from the XML.
            icecat_url = f"https://icecat.biz/en/search?term={mpn}" # Fallback safe search
            # If we find a specific ID in the XML, we can improve this.
            product_id = product_node.get('ID')
            if product_id:
                icecat_url = f"https://icecat.biz/p/product/{product_id}.html"
            
            vals['icecat_product_url'] = icecat_url

        # 2. Main Image (HighPic)
        high_pic = product_node.get('HighPic')
        high_pic_url = high_pic
        
        existing_images_count = len(product.tec_product_image_ids)
        next_sequence = 10 + existing_images_count
        
        if high_pic and 'http' in high_pic:
            img_data = _download_image(high_pic)
            if img_data:
                # Additive Logic: Check if main image exists
                if not product.image_1920:
                    vals['image_1920'] = img_data
                    _logger.info(f"Icecat: Set main image for {mpn}")
                else:
                    # Add as gallery image
                    product.env['tec.product.image'].create({
                        'product_tmpl_id': product.id,
                        'name': 'Icecat Main View',
                        'sequence': next_sequence,
                        'image_1920': img_data
                    })
                    next_sequence += 1

        # 3. Specifications (Features) -> Append to Description
        # We build a simple HTML table
        specs_html = _parse_specs(product_node)
        if specs_html:
            # Append, don't overwrite if existing description has content
            current_desc = product.tec_enriched_description or ''
            if 'vals' in locals() and 'tec_enriched_description' in vals:
                 current_desc = vals['tec_enriched_description']
            
            vals['tec_enriched_description'] = f"{current_desc}<br/>{specs_html}"

        # Apply updates to Product Template
        if vals:
            product.write(vals)
            _logger.info(f"Updated Product {mpn} with Icecat data.")

        # 4. Gallery Images (ProductGallery)
        # We add them to tec.product.image
        gallery_node = product_node.find('ProductGallery')
        if gallery_node is not None:
            # We don't delete existing ones to avoid clearing manual uploads, 
            # unless we implement a clear flag. For now, append.
            
            for i, pic_node in enumerate(gallery_node.findall('ProductPicture')):
                # Limit to avoiding overload
                if i > 10: break
                
                pic_url = pic_node.get('Pic500x500') or pic_node.get('Pic')
                if pic_url and 'http' in pic_url:
                    # Check if this URL is already the main image to avoid duplicate
                    if pic_url == high_pic_url:
                        continue
                        
                    img_data = _download_image(pic_url)
                    if img_data:
                        product.env['tec.product.image'].create({
                            'product_tmpl_id': product.id,
                            'name': f"Icecat Gallery {i+1}",
                            'sequence': next_sequence + i,
                            'image_1920': img_data
                        })

        return True

    except Exception as e:
        _logger.error(f"Icecat Engine Error for {mpn}: {str(e)}")
        return False

def _download_image(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return base64.b64encode(r.content)
    except Exception as e:
        _logger.warning(f"Failed to download image {url}: {e}")
    return False

def _parse_specs(product_node):
    """
    Parses ProductFeature elements to build an HTML table.
    """
    rows = []
    # Find all ProductFeature elements
    for feature in product_node.findall('.//ProductFeature'):
        # Value
        value = feature.get('Presentation_Value')
        
        # Name (Nested in Feature/Name alias)
        # Structure: <ProductFeature...> <Feature...> <Name... Value="Display diagonal"/> ...
        name = ""
        feat_node = feature.find('Feature')
        if feat_node is not None:
            name_node = feat_node.find('Name')
            if name_node is not None:
                name = name_node.get('Value')
        
        if name and value:
            rows.append(f"<tr><td style='font-weight:bold; width:40%;'>{name}</td><td>{value}</td></tr>")
    
    if rows:
        return f"""
        <div class="tec-specs-table mt-4">
            <h4 class="mb-3">Especificaciones Detalladas (Icecat)</h4>
            <table class="table table-bordered table-sm table-striped">
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
    return ""
