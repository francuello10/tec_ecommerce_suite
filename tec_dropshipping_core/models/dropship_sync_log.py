from odoo import models, fields, api, _

class DropshipSyncLog(models.Model):
    _name = 'tec.dropshipping.log'
    _description = 'Dropshipping Sync Log'
    _order = 'sync_date desc'

    backend_id = fields.Many2one('dropship.backend', string='Backend', required=False, ondelete='cascade')
    sync_date = fields.Datetime(string='Sync Date', default=fields.Datetime.now, readonly=True)
    sync_type = fields.Selection([
        ('catalog', 'Inventory & Prices'),
        ('characteristics', 'Content & Images'),
        ('brands', 'Brands Sync'),
        ('enrichment', 'Product Enrichment'),
    ], string='Sync Type', required=True)
    
    products_created = fields.Integer(string='Created', readonly=True)
    products_updated = fields.Integer(string='Updated', readonly=True)
    items_deleted = fields.Integer(string='Deleted/Cleaned', readonly=True)
    
    status = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial (Warnings)'),
        ('error', 'Failed')
    ], string='Status', readonly=True, default='success')
    
    log_summary = fields.Text(string='Summary', readonly=True)
    error_details = fields.Text(string='Error Details', readonly=True)

    def name_get(self):
        result = []
        for log in self:
            name = f"{log.backend_id.name} - {log.sync_type} ({log.sync_date.strftime('%Y-%m-%d %H:%M')})"
            result.append((log.id, name))
        return result
