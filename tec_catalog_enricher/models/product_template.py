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
        """ Hard Data Waterfall: Lenovo -> Icecat -> Google """
        ICP = self.env['ir.config_parameter'].sudo()
        for product in self:
            mpn = product.original_part_number or product.default_code
            if not mpn:
                continue

            # 1. Lenovo PSREF (Specialist) - No toggle yet as it's built-in
            if product.product_brand_id.name and 'lenovo' in product.product_brand_id.name.lower():
                _logger.info(f"{SUITE_LOG_PREFIX}Enriching {mpn} via Lenovo PSREF")
                if lenovo_engine.enrich_product(product, mpn):
                    product.enrichment_source = 'lenovo'
                    product.enrichment_state = 'tech_done'
                    continue
            
            # 2. Icecat (Standard)
            if ICP.get_param('tec_catalog_enricher.use_icecat'):
                _logger.info(f"{SUITE_LOG_PREFIX}Enriching {mpn} via Icecat")
                if icecat_engine.enrich_product(product, mpn):
                    product.enrichment_source = 'icecat'
                    product.enrichment_state = 'tech_done'
                    continue

            # 3. Google (Fallback)
            if ICP.get_param('tec_catalog_enricher.use_google'):
                if google_engine.enrich_product(product, mpn):
                    product.enrichment_source = 'google'
                    product.enrichment_state = 'tech_done'
    
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

    def action_open_website(self):
        self.ensure_one()
        action = self.env.ref('website.action_website_preview', raise_if_not_found=False)
        return action.read()[0] if action else {'type': 'ir.actions.act_window_close'}
