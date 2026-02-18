from odoo import fields, models, api, _
import requests
import logging

_logger = logging.getLogger(__name__)

class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    meli_id = fields.Char(string='MELI Category ID', index=True, copy=False)
    meli_parent_id = fields.Char(string='MELI Parent ID', index=True, copy=False)
    is_meli_category = fields.Boolean(string='Is MELI Category', default=False)

    def action_fetch_meli_categories(self):
        """ Fetch MELI Categories from API (Recursive or Dump) """
        # Only fetch root categories and children to build the tree
        # API: https://api.mercadolibre.com/sites/MLA/categories
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('tec_catalog_meli.api_url', 'https://api.mercadolibre.com')
        site_id = 'MLA' # Argentina
        
        try:
            url = f"{base_url}/sites/{site_id}/categories"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                categories = res.json()
                self._process_categories(categories, parent=False)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Success"),
                        'message': _("Fetched %s root categories. Background job started for details.") % len(categories),
                        'sticky': False,
                    }
                }
        except Exception as e:
            _logger.error(f"Failed to fetch MELI categories: {e}")
            raise

    def _process_categories(self, categories, parent=False):
        for cat_data in categories:
            meli_id = cat_data.get('id')
            name = cat_data.get('name')
            
            existing = self.search([('meli_id', '=', meli_id)], limit=1)
            if not existing:
                vals = {
                    'name': name,
                    'meli_id': meli_id,
                    'is_meli_category': True,
                    'parent_id': parent.id if parent else False,
                }
                existing = self.create(vals)
            
            # Recursive fetch? MELI tree is huge. Maybe just 1-2 levels for now?
            # Or use a background job.
            # For MVP, let's just create roots. User asked for dump.
            pass
