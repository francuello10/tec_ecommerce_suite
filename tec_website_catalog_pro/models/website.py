from odoo import fields, models

class Website(models.Model):
    _inherit = 'website'

    stock_display_mode = fields.Selection([
        ('max', 'Máximo de Sucursales (CBA vs BSAS)'),
        ('sum', 'Suma Total (CBA + BSAS)'),
    ], string='Modo de Visualización de Stock', default='max', help="Define cómo se muestra el stock en el sitio web.")

    def _get_product_available_qty(self, product, **kwargs):
        """
        Overriding to subtract safety stock from the available quantity.
        'product' here is a product.product record.
        """
        qty = super()._get_product_available_qty(product, **kwargs)
        
        # Access the computed safety stock from the template
        safety_stock = product.product_tmpl_id.computed_safety_stock
        
        # If the result is negative, return 0.0 to indicate out of stock.
        return max(0.0, qty - safety_stock)
