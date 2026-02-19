from odoo import api, fields, models
from .enrichment_engines import lenovo_engine, icecat_engine, google_engine, youtube_engine, ai_engine
import logging

_logger = logging.getLogger(__name__)
SUITE_LOG_PREFIX = "[Tec Suite] Brain Hub: "

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    external_product_url = fields.Char(string="URL Ficha Oficial", help="Link a la página oficial del fabricante.")
    icecat_product_url = fields.Char(string="URL Icecat", help="Link directo a la ficha en Icecat.")
    lenovo_datasheet_url = fields.Char(string="URL Datasheet Lenovo", help="Link al PDF oficial de Lenovo.")

    # Modified: Remove CREATE override that sets MPN = default_code
    # Because in Dropshipping default_code IS Supplier SKU, not MPN
    # We rely on specific dropshipping modules to set original_part_number



    def action_fetch_technical_data(self):
        """ Fetch data from multiple sources. Non-waterfall (Additive). """
        ICP = self.env['ir.config_parameter'].sudo()
        total = len(self)
        success_count = 0
        
        for product in self:
            # 1. Protection: Skip if already enriched, unless "Force" is checked
            if product.enrichment_state in ['tech_done', 'full_enriched'] and not product.force_enrichment:
                _logger.info(f"{SUITE_LOG_PREFIX}Skipping {product.name} (Already Enriched)")
                continue

            mpn = product.original_part_number or product.default_code
            if not mpn:
                continue

            success_sources = []

            # 1. Lenovo PSREF
            if product.product_brand_id.name and 'lenovo' in product.product_brand_id.name.lower():
                try:
                    with self.env.cr.savepoint():
                        if lenovo_engine.enrich_product(product, mpn):
                            success_sources.append('lenovo')
                            self._log_enrichment(product, 'success', 'Lenovo PSREF', 'Datos técnicos e imágenes actualizados.')
                        else:
                            product.message_post(body="ℹ️ <b>Lenovo PSREF:</b> Producto no encontrado en base oficial.")
                except Exception as e:
                    _logger.error(f"Lenovo Engine Failed: {e}")
                    product.message_post(body=f"❌ <b>Lenovo PSREF Error:</b> {str(e)}")
            
            # 2. Icecat
            if ICP.get_param('tec_catalog_enricher.use_icecat'):
                try:
                    with self.env.cr.savepoint():
                        if icecat_engine.enrich_product(product, mpn):
                            success_sources.append('icecat')
                            self._log_enrichment(product, 'success', 'Icecat', 'Datos técnicos e imágenes actualizados.')
                        else:
                             product.message_post(body="ℹ️ <b>Icecat:</b> Producto no encontrado en catálogo.")
                except Exception as e:
                    _logger.error(f"Icecat Engine Failed: {e}")
                    product.message_post(body=f"❌ <b>Icecat Error:</b> {str(e)}")

            # 3. Google Fallback
            if not success_sources and ICP.get_param('tec_catalog_enricher.use_google'):
                try:
                    with self.env.cr.savepoint():
                        if google_engine.enrich_product(product, mpn):
                            success_sources.append('google')
                            self._log_enrichment(product, 'success', 'Google', 'Datos básicos obtenidos.')
                        else:
                            product.message_post(body="ℹ️ <b>Google Fallback:</b> Sin resultados útiles.")
                except Exception as e:
                    _logger.error(f"Google Engine Failed: {e}")
                    product.message_post(body=f"❌ <b>Google Error:</b> {str(e)}")

            # Update final state & Logs
            if success_sources:
                success_count += 1
                product.enrichment_state = 'tech_done'
                if len(success_sources) > 1:
                    product.enrichment_source = 'mixed'
                else:
                    product.enrichment_source = success_sources[0]
                
                # Reset force flag
                product.force_enrichment = False
                
                # Simple Success Log
                sources_label = ", ".join([s.capitalize() for s in success_sources])
                body = f"✅ <b>Enriquecimiento Exitoso:</b> Se obtuvo información técnica desde: <b>{sources_label}</b>."
                product.message_post(body=body)
            else:
                # No data found at all
                msg = "No se encontró información técnica en ninguna de las fuentes consultadas."
                self._log_enrichment(product, 'warning', 'Sincronizador', msg)
                
                # Simple Warning Log
                body = f"⚠️ <b>Sin Resultados:</b> Se consultaron todas las fuentes pero no se hallaron datos para el PN: <b>{mpn}</b>."
                product.message_post(body=body)

        # Final Summary Notification for Mass Action
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Proceso de Enriquecimiento Finalizado',
                'message': f'Se procesaron {total} productos. Éxitos: {success_count} | Fallidos: {total - success_count}',
                'type': 'success' if success_count > 0 else 'warning',
                'sticky': False,
            }
        }
    
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
