from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_tec_ecommerce_suite = fields.Boolean(
        string="Tec eCommerce Suite",
        group='base.group_user',
        implied_group='tec_dropshipping_core.group_tec_ecommerce_suite_user',
        config_parameter='tec_dropshipping_core.module_active',
        help="Master switch to enable the Tec eCommerce Suite features."
    )
