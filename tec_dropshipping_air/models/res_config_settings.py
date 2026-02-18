from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    air_auto_create_brands = fields.Boolean(
        string="Crear Marcas Automáticamente (Air)",
        config_parameter='tec_dropshipping_air.auto_create_brands',
        default=True,
        help="Si está activo, la sincronización creará marcas nuevas si no existen."
    )
    
    air_auto_download_images = fields.Boolean(
        string="Descargar Imágenes Automáticamente (Air)",
        config_parameter='tec_dropshipping_air.auto_download_images',
        default=True,
        help="Si está activo, la sincronización descargará y asignará imágenes desde URLs."
    )

    air_only_sync_existing_products = fields.Boolean(
        string="Sincronizar solo Productos Existentes (Air)",
        config_parameter='tec_dropshipping_air.only_sync_existing',
        default=False,
        help="Si está activo, la sincronización de características NO creará productos nuevos; solo actualizará los que ya existen (normalmente creados por la sincronización de stock)."
    )
