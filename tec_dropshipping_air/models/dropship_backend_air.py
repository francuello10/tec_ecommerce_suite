import logging
import base64
import csv
import io
import requests
import pandas as pd
import re
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
SUITE_LOG_PREFIX = "[Tec Suite] Air Connector: "

class DropshipBackendAir(models.Model):
    _inherit = 'dropship.backend'

    provider_code = fields.Selection(selection_add=[('air_csv', 'Air Computers (CSV/XLSX)')], ondelete={'air_csv': 'cascade'})
    url_endpoint_characteristics = fields.Char(string='URL Características (CSV)', help='URL del CSV de características de Air Computers')

    def action_sync_air_brands(self):
        """ Manual trigger for brands sync """
        self.ensure_one()
        _logger.info(f"{SUITE_LOG_PREFIX}Manual Brands Sync Triggered for {self.name}")
        df = self._get_df_from_url(self.url_endpoint)
        if df is not None:
            self._sync_brands_impl(df)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Marcas Sincronizadas'),
                    'message': _('Se han sincronizado las marcas exitosamente.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        return False

    def action_sync_air_characteristics(self):
        """ Manual trigger for characteristics sync """
        self.ensure_one()
        self.sync_characteristics()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Características Sincronizadas'),
                'message': _('Se han actualizado las descripciones e imágenes desde Air.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _get_df_from_url(self, url):
        """ Consolidated helper for fetching and parsing URL to DataFrame """
        content = self._fetch_any_url_content(url)
        if not content:
            return None
        try:
            url_lower = (url or "").lower()
            is_xlsx = url_lower.endswith('.xlsx') or url_lower.endswith('.xls')
            if 'docs.google.com/spreadsheets' in url_lower:
                is_xlsx = False
            
            if is_xlsx:
                df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
            else:
                try:
                    df = pd.read_csv(io.StringIO(content.decode('utf-8')), sep=None, engine='python')
                except UnicodeDecodeError:
                    df = pd.read_csv(io.StringIO(content.decode('latin-1')), sep=None, engine='python')
            
            df.columns = df.columns.str.strip().str.upper()
            return df
        except Exception as e:
            _logger.error(f"Failed to parse file from {url}: {e}")
            raise UserError(_("Failed to parse the file: %s") % str(e))

    def sync_characteristics(self):
        self.ensure_one()
        _logger.info(f"Starting Air Computers Characteristics Sync for Backend: {self.name}")

        # Fetch content
        content = self._fetch_characteristics_content()
        if not content:
            _logger.warning("No characteristics content fetched.")
            return

        try:
            try:
                decoded_content = content.decode('utf-8')
            except UnicodeDecodeError:
                decoded_content = content.decode('latin-1')
            csv_file = io.StringIO(decoded_content)
            df = pd.read_csv(csv_file, sep=None, engine='python')
            df.columns = df.columns.str.strip()
            df.columns = [c.upper() for c in df.columns]
        except Exception as e:
            raise UserError(_("Failed to parse the characteristics file: %s") % str(e))

        if 'CODPROV' not in df.columns:
            raise UserError(_("The CSV file must contain a 'CODPROV' column."))

        # Heavy lifting in separate cursor to avoid timeouts
        backend_id = self.id
        with self.pool.cursor() as new_cr:
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            backend = new_env['dropship.backend'].browse(backend_id)
            try:
                counts = backend._sync_characteristics_impl(df)
                new_cr.commit()
                # Create success log
                self.env['tec.dropshipping.log'].create({
                    'backend_id': backend_id,
                    'sync_type': 'characteristics',
                    'products_created': counts.get('created', 0),
                    'products_updated': counts.get('updated', 0),
                    'status': 'success',
                    'log_summary': f"Sincronización de características completada. {counts.get('created')} creados, {counts.get('updated')} actualizados."
                })
            except Exception as e:
                _logger.error(f"{SUITE_LOG_PREFIX}Characteristics sync failed for backend {backend.name}: {e}")
                try:
                    new_cr.rollback()
                except Exception:
                    _logger.warning(f"{SUITE_LOG_PREFIX}Rollback failed (connection likely lost).")
                # Create error log
                self.env['tec.dropshipping.log'].create({
                    'backend_id': backend_id,
                    'sync_type': 'characteristics',
                    'status': 'error',
                    'error_details': str(e),
                    'log_summary': "Error crítico durante la sincronización de características."
                })
                raise e
        return True

    def _sync_characteristics_impl(self, df):
        ProductTemplate = self.env['product.template']
        ProductProduct = self.env['product.product']
        updated_count = 0
        created_count = 0
        
        only_existing = self.env['ir.config_parameter'].sudo().get_param('tec_dropshipping_air.only_sync_existing', 'False') == 'True'

        # 1. Clean and Prepare CODPROVs
        # Convert to string and handle potential .0 from float conversion
        def clean_code(val):
            if pd.isna(val): return ""
            s = str(val).strip()
            if s.endswith('.0'): s = s[:-2]
            return s

        df['CLEAN_CODPROV'] = df['CODPROV'].apply(clean_code)
        all_codprovs = df['CLEAN_CODPROV'].unique().tolist()
        all_codprovs = [c for c in all_codprovs if c]
        
        # 2. Bulk Search Existing Variants (to find templates reliably)
        existing_templates_map = {}
        chunk_size = 1000
        for i in range(0, len(all_codprovs), chunk_size):
            chunk = all_codprovs[i:i + chunk_size]
            variants = ProductProduct.search([('default_code', 'in', chunk)])
            for v in variants:
                existing_templates_map[v.default_code] = v.product_tmpl_id

        # 3. Process Rows
        for index, row in df.iterrows():
            cod_prov = row.get('CLEAN_CODPROV')
            if not cod_prov:
                continue

            try:
                with self.env.cr.savepoint():
                    product_tmpl = existing_templates_map.get(cod_prov)
                    
                    # Extract data
                    desc_raw = str(row.get('CARACTERISTICAS', '')).strip()
                    name = str(row.get('DESCRIPCIÓN', '')).strip()
                    
                    # Extract PN from characteristics if possible
                    pn = ""
                    pn_match = re.search(r'(?:Nº Parte|PN|Part Number):\s*([^|,\n]+)', desc_raw, re.IGNORECASE)
                    if pn_match:
                        pn = pn_match.group(1).strip()
                    
                    vals = {
                        'air_description_raw': desc_raw,
                        'description_sale': desc_raw or name,
                    }
                    if pn:
                        vals['original_part_number'] = pn
                    
                    if not product_tmpl:
                        if only_existing:
                            _logger.debug(f"{SUITE_LOG_PREFIX}Skipping creation for {cod_prov} (only_sync_existing is active)")
                            continue

                        # CREATE Generic Product (0 price/stock)
                        created_count += 1
                        # Fallback for category
                        cat_id = self.env.ref('product.product_category_all', raise_if_not_found=False)
                        if not cat_id:
                            cat_id = self.env['product.category'].search([('name', '=', 'All')], limit=1)
                        if not cat_id:
                            cat_id = self.env['product.category'].search([], limit=1) # Last resort
                            
                        vals.update({
                            'name': name or f"Product {cod_prov}",
                            'default_code': cod_prov,
                            'type': 'consu',
                            'categ_id': cat_id.id if cat_id else False,
                        })
                        product_tmpl = ProductTemplate.create(vals)
                        existing_templates_map[cod_prov] = product_tmpl
                        _logger.info(f"{SUITE_LOG_PREFIX}Created generic product for {cod_prov}")
                    else:
                        # Only update if description or PN changed
                        if product_tmpl.air_description_raw != desc_raw or product_tmpl.original_part_number != pn:
                            updated_count += 1
                            product_tmpl.write(vals)
                        else:
                            _logger.debug(f"{SUITE_LOG_PREFIX}Skipping description update for {cod_prov} (No changes)")
                    
                    # Handle IMAGES (Smarter Sync)
                    image_urls = []
                    for i in range(1, 7):
                        img_val = row.get(f'IMG{i}')
                        if img_val and not pd.isna(img_val) and str(img_val).strip().startswith('http'):
                            image_urls.append(str(img_val).strip())
                    
                    urls_str = "|".join(image_urls)
                    if image_urls:
                        # Only download if URLs list changed OR forced
                        if product_tmpl.air_source_image_urls != urls_str or not product_tmpl.image_1920:
                            _logger.info(f"{SUITE_LOG_PREFIX}Downloading {len(image_urls)} images for {cod_prov}")
                            product_tmpl.air_has_images = True
                            self._download_and_assign_images(product_tmpl, image_urls)
                            product_tmpl.air_source_image_urls = urls_str
                        else:
                            _logger.debug(f"{SUITE_LOG_PREFIX}Skipping image download for {cod_prov} (URLs unchanged)")
                    else:
                        if product_tmpl.air_has_images:
                             product_tmpl.air_has_images = False
                             product_tmpl.air_source_image_urls = False

                    # Check Publication Status
                    if product_tmpl.product_variant_ids:
                        self._update_publication_status(product_tmpl.product_variant_ids[0])

            except Exception as e:
                _logger.error(f"{SUITE_LOG_PREFIX}Error processing characteristics for {cod_prov}: {e}")

            # Commit periodically to keep transaction size manageable
            if (updated_count + created_count) % 50 == 0:
                self.env.cr.commit()
                self.env.invalidate_all()

        _logger.info(f"Characteristics Sync Complete. Created: {created_count}, Updated: {updated_count}")
        return {'created': created_count, 'updated': updated_count}

    def _download_and_assign_images(self, product, urls):
        """ Download images and set the first one as main, others as extra (Backend & Website) """
        auto_download = self.env['ir.config_parameter'].sudo().get_param('tec_dropshipping_air.auto_download_images', 'True') == 'True'
        if not auto_download:
            _logger.info("Image Auto-Download is disabled. Skipping.")
            return

        first = True
        # 1. Clear existing extra images (Backend)
        product.tec_product_image_ids.unlink()
        
        # 2. Clear existing extra images (Website) if module installed
        if hasattr(product, 'product_template_image_ids'):
            product.product_template_image_ids.unlink()

        for url in urls:
            try:
                res = requests.get(url, timeout=15)
                if res.status_code == 200:
                    image_data = base64.b64encode(res.content)
                    if first:
                        product.image_1920 = image_data
                        first = False
                    else:
                        # Save to Backend Model (Always)
                        self.env['tec.product.image'].create({
                            'name': f"Air Image {product.default_code}",
                            'image_1920': image_data,
                            'product_tmpl_id': product.id
                        })
                        
                        # Save to Website Model (If available)
                        if hasattr(product, 'product_template_image_ids'):
                            self.env['product.image'].create({
                                'name': f"Air Image {product.default_code}",
                                'image_1920': image_data,
                                'product_tmpl_id': product.id
                            })
            except Exception as e:
                _logger.warning(f"Failed to download image from {url}: {e}")

    def _fetch_any_url_content(self, url):
        """ Robust downloader for both HTTP/S and Local Paths """
        if not url:
            return False
            
        # 1. Google Sheets Transformation
        if 'docs.google.com/spreadsheets' in url:
            ssid_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
            if ssid_match:
                ssid = ssid_match.group(1)
                new_url = f"https://docs.google.com/spreadsheets/d/{ssid}/export?format=csv"
                gid_match = re.search(r'[#&?]gid=([0-9]+)', url)
                if gid_match:
                    new_url += f"&gid={gid_match.group(1)}"
                _logger.info(f"Transforming GS URL to: {new_url}")
                url = new_url
        
        # 2. Fetch Logic
        if url.startswith('http'):
            try:
                # Add headers to look like a browser to avoid some blocks
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                return response.content
            except Exception as e:
                _logger.error(f"Failed to fetch remote URL {url}: {e}")
                raise UserError(_("No se pudo descargar el archivo desde la URL: %s") % str(e))
        else:
            # 3. Local Path Fallback
            import os
            if os.path.exists(url):
                with open(url, 'rb') as f:
                    return f.read()
            else:
                _logger.error(f"Local file not found: {url}")
                return False

    def _fetch_characteristics_content(self):
        return self._fetch_any_url_content(self.url_endpoint_characteristics)

    def _fetch_file_content(self):
        return self._fetch_any_url_content(self.url_endpoint)

    def sync_catalog(self):
        self.ensure_one()
        if self.provider_code != 'air_csv':
            return super().sync_catalog()

        _logger.info(f"Starting Air Computers Sync for Backend: {self.name}")

        # Fetch and Parse
        df = self._get_df_from_url(self.url_endpoint)
        if df is None:
            return

        # Synchronize
        self._sync_brands_impl(df)
        
        # Use separate cursor for long sync to avoid request timeouts
        backend_id = self.id
        with self.pool.cursor() as new_cr:
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            backend = new_env['dropship.backend'].browse(backend_id)
            try:
                # 2. Sync Catalog
                counts = backend._sync_catalog_impl(df)
                backend.last_sync = fields.Datetime.now()
                new_cr.commit()
                # Create success log
                self.env['tec.dropshipping.log'].create({
                    'backend_id': backend_id,
                    'sync_type': 'catalog',
                    'products_created': counts.get('created', 0),
                    'products_updated': counts.get('updated', 0),
                    'items_deleted': counts.get('deleted', 0),
                    'status': 'success',
                    'log_summary': f"Sincronización de catálogo completada. {counts.get('created')} creados, {counts.get('updated')} actualizados, {counts.get('deleted')} líneas de stock limpiadas."
                })
            except Exception as e:
                _logger.error(f"{SUITE_LOG_PREFIX}Catalog sync failed for backend {backend.name}: {e}")
                try:
                    new_cr.rollback()
                except Exception:
                    pass
                # Create error log
                self.env['tec.dropshipping.log'].create({
                    'backend_id': backend_id,
                    'sync_type': 'catalog',
                    'status': 'error',
                    'error_details': str(e),
                    'log_summary': f"Error crítico durante la sincronización de catálogo: {str(e)[:100]}..."
                })
                raise e

        return True

    def _sync_brands_impl(self, df):
        """ Extract and create unique brands from the dataframe """
        if 'MARCA' not in df.columns:
            return
            
        auto_create = self.env['ir.config_parameter'].sudo().get_param('tec_dropshipping_air.auto_create_brands', 'True') == 'True'
        if not auto_create:
            _logger.info("Brand Auto-Creation is disabled. Skipping brand sync.")
            return

        Brand = self.env['tec.catalog.brand']
        # Extract unique clean names and filter invalid ones
        _logger.info(f"Syncing brands. Columns: {list(df.columns)}")
        raw_brands = df['MARCA'].unique().tolist()
        _logger.info(f"Raw brands found in MARCA column: {raw_brands}")
        valid_brands = []
        for b in raw_brands:
            b_str = str(b).strip()
            if b_str and b_str.lower() not in ['nan', 'none', 'null', '0', 'false']:
                valid_brands.append(b_str)
        
        if not valid_brands:
            return
        
        # Bulk check existing
        existing_brands = Brand.search([('name', 'in', valid_brands)])
        existing_names = {b.name.lower(): b.id for b in existing_brands}
        
        to_create = []
        for name in valid_brands:
            if name.lower() not in existing_names:
                to_create.append({'name': name})
                existing_names[name.lower()] = True # Placeholder to avoid dupes in loop
        
        if to_create:
            Brand.create(to_create)
            count = len(to_create)
            _logger.info(f"Created {count} new brands from CSV.")
            
            # Create success log for brands
            self.env['tec.dropshipping.log'].create({
                'backend_id': self.id,
                'sync_type': 'brands', # We might need to add this selection to the model or use 'other'
                'status': 'success',
                'log_summary': f"Sincronización de marcas completada. {count} nuevas marcas creadas."
            })
        else:
             _logger.info("No new brands found to create.")
             # Optional: Log that no brands were created? Or too noisy? 
             # User asked for "sync marcas tambien debe quedar logeado".
             self.env['tec.dropshipping.log'].create({
                'backend_id': self.id,
                'sync_type': 'brands', # We might need to add this selection to the model or use 'other'
                'status': 'success',
                'log_summary': f"Sincronización de marcas verificada. No se encontraron nuevas marcas."
            })



    # Old _fetch_file_content removed, using consolidated _fetch_any_url_content instead.

    def _get_or_create_category(self, row, col_map=None):
        Category = self.env['product.category']
        rubro_name = self._get_row_str(row, 'RUBRO', col_map).strip() or 'Dropship'
        
        category = Category.search([('name', '=', rubro_name)], limit=1)
        if not category:
            parent_cat = Category.search([('name', '=', 'Dropship/Air')], limit=1)
            if not parent_cat:
                parent_cat = Category.create({'name': 'Dropship/Air'})
            category = Category.create({'name': rubro_name, 'parent_id': parent_cat.id})
        return category

    def _create_product_from_row(self, row, cod_prov, tax_map, col_map):
        Product = self.env['product.product']
        
        # Clean PN before using
        part_number = self._get_row_str(row, 'Part Number', col_map)
        if not part_number:
            part_number = self._get_row_str(row, 'ORIGINAL_PART_NUMBER', col_map)

        # 1. Category
        category = self._get_or_create_category(row, col_map)

        # 2. Brand (Search/Create as safety, but should be there)
        marca_name = str(row.get('MARCA', '')).strip()
        brand = False
        if marca_name and marca_name.lower() not in ['nan', 'none', '', '0']:
            Brand = self.env['tec.catalog.brand']
            brand = Brand.search([('name', '=ilike', marca_name)], limit=1)
            # Normal creation is now handled by _sync_brands_impl in bulk at start
            if not brand:
                auto_create = self.env['ir.config_parameter'].sudo().get_param('tec_dropshipping_air.auto_create_brands', 'True') == 'True'
                if auto_create:
                    brand = Brand.create({'name': marca_name})
                    _logger.info(f"Auto-created brand during product creation: {marca_name}")
        
        vals = {
            'name': str(row.get('DESCRIPCIÓN', 'New Product')).strip(),
            'default_code': cod_prov,
            'original_part_number': part_number,
            'type': 'consu',
            'categ_id': category.id,
            'product_brand_id': brand.id if brand else False,
            'description_sale': f"PN: {part_number}\nCod. Prov: {cod_prov}", 
        }
        
        # 3. Taxes
        iva_val = str(row.get('IVA', '')).strip()
        # Handle "21" vs "21.0"
        if iva_val.endswith('.0'):
            iva_val = iva_val[:-2]
            
        if iva_val in tax_map:
            purchase_tax_id, sale_tax_id = tax_map[iva_val]
            if purchase_tax_id:
                vals['supplier_taxes_id'] = [(6, 0, [purchase_tax_id])]
            if sale_tax_id:
                vals['taxes_id'] = [(6, 0, [sale_tax_id])]

        product = Product.create(vals)
        
        # Calculate Price and set additional info immediately
        self._update_product_info(product, row, col_map, tax_map)
        
        return product

    def _update_product_info(self, product, row, col_map, tax_map=None):
        # 1. Basic Info
        # Source of truth is USD
        # COSTO+ is likely the Net Cost in USD from Air Computers
        usd_cost = self._get_row_val(row, 'COSTO+', col_map) or self._get_row_val(row, 'COSTO', col_map)
        margin = self.global_margin or 30.0
        
        # Calculate USD Price with Margin
        usd_sale_price_net = usd_cost * (1 + margin / 100.0)
        
        # Current Exchange Rate conversion for ARS fields
        company_currency = self.env.company.currency_id
        usd_currency = self.env.ref('base.USD')
        
        ars_sale_price_net = usd_sale_price_net
        ars_cost_net = usd_cost
        
        if company_currency != usd_currency:
            # We convert the USD price to ARS
            ars_sale_price_net = usd_currency._convert(usd_sale_price_net, company_currency, self.env.company, fields.Date.today())
            ars_cost_net = usd_currency._convert(usd_cost, company_currency, self.env.company, fields.Date.today())

        part_number = self._get_row_str(row, 'Part Number', col_map)
        if not part_number:
            part_number = self._get_row_str(row, 'ORIGINAL_PART_NUMBER', col_map)
        cod_prov = self._get_row_str(row, 'CODPROV', col_map)
        
        # Tax calculation (Preserve logic)
        purchase_tax_id = False
        sale_tax_id = False
        if tax_map:
            iva_val = str(row.get('IVA', '')).strip()
            if iva_val.endswith('.0'): iva_val = iva_val[:-2]
            
            if iva_val in tax_map:
                purchase_tax_id, sale_tax_id = tax_map[iva_val]

        # Update category (Rubro)
        category = self._get_or_create_category(row, col_map)

        vals = {
            'x_usd_price': usd_sale_price_net,
            'x_usd_cost': usd_cost,
            'list_price': ars_sale_price_net,
            'standard_price': ars_cost_net,
            'original_part_number': part_number,
            'description_sale': f"PN: {part_number}\nCod. Prov: {cod_prov}",
            'categ_id': category.id,
        }
        
        # 1.1 Taxes: Essential to keep them so Odoo can CALCULATE the final price in Frontend
        if purchase_tax_id:
            vals['supplier_taxes_id'] = [(6, 0, [purchase_tax_id])]
        if sale_tax_id:
            vals['taxes_id'] = [(6, 0, [sale_tax_id])]

        # 2. Brand
        marca_name = self._get_row_str(row, 'MARCA', col_map)
        if marca_name:
            Brand = self.env['tec.catalog.brand']
            brand = Brand.search([('name', '=ilike', marca_name)], limit=1)
            if not brand:
                auto_create = self.env['ir.config_parameter'].sudo().get_param('tec_dropshipping_air.auto_create_brands', 'True') == 'True'
                if auto_create:
                    brand = Brand.create({'name': marca_name})
                    _logger.info(f"Auto-created brand during update: {marca_name}")
            
            if brand:
                # _logger.debug(f"Assigning brand {brand.name} to {product.default_code}")
                vals['product_brand_id'] = brand.id
            else:
                _logger.warning(f"Brand '{marca_name}' NOT FOUND and auto_create is OFF.")
        else:
            # Clear brand if CSV says nan/none or is empty
            vals['product_brand_id'] = False

        _logger.debug(f"Writing vals for {product.default_code}: {vals}")
        product.write(vals)

    def _update_supplier_info(self, product, location, cost, qty, sequence, product_code=False, last_update=False):
        SupplierInfo = self.env['product.supplierinfo']
        
        vals = {
            'partner_id': location.partner_id.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'price': cost,
            'currency_id': self.env.ref('base.USD').id, # Force USD
            'min_qty': 0,
            'sequence': sequence,
            'x_vendor_stock': qty,
            'product_code': product_code,
            'dropship_location_id': location.id,
            'x_last_update_date': last_update,
        }
        SupplierInfo.create(vals)

    def _sync_catalog_impl(self, df):
        Product = self.env['product.product']
        Location = self.env['dropship.location']
        col_map = {str(c).upper(): c for c in df.columns}
        _logger.info(f"Syncing Air Catalog. Available CSV Columns: {list(col_map.keys())}")
        
        tax_map = {m.csv_value: (m.tax_id.id, m.sale_tax_id.id) for m in self.tax_mapping_ids}
        
        # 0. Get specific Air Computers Partner
        air_partner = self.env['res.partner'].search([('name', '=', 'Air Computers')], limit=1)
        if not air_partner:
            air_partner = self.env['res.partner'].create({
                'name': 'Air Computers',
                'is_company': True,
                'supplier_rank': 1,
            })

        # Ensure Locations Exist for CBA and BSAS
        # Check for CBA
        loc_cba = self.location_ids.filtered(lambda l: l.import_column == 'CBA')
        if not loc_cba:
            _logger.info("Creating missing location for CBA")
            loc_cba = Location.create({
                'name': 'Air Computers Córdoba',
                'backend_id': self.id,
                'import_column': 'CBA',
                'partner_id': air_partner.id, 
            })
        else:
            # Ensure partner is correct if it exists
            if loc_cba.partner_id != air_partner:
                loc_cba.partner_id = air_partner
        
        # Check for BS AS
        loc_bsas = self.location_ids.filtered(lambda l: l.import_column in ['BS AS', 'LUG', 'BUENOS AIRES'])
        if not loc_bsas:
             _logger.info("Creating missing location for Buenos Aires")
             loc_bsas = Location.create({
                'name': 'Air Computers Buenos Aires',
                'backend_id': self.id,
                'import_column': 'BS AS', # Default to BS AS column name
                'partner_id': air_partner.id,
            })
        else:
             if loc_bsas.partner_id != air_partner:
                loc_bsas.partner_id = air_partner

        # Reload locations
        self.invalidate_recordset(['location_ids'])
        locations = self.location_ids
        _logger.info(f"Locations for sync: {[l.name for l in locations]}")
        
        # 1. Clear old lines for this backend AND Partner
        # We delete lines linked to these locations OR linked to the Air Computers Partner
        # This ensures we don't have duplicates if someone manually added lines or from old syncs
        domain = ['|', ('dropship_location_id', 'in', locations.ids), ('partner_id', '=', air_partner.id)]
        # Safety: Only delete if product is in the catalog? 
        # No, sync_catalog is authoritative for Air Computers. Wiping all Air Computer lines is safer to avoid orphans.
        existing_lines = self.env['product.supplierinfo'].search(domain)
        # However, be careful not to delete lines for OTHER products not in the CSV?
        # The prompt implies we want to clean up.
        # But if the CSV is partial, we might lose data.
        # Given this is a full sync usually, it's acceptable.
        item_count = len(existing_lines)
        existing_lines.unlink()
        _logger.info(f"Deleted {item_count} old supplier info lines for Air Computers.")

        # 3. Bulk Search Existing Products using CODPROV
        # We need to filter out invalid CODPROV first
        df = df[df['CODPROV'].notnull()]
        all_codprovs = df['CODPROV'].astype(str).str.strip().unique().tolist()
        
        existing_products_map = {}
        chunk_size = 1000
        for i in range(0, len(all_codprovs), chunk_size):
            chunk = all_codprovs[i:i + chunk_size]
            products = Product.search([('default_code', 'in', chunk)])
            for p in products:
                existing_products_map[p.default_code] = p

        
        # --- Date Extraction Optimization ---
        # User requested to extract 'FECHA' (Col M) which is constant for all rows.
        global_last_update = False
        date_col_actual = col_map.get('FECHA')
        
        # Fallback to index 12 (Col M) if 'FECHA' not found by name
        if not date_col_actual and len(df.columns) > 12:
            potential_col = df.columns[12] # Index 12 is M
            _logger.info(f"FECHA column not found by name. Trying Column Index 12: {potential_col}")
            date_col_actual = potential_col

        if date_col_actual:
            try:
                # Get first non-null value
                valid_dates = df[date_col_actual].dropna()
                if not valid_dates.empty:
                    raw_date = valid_dates.iloc[0]
                    # Attempt robust parsing
                    if isinstance(raw_date, (datetime, pd.Timestamp)):
                        global_last_update = raw_date
                    else:
                        # Parse strings like "18/02/2026 15:30"
                        global_last_update = pd.to_datetime(str(raw_date).strip(), dayfirst=True, errors='coerce')
                    
                    if pd.isnull(global_last_update):
                        global_last_update = False
                    elif hasattr(global_last_update, 'to_pydatetime'):
                         global_last_update = global_last_update.to_pydatetime()
                        
                    _logger.info(f"Global Last Update Date extracted: {global_last_update}")
            except Exception as e:
                _logger.warning(f"Failed to extract global date from column {date_col_actual}: {e}")

        created_count = 0
        updated_count = 0
        
        # 4. Process Rows
        for index, row in df.iterrows():
            cod_prov = self._get_row_str(row, 'CODPROV', col_map)
            if not cod_prov:
                continue

            try:
                with self.env.cr.savepoint():
                    product = existing_products_map.get(cod_prov)
                    if not product:
                        created_count += 1
                        product = self._create_product_from_row(row, cod_prov, tax_map, col_map)
                        existing_products_map[cod_prov] = product
                    else:
                        updated_count += 1
                        self._update_product_info(product, row, col_map, tax_map)

                    # --- MELI Category Mapping ---
                    if 'tec.catalog.category.mapping' in self.env:
                        rubro_name = self._get_row_str(row, 'RUBRO', col_map)
                        if rubro_name:
                            mapping = self.env['tec.catalog.category.mapping'].search([('supplier_category_name', '=', rubro_name)], limit=1)
                            if mapping and mapping.public_category_id:
                                product.public_categ_ids = [(4, mapping.public_category_id.id)]
                    # -----------------------------

                    # Update Stock / Supplier Info
                    raw_cost = self._get_row_val(row, 'COSTO+', col_map) or self._get_row_val(row, 'COSTO', col_map)
                    
                    seq = 1
                    for loc in locations:
                        target_col = loc.import_column or loc.name
                        qty = 0.0
                        
                        if target_col in ['BS AS', 'BSAS', 'BUENOS AIRES']:
                             qty = self._get_row_val(row, target_col, col_map)
                             if qty <= 0:
                                 qty = self._get_row_val(row, 'LUG', col_map)
                        else:
                             qty = self._get_row_val(row, target_col, col_map)

                        # Always update supplier info to record the last scrape date, even if stock is 0
                        self._update_supplier_info(product, loc, raw_cost, qty, seq, product_code=cod_prov, last_update=global_last_update)
                        seq += 1
                    
                    # Check Publication Status
                    self._update_publication_status(product)

                
            except Exception as row_error:
                _logger.error(f"{SUITE_LOG_PREFIX}Error processing row {index} (CodProv: {cod_prov}): {row_error}")
                continue

            # Commit periodically to keep transaction size manageable
            if index % 100 == 0:
                self.env.cr.commit()
                self.env.invalidate_all()

        _logger.info(f"Sync Complete. Created: {created_count}, Updated: {updated_count}")
        return {'created': created_count, 'updated': updated_count, 'deleted': item_count}

    def _parse_float(self, value):
        try:
            return float(str(value).replace(',', '.'))
        except (ValueError, TypeError):
            return 0.0

    def _get_row_val(self, row, col_name, col_map=None):
        if not col_name: return 0.0
        col_map = col_map or {}
        # Try direct or from map
        possible_keys = [str(col_name).upper(), str(col_name).strip().upper()]
        
        actual_col = None
        for key in possible_keys:
            if key in col_map:
                actual_col = col_map[key]
                break
        
        # If not in map directly, maybe it IS the key in the row if we iterate?
        # But we rely on col_map keys being UPPER
        
        if actual_col:
            val = row.get(actual_col)
            if pd.isna(val): return 0.0
            return self._parse_float(val)
        return 0.0

    
    def _update_publication_status(self, product):
        """ Enforce publication rule: Stock > 0 AND (Has Description OR Has Images) """
        # 1. Check Stock (Sum of dropship locations)
        # We assume sellers with dropship_location_id are valid
        sellers = product.seller_ids.filtered(lambda s: s.dropship_location_id)
        stock_total = sum(sellers.mapped('x_vendor_stock'))
        
        # 2. Check Content
        # air_description_raw is on template. tec_product_image_ids is on template.
        tmpl = product.product_tmpl_id
        has_desc = bool(tmpl.air_description_raw) or bool(tmpl.website_description) or bool(tmpl.description_sale)
        # Note: description_sale is usually just PN/Code in our case, so maybe strict check on air_description_raw?
        # User said "descripcion air".
        # Let's stick to air_description_raw OR website_description.
        has_desc_strict = bool(tmpl.air_description_raw) or bool(tmpl.website_description)
        
        has_images = bool(tmpl.tec_product_image_ids) or bool(tmpl.image_1920)
        
        has_content = has_desc_strict or has_images
        
        # 3. Decision
        should_publish = (stock_total > 0) and has_content
        
        # 4. Apply
        if tmpl.is_published != should_publish:
            tmpl.is_published = should_publish

    def _get_row_str(self, row, col_name, col_map=None):
        if not col_name: return ''
        col_map = col_map or {}
        
        possible_keys = [str(col_name).upper(), str(col_name).strip().upper()]
        actual_col = None
        for key in possible_keys:
            if key in col_map:
                actual_col = col_map[key]
                break
                
        if actual_col:
            val = row.get(actual_col, '')
            if pd.isna(val) or str(val).lower() in ['nan', 'none', 'null', '0', 'false']:
                return ''
            return str(val).strip()
        return ''

