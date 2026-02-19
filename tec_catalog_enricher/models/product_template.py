from odoo import api, fields, models
from .enrichment_engines import lenovo_engine, icecat_engine, google_engine, youtube_engine, ai_engine
import logging

_logger = logging.getLogger(__name__)
SUITE_LOG_PREFIX = "[Tec Suite] Brain Hub: "

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # --- Enrichment Control ---
    enrichment_state = fields.Selection([
        ('draft', 'Pending'),
        ('tech_done', 'Tech Info OK'),
        ('marketing_done', 'Marketing OK'),
        ('full_enriched', 'Fully Enriched')
    ], string="Enrichment Status", default='draft', tracking=True)

    enrichment_source = fields.Selection([
        ('manual', 'Manual'),
        ('lenovo', 'Lenovo PSREF'),
        ('icecat', 'Open Icecat'),
        ('google', 'Google Fallback'),
        ('ai', 'IA Generada'),
        ('mixed', 'Fuentes Mixtas')
    ], string="Fuente de Datos", readonly=True, copy=False)

    external_product_url = fields.Char(string="URL Ficha Oficial", help="Link a la página oficial del fabricante.")
    icecat_product_url = fields.Char(string="URL Icecat", help="Link directo a la ficha en Icecat.")
    lenovo_datasheet_url = fields.Char(string="URL Datasheet Lenovo", help="Link al PDF oficial de Lenovo.")
    support_search_url = fields.Char(string="URL Soporte", compute='_compute_support_url', help="Link dinámico de búsqueda de drivers/soporte.")
    force_enrichment = fields.Boolean(string="Forzar Actualización", help="Si se marca, permite sobrescribir datos existentes.")

    # Modified: Remove CREATE override that sets MPN = default_code
    # Because in Dropshipping default_code IS Supplier SKU, not MPN
    # We rely on specific dropshipping modules to set original_part_number


    @api.depends('product_brand_id', 'original_part_number')
    def _compute_support_url(self):
        for product in self:
            if product.product_brand_id and product.original_part_number:
                query = f"support {product.product_brand_id.name} {product.original_part_number} drivers"
                product.support_search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            else:
                product.support_search_url = False

    def action_fetch_technical_data(self):
        """ Fetch data from multiple sources. Non-waterfall (Additive). """
        ICP = self.env['ir.config_parameter'].sudo()
        for product in self:
            mpn = product.original_part_number or product.default_code
            if not mpn:
                continue

            success_sources = []

            # 1. Lenovo PSREF (Specialist)
            if product.product_brand_id.name and 'lenovo' in product.product_brand_id.name.lower():
                _logger.info(f"{SUITE_LOG_PREFIX}Enriching {mpn} via Lenovo PSREF")
                try:
                    with self.env.cr.savepoint():
                        if lenovo_engine.enrich_product(product, mpn):
                            success_sources.append('lenovo')
                            self._log_enrichment(product, 'success', 'Lenovo PSREF', 'Datos técnicos e imágenes actualizados.')
                        else:
                            self._log_enrichment(product, 'warning', 'Lenovo PSREF', 'No se encontraron datos en PSREF.')
                except Exception as e:
                    _logger.error(f"Lenovo Engine Failed: {e}")
                    self._log_enrichment(product, 'error', 'Lenovo PSREF', f'Error crítico: {str(e)}')
            
            # 2. Icecat (Standard)
            if ICP.get_param('tec_catalog_enricher.use_icecat'):
                _logger.info(f"{SUITE_LOG_PREFIX}Enriching {mpn} via Icecat")
                try:
                    with self.env.cr.savepoint():
                        if icecat_engine.enrich_product(product, mpn):
                            success_sources.append('icecat')
                            self._log_enrichment(product, 'success', 'Icecat', 'Datos técnicos e imágenes actualizados.')
                        else:
                             self._log_enrichment(product, 'warning', 'Icecat', 'Producto no encontrado o error de conexión.')
                except Exception as e:
                    _logger.error(f"Icecat Engine Failed: {e}")
                    self._log_enrichment(product, 'error', 'Icecat', f'Error crítico: {str(e)}')

            # 3. Google (Fallback) - Only if no hard data was found yet? 
            # Or always? User says "Hacer los dos y luego depuro". 
            # Let's run Google only if nothing else found to avoid too much noise, or per user preference.
            # For now, following "do both", let's keep waterfall for google or run it too.
            if not success_sources and ICP.get_param('tec_catalog_enricher.use_google'):
                try:
                    with self.env.cr.savepoint():
                        if google_engine.enrich_product(product, mpn):
                            success_sources.append('google')
                            self._log_enrichment(product, 'success', 'Google', 'Datos básicos obtenidos.')
                        else:
                            self._log_enrichment(product, 'warning', 'Google', 'Búsqueda sin resultados útiles.')
                except Exception as e:
                    _logger.error(f"Google Engine Failed: {e}")
                    self._log_enrichment(product, 'error', 'Google', f'Error crítico: {str(e)}')

            # Update final state based on all sources
            if success_sources:
                product.enrichment_state = 'tech_done'
                if len(success_sources) > 1:
                    product.enrichment_source = 'mixed'
                else:
                    product.enrichment_source = success_sources[0]
    
    def action_generate_marketing_content(self):
        """ Soft Data + Social Proof: YouTube -> Gemini AI """
        ICP = self.env['ir.config_parameter'].sudo()
        for product in self:
            state = 'tech_done'
            
            # 1. YouTube Social Proof
            if ICP.get_param('tec_catalog_enricher.use_youtube'):
                if youtube_engine.enrich_video(product):
                    state = 'marketing_done'

            # 2. Gemini AI Marketing
            if ICP.get_param('tec_catalog_enricher.use_gemini'):
                if ai_engine.enrich_marketing(product):
                     state = 'marketing_done'
            
            if state == 'marketing_done':
                # Check complete status
                if product.enrichment_state == 'tech_done':
                    product.enrichment_state = 'full_enriched'
                else:
                    product.enrichment_state = 'marketing_done'
                product.enrichment_source = 'mixed'

    def _cron_notify_price_drops(self):
        """ Task for daily price drop notifications """
        _logger.info(f"{SUITE_LOG_PREFIX}Running Price Drop Notification Cron")
        # Logic to be implemented: 
        # 1. Identify products with price drops
        # 2. Find carts with these products
        # 3. Send email notifications
        pass

    def _log_enrichment(self, product, level, source, message):
        """ Helper to log enrichment actions """
        try:
             # status map: 'success' -> 'success', 'warning' -> 'partial', 'error' -> 'error'
             status_map = {'success': 'success', 'warning': 'partial', 'error': 'error'}
             
             self.env['tec.dropshipping.log'].create({
                'sync_type': 'enrichment',
                'status': status_map.get(level, 'error'), 
                'log_summary': f"[Enrichment: {source}] {product.name} ({product.original_part_number}): {message}"
            })
        except Exception as e:
            _logger.warning(f"Failed to create enrichment log: {e}")

    def action_open_website(self):
        self.ensure_one()
        action = self.env.ref('website.action_website_preview', raise_if_not_found=False)
        return action.read()[0] if action else {'type': 'ir.actions.act_window_close'}
