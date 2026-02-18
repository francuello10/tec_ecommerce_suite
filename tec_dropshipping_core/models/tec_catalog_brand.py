from odoo import fields, models

class TecCatalogBrand(models.Model):
    _name = 'tec.catalog.brand'
    _description = 'Marca de Producto'
    _order = 'name'

    name = fields.Char(string='Nombre de la Marca', required=True)
    logo = fields.Image(string='Logo')
    description = fields.Html(string='Descripción')
    website_url = fields.Char(string='URL del Sitio Web')
