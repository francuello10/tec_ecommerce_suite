from odoo import models, fields

class DropshipTaxMap(models.Model):
    _name = 'dropship.tax.map'
    _description = 'Dropshipping Tax Mapping'

    backend_id = fields.Many2one('dropship.backend', string='Backend', required=True, ondelete='cascade')
    csv_value = fields.Char(string='CSV Tax Value', required=True, help='Value found in the CSV (e.g., "10.5", "21")')
    tax_id = fields.Many2one('account.tax', string='Purchase Tax', required=True, domain=[('type_tax_use', '=', 'purchase')])
    sale_tax_id = fields.Many2one('account.tax', string='Sale Tax', required=True, domain=[('type_tax_use', '=', 'sale')])
