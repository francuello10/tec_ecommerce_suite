from odoo import fields, models

class ProductCategory(models.Model):
    _inherit = 'product.category'

    safety_stock_qty = fields.Float(
        string='Website Safety Stock',
        default=-1.0,
        help='Set -1 to inherit from Global settings. Set 0 to FORCE PUBLISH (disable safety stock). Set > 0 to enforce a buffer.'
    )
