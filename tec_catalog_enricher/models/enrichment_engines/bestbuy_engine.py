import requests
import base64
import logging

_logger = logging.getLogger(__name__)

def enrich_product(product, mpn):
    """
    Motor de Enriquecimiento: Best Buy Developer API.
    Busca productos tecnológicos en el catálogo de EE.UU por Manufacturer Part Number (MPN).
    Requiere una API Key obtenida en developer.bestbuy.com.
    """
    ICP = product.env['ir.config_parameter'].sudo()
    
    use_bestbuy = ICP.get_param('tec_catalog_enricher.use_bestbuy', 'False') == 'True'
    if not use_bestbuy:
        return False
        
    api_key = ICP.get_param('tec_catalog_enricher.bestbuy_api_key')
    if not api_key:
        _logger.warning("Best Buy API Key missing in Settings.")
        return False

    if not mpn or not product.product_brand_id:
        return False

    brand_name = product.product_brand_id.name
    # Buscar por Manufacturer y Model Number. A veces Best Buy usa manufacturer="HP" en lugar de HEWLETT PACKARD.
    # Por eso el Brand Normalization previo nos ayuda.
    
    # URL Construct para Best Buy API (Products Endpoint)
    # search by modelNumber (which is usually MPN) or upc
    # filter by manufacturer for safety
    query = f"(modelNumber={mpn}&manufacturer={brand_name})"
    url = f"https://api.bestbuy.com/v1/products{query}?format=json&show=sku,name,longDescription,features.feature,details.name,details.value,image,alternateViews.image&apiKey={api_key}"
    
    try:
        _logger.info(f"BestBuy Sync for {mpn} ({brand_name})...")
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            _logger.warning(f"BestBuy API Error {response.status_code}: {response.text[:200]}")
            return False
            
        data = response.json()
        if data.get('total', 0) == 0:
            _logger.info(f"BestBuy: Product {mpn} not found.")
            return False
            
        # Tomar el primer resultado
        p_data = data['products'][0]
        
        vals = {}
        
        # --- 1. Descripción Larga ---
        long_desc = p_data.get('longDescription', '')
        
        # --- 2. Features (Viñetas de Marketing) ---
        features = p_data.get('features', [])
        features_html = ""
        if features:
            lis = "".join([f"<li>{f.get('feature', '')}</li>" for f in features if f.get('feature')])
            features_html = f"<ul>{lis}</ul>"
            
        # --- 3. Detalles de Especificaciones (Technical Sheet) ---
        details = p_data.get('details', [])
        specs_rows = []
        for det in details:
            name = det.get('name', '')
            val = det.get('value', '')
            if name and val:
                specs_rows.append(f'''
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 6px 10px; font-weight: bold; width: 40%; color: #333; background-color: #fcfcfc;">{name}</td>
                        <td style="padding: 6px 10px; color: #666;">{val}</td>
                    </tr>
                ''')
                
        specs_html = ""
        if specs_rows:
            specs_html = f'''
            <div class="tec-bestbuy-specs" style="margin-top: 15px; font-family: sans-serif; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden;">
                <div style="background-color: #0046be; color: white; padding: 8px 12px; font-size: 1em; font-weight: bold; border-bottom: 1px solid #003696;">
                    🎯 Especificaciones Técnicas
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <tbody>
                        {''.join(specs_rows)}
                    </tbody>
                </table>
            </div>
            '''

        # Consolidar todo en la variable de Odoo
        bestbuy_section = ""
        if long_desc or features_html or specs_html:
             bestbuy_section = f"""
                <div class="tec-bestbuy-enrichment" style="margin-top: 30px; border-top: 2px dashed #0046be; padding-top: 20px;">
                    <div style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
                         <i>Fuente: Información proveída por Best Buy® Data API</i>
                    </div>
                    {f'<p class="bestbuy-long-desc">{long_desc}</p>' if long_desc else ''}
                    {features_html}
                    {specs_html}
                </div>
             """
             current_desc = product.tec_enriched_description or ''
             vals['tec_enriched_description'] = f"{current_desc}{bestbuy_section}"
             
        # --- 4. Imágenes ---
        gallery_images_data = []
        seen_urls = set()
        
        main_img_url = p_data.get('image')
        if main_img_url and main_img_url not in seen_urls:
            seen_urls.add(main_img_url)
            img_bin = _download_image(main_img_url)
            if img_bin:
                if not product.image_1920:
                    vals['image_1920'] = img_bin
                else:
                    gallery_images_data.append(('BestBuy Main View', img_bin))
                    
        # Galería alternativa
        alt_views = p_data.get('alternateViews', [])
        for i, view in enumerate(alt_views):
            if i > 5: break # Max 5 extra images
            alt_img_url = view.get('image')
            if alt_img_url and alt_img_url not in seen_urls:
                seen_urls.add(alt_img_url)
                img_bin = _download_image(alt_img_url)
                if img_bin:
                    gallery_images_data.append((f'BestBuy View {i+1}', img_bin))
                    
        # Guardado en Odoo
        if vals:
            product.write(vals)
            
        if gallery_images_data:
            existing_count = len(product.tec_product_image_ids)
            for i, (name, data) in enumerate(gallery_images_data):
                product.env['tec.product.image'].create({
                    'product_tmpl_id': product.id,
                    'name': name,
                    'sequence': 60 + existing_count + i,
                    'image_1920': data
                })
        
        return True
        
    except requests.exceptions.Timeout:
        _logger.warning(f"BestBuy API timeout para {mpn}")
        return False
    except Exception as e:
        _logger.error(f"BestBuy API Error for {mpn}: {str(e)}")
        return False

def _download_image(url):
    try:
        # A veces BestBuy bloquea scrapers sin User-Agent
        headers = {'User-Agent': 'Mozilla/5.0 Odoo/19.0'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return base64.b64encode(r.content)
    except Exception:
        pass
    return False
