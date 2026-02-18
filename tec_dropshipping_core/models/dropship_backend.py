from odoo import models, fields, api

class DropshipBackend(models.Model):
    _name = 'dropship.backend'
    _description = 'Dropshipping Backend Strategy'

    name = fields.Char(required=True)
    provider_code = fields.Selection([], string='Provider Code', required=True)
    
    url_endpoint = fields.Char(string='URL Endpoint', help='URL to fetch the catalog file (CSV/XLSX)')
    global_margin = fields.Float(string='Global Margin (%)', default=30.0, help='Margin to apply to the cost to calculate list price.')
    
    tax_mapping_ids = fields.One2many('dropship.tax.map', 'backend_id', string='Tax Mappings')
    location_ids = fields.One2many('dropship.location', 'backend_id', string='Locations')
    
    cron_id = fields.Many2one('ir.cron', string='Auto-Sync Cron')
    last_sync = fields.Datetime(string='Last Sync')
    
    sync_log_ids = fields.One2many('tec.dropshipping.log', 'backend_id', string='Sync Logs')
    sync_log_count = fields.Integer(string='Logs Count', compute='_compute_sync_log_count')

    def _compute_sync_log_count(self):
        for backend in self:
            backend.sync_log_count = len(backend.sync_log_ids)

    def action_view_sync_logs(self):
        self.ensure_one()
        return {
            'name': _('Sync Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'tec.dropshipping.log',
            'view_mode': 'list,form',
            'domain': [('backend_id', '=', self.id)],
            'target': 'current',
        }

    def sync_catalog(self):
        """ Abstract method to be implemented by provider modules """
        raise NotImplementedError("This method must be implemented by the specific provider module.")
