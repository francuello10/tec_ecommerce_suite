from odoo import fields, models

class TecProductImage(models.Model):
    _name = 'tec.product.image'
    _description = 'Imagen de Producto (Backend)'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(default=10)
    image_1920 = fields.Image(string='Imagen', max_width=1920, max_height=1920)
    product_tmpl_id = fields.Many2one('product.template', string='Producto', ondelete='cascade')
