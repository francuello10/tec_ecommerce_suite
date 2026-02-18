from odoo import models, fields

class DropshipLocation(models.Model):
    _name = 'dropship.location'
    _description = 'Dropshipping Warehouse Location'
    _order = 'sequence'

    name = fields.Char(required=True)
    backend_id = fields.Many2one('dropship.backend', string='Backend', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Supplier Entity', required=True, help='Partner used for Purchase Orders')
    import_column = fields.Char(string='CSV Column Name', help='Column name in the supplier file that contains stock for this location (e.g., CBA, BS AS)')
    sequence = fields.Integer(string='Priority', default=10, help='Lower number means higher priority for routing.')
