from odoo import fields, models, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    safety_stock_qty = fields.Float(
        string='Stock de Seguridad Global',
        default=0.0,
        help='Cantidad global de stock de seguridad que se resta de la disponibilidad web. Se aplica si no hay reglas por categoría o producto.'
    )

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_smart_labels = fields.Boolean(
        string="Habilitar Etiquetas Smart", 
        config_parameter='tec_website_catalog_pro.show_smart_labels', 
        default=True,
        help="Muestra etiquetas de 'Nuevo', 'Stock Bajo' y 'Descuento' en el frontend."
    )

    catalog_pro_show_usd_exchange = fields.Boolean(
        string="Mostrar Referencia USD / TC",
        config_parameter='tec_website_catalog_pro.show_usd_exchange',
        default=True,
        help="Muestra el precio en USD y el Tipo de Cambio en la cabecera y ficha."
    )

    catalog_pro_show_highlights = fields.Boolean(
        string="Mostrar Destacados (IA)",
        config_parameter='tec_website_catalog_pro.show_highlights',
        default=True,
        help="Muestra los puntos destacados generados por IA en la ficha."
    )

    catalog_pro_show_videos = fields.Boolean(
        string="Habilitar Galería de Videos",
        config_parameter='tec_website_catalog_pro.show_videos',
        default=True,
        help="Habilita la pestaña de video en la ficha de producto."
    )

    catalog_pro_show_air_description = fields.Boolean(
        string="Mostrar Descripción de Fabricante (Air)",
        config_parameter='tec_website_catalog_pro.show_air_description',
        default=True,
        help="Muestra la descripción técnica enriquecida del proveedor (Air Computers) si está disponible."
    )

    safety_stock_qty = fields.Float(
        string="Stock de Seguridad Web Global",
        related='company_id.safety_stock_qty',
        readonly=False,
        help='Cantidad global de stock de seguridad que se resta de la disponibilidad web. Se aplica si no hay reglas por categoría o producto.'
    )

    safety_stock_active = fields.Boolean(
        string="Habilitar Protección de Stock",
        config_parameter='tec_website_safety_stock.active',
        default=True,
        help="Si se desactiva, el sitio web mostrará el stock real sin reducciones de seguridad."
    )

    catalog_enricher_show_spec_links = fields.Boolean(
        string="Mostrar Links a Fichas Oficiales",
        config_parameter='tec_catalog_enricher_website.show_spec_links',
        default=True
    )

    catalog_enricher_show_support_buttons = fields.Boolean(
        string="Mostrar Botones de Soporte Oficial",
        config_parameter='tec_catalog_enricher_website.show_support_buttons',
        default=True
    )

    stock_display_mode = fields.Selection(
        related='website_id.stock_display_mode',
        readonly=False,
        string="Modo de Visualización de Stock",
    )

