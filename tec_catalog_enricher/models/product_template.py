from odoo import api, fields, models
from .enrichment_engines import lenovo_engine, icecat_engine, bestbuy_engine, open_product_data_engine, google_engine, youtube_engine, ai_engine
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
        
        # Performance: If it's a mass action, we should be careful with timeouts
        # For very large sets, Odoo usually times out after 60-120s.
        _logger.info(f"{SUITE_LOG_PREFIX}Starting enrichment for {total} products")

        for product in self:
            try:
                # 1. Protection: Skip if already enriched, unless "Force" is checked
                if product.enrichment_state in ['tech_done', 'full_enriched'] and not product.force_enrichment:
                    _logger.info(f"{SUITE_LOG_PREFIX}Skipping {product.name} (Already Enriched)")
                    continue

                mpn = product.original_part_number or product.default_code
                if not mpn:
                    continue

                success_sources = []
                failed_sources = []
                error_sources = []

                # Use a specific savepoint per product so one failure doesn't roll back the whole batch
                with self.env.cr.savepoint():
                    # 1. Lenovo PSREF
                    if ICP.get_param('tec_catalog_enricher.use_lenovo_psref', 'True') == 'True' and product.product_brand_id.name and 'lenovo' in product.product_brand_id.name.lower():
                        try:
                            if lenovo_engine.enrich_product(product, mpn):
                                success_sources.append('Lenovo PSREF')
                                self._log_enrichment(product, 'success', 'Lenovo PSREF', 'Datos técnicos e imágenes actualizados.')
                            else:
                                failed_sources.append('Lenovo PSREF')
                        except Exception as e:
                            _logger.error(f"Lenovo Engine Failed: {e}")
                            error_sources.append(f'Lenovo PSREF ({str(e)[:30]})')
                    
                    # 2. Icecat
                    if ICP.get_param('tec_catalog_enricher.use_icecat'):
                        try:
                            if icecat_engine.enrich_product(product, mpn):
                                success_sources.append('Icecat')
                                self._log_enrichment(product, 'success', 'Icecat', 'Datos técnicos e imágenes actualizados.')
                            else:
                                failed_sources.append('Icecat')
                        except Exception as e:
                            _logger.error(f"Icecat Engine Failed: {e}")
                            error_sources.append(f'Icecat ({str(e)[:30]})')

                    # 3. Best Buy API
                    if not success_sources and ICP.get_param('tec_catalog_enricher.use_bestbuy'):
                        try:
                            if bestbuy_engine.enrich_product(product, mpn):
                                success_sources.append('Best Buy')
                                self._log_enrichment(product, 'success', 'Best Buy', 'Datos técnicos e imágenes actualizados.')
                            else:
                                failed_sources.append('Best Buy')
                        except Exception as e:
                            _logger.error(f"BestBuy Engine Failed: {e}")
                            error_sources.append(f'Best Buy ({str(e)[:30]})')

                    # 4. Product Open Data (POD)
                    if not success_sources and ICP.get_param('tec_catalog_enricher.use_pod'):
                        try:
                            if open_product_data_engine.enrich_product(product, mpn, ean=product.barcode):
                                success_sources.append('Product Open Data')
                                self._log_enrichment(product, 'success', 'Open Product Data', 'Información encontrada en base abierta.')
                            else:
                                failed_sources.append('Product Open Data')
                        except Exception as e:
                            _logger.error(f"POD Engine Failed: {e}")
                            error_sources.append(f'Product Open Data ({str(e)[:30]})')

                    # 5. Google Fallback (AI Web Search)
                    if not success_sources and ICP.get_param('tec_catalog_enricher.use_google'):
                        try:
                            if google_engine.enrich_product(product, mpn):
                                success_sources.append('Google AI Search')
                                self._log_enrichment(product, 'success', 'Google', 'Datos básicos (y texto AI) obtenidos.')
                            else:
                                failed_sources.append('Google AI Search')
                        except Exception as e:
                            _logger.error(f"Google Engine Failed: {e}")
                            error_sources.append(f'Google AI Search ({str(e)[:30]})')

                    # Update final state & Logs
                    if success_sources:
                        success_count += 1
                        product.enrichment_state = 'tech_done'
                        product.enrichment_source = 'mixed' if len(success_sources) > 1 else success_sources[0].lower()
                        product.force_enrichment = False
                        
                        sources_label = ", ".join(success_sources)
                        failed_label = ", ".join(failed_sources) if failed_sources else 'Ninguna'
                        
                        body = f"📥 Ficha Técnica Obtenida<br/>✅ Fuentes Exitosas: {sources_label}<br/>ℹ️ Omitidas / Sin datos: {failed_label}"
                        if error_sources:
                            body += f'<br/>❌ Errores técnicos: {", ".join(error_sources)}'
                        product.message_post(body=body)
                    else:
                        msg = "No se encontró información técnica en ninguna de las fuentes consultadas."
                        self._log_enrichment(product, 'warning', 'Sincronizador', msg)
                        
                        failed_label = ", ".join(failed_sources) if failed_sources else "ninguna (deshabilitadas)"
                        body = f"⚠️ Sin Resultados Técnicos<br/>Se buscaron datos en {failed_label} pero no se obtuvieron resultados para el PN {mpn}."
                        if error_sources:
                            body += f'<br/>❌ Errores técnicos: {", ".join(error_sources)}'
                        product.message_post(body=body)

                # IMPORTANT: In mass actions, commit after each product so:
                # 1. We don't lose work if the whole request times out.
                # 2. The user can see progress in the logs if they open another tab.
                if total > 1:
                    self.env.cr.commit()

            except Exception as product_error:
                _logger.error(f"Critical error processing product {product.id}: {product_error}")
                continue

        # Final Summary Notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Proceso de Enriquecimiento Finalizado',
                'message': f'Se procesaron {total} productos. Éxitos: {success_count} | Fallidos: {total - success_count}',
                'type': 'success' if success_count > 0 else 'warning',
                'sticky': True, # Keep it visible for mass actions
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }
    
    def action_generate_marketing_content(self):
        """ Soft Data + Social Proof: YouTube -> Gemini AI """
        ICP = self.env['ir.config_parameter'].sudo()
        total = len(self)
        success_count = 0

        for product in self:
            try:
                with self.env.cr.savepoint():
                    state = 'tech_done'
                    logs = []
                    
                    # 1. YouTube Social Proof
                    if ICP.get_param('tec_catalog_enricher.use_youtube'):
                        if youtube_engine.enrich_video(product):
                            state = 'marketing_done'
                            logs.append("🎬 YouTube: Video y tags obtenidos exitosamente.")

                    # 2. Gemini AI Marketing
                    if ICP.get_param('tec_catalog_enricher.use_gemini'):
                        if ai_engine.enrich_marketing(product):
                             state = 'marketing_done'
                             provider = ICP.get_param('tec_catalog_enricher.ai_provider', 'gemini')
                             if provider == 'openai':
                                 model = ICP.get_param('tec_catalog_enricher.openai_model') or 'gpt-4.1-nano'
                                 provider_name = 'OpenAI'
                             else:
                                 model = ICP.get_param('tec_catalog_enricher.gemini_model') or 'gemini-2.0-flash'
                                 provider_name = 'Google Gemini'
                             logs.append(f"✨ IA Marketing: Descripción generada exitosamente usando {provider_name} ({model}).")
                    
                    if state == 'marketing_done':
                        success_count += 1
                        # Check complete status
                        if product.enrichment_state == 'tech_done':
                            product.enrichment_state = 'full_enriched'
                        else:
                            product.enrichment_state = 'marketing_done'
                        product.enrichment_source = 'mixed'
                        # Reset force
                        product.force_enrichment = False

                        # Log everything to chatter
                        logs_html = "<br/>".join([f"✔️ {log}" for log in logs])
                        body = f"✨ Marketing Generado Exitosamente<br/>{logs_html}"
                        product.message_post(body=body)
                    else:
                        body = "⚠️ Generación de Marketing<br/>No se obtuvieron resultados o las integraciones están deshabilitadas."
                        product.message_post(body=body)

                # Individual commit for mass actions
                if total > 1:
                    self.env.cr.commit()

            except Exception as e:
                _logger.error(f"Failed to generate marketing for product {product.id}: {e}")
                continue

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Contenido de Marketing Generado',
                'message': f'Se procesaron {total} productos. Éxitos: {success_count}',
                'type': 'success',
                'sticky': total > 1,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            }
        }

    @api.model
    def _cron_mass_enrich_catalog(self, limit=50):
        """ Task for automated background mass enrichment of High-Ticket categories """
        _logger.info(f"{SUITE_LOG_PREFIX}Running Mass Catalog Enrichment Cron (limit: {limit})...")
        
        # We only want to auto-process products that:
        # 1. Are active
        # 2. Have actual MPN or Supplier SKU to search for
        # 3. Are pending enrichment
        # 4. Have some stock (priority) or as configured. 
        # (Keeping it simple: just need MPN and 'pending' enrichment state)
        domain = [
            ('enrichment_state', 'in', ['pending', False]),
            ('type', '=', 'product'),
            '|', ('original_part_number', '!=', False), ('default_code', '!=', False)
        ]
        
        # Priority High-Ticket categories names
        high_ticket_names = [
            'Notebooks', 'PCs', 'Computadoras', 'Mini PCs', 'Servidores', 
            'Monitores', 'Impresoras', 'Periféricos Gamers', 'Videovigilancia'
        ]
        
        # Try to find these categories first
        categories = self.env['product.category'].search([('name', 'in', high_ticket_names)])
        if categories:
             domain.append(('categ_id', 'child_of', categories.ids))
             
        products = self.search(domain, limit=limit)
        
        if not products:
             _logger.info(f"{SUITE_LOG_PREFIX}No pending priority products found for auto-enrichment.")
             return

        _logger.info(f"{SUITE_LOG_PREFIX}Found {len(products)} pending products. Starting process...")
        
        # Chain both actions. The methods already have robust savepoints to prevent complete rollback.
        products.action_fetch_technical_data()
        products.action_generate_marketing_content()
        
        _logger.info(f"{SUITE_LOG_PREFIX}Mass Catalog Enrichment Cron completed.")

    def _cron_notify_price_drops(self):
        """ Task for daily price drop notifications """
        _logger.info(f"{SUITE_LOG_PREFIX}Running Price Drop Notification Cron")
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
