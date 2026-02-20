from odoo import fields, models, api
from datetime import timedelta

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # product_brand_id is defined in tec_dropshipping_core

    is_new_arrival = fields.Boolean(
        string='Es Novedad',
        compute='_compute_is_new_arrival',
        store=False
    )
    is_low_stock = fields.Boolean(
        string='Stock Bajo',
        compute='_compute_is_low_stock',
        store=False
    )
    discount_percent = fields.Integer(
        string='Porcentaje de Descuento',
        compute='_compute_discount_percent',
        store=False
    )

    # Marketplace Metadata
    video_url = fields.Char(string='URL de Video', help='URL de YouTube o Vimeo.')
    condition = fields.Selection([
        ('new', 'Nuevo'),
        ('refurbished', 'Reacondicionado'),
        ('used', 'Usado')
    ], string='Condición', default='new', help='Estado del producto para marketplaces.')
    
    highlights = fields.Html(
        string='Puntos Destacados (Bullet Points)',
        translate=True,
        help='Puntos clave del producto (estilo Amazon/MELI).'
    )

    # --- Safety Stock (Migrated from tec_website_safety_stock) ---
    safety_stock_qty = fields.Float(
        string='Reserva de Seguridad (Cantidad)',
        default=-1.0,
        help='-1: Heredar, 0: Publicar siempre, >0: Buffer fijo.'
    )

    safety_stock_type_desc = fields.Selection([
        ('inherit', '📦 Heredar regla (Categoría o General)'),
        ('disable', '🚀 Publicar Siempre (Ignorar Stock Mínimo)'),
        ('custom', '🛡️ Reserva Fija (Personalizada)')
    ], string='Modo de Seguridad Web', compute='_compute_safety_stock_type_desc', readonly=True)

    computed_safety_stock = fields.Float(
        string='Reserva Aplicada Real (Final)',
        compute='_compute_safety_stock_qty',
        store=False,
        help='Cantidad real que se está restando de la disponibilidad web.'
    )

    @api.depends('safety_stock_qty')
    def _compute_safety_stock_type_desc(self):
        for template in self:
            if template.safety_stock_qty == -1.0:
                template.safety_stock_type_desc = 'inherit'
            elif template.safety_stock_qty == 0.0:
                template.safety_stock_type_desc = 'disable'
            else:
                template.safety_stock_type_desc = 'custom'

    @api.depends('safety_stock_qty', 'categ_id.safety_stock_qty')
    def _compute_safety_stock_qty(self):
        active = self.env['ir.config_parameter'].sudo().get_param('tec_website_catalog_pro.safety_stock_active', 'True') == 'True'
        for template in self:
            if not active:
                template.computed_safety_stock = 0.0
                continue

            # 1. Product Level Override
            if template.safety_stock_qty >= 0.0:
                template.computed_safety_stock = template.safety_stock_qty
                continue

            # 2. Category Level Rule
            if template.categ_id.safety_stock_qty >= 0.0:
                template.computed_safety_stock = template.categ_id.safety_stock_qty
                continue

            # 3. Global Fallback
            template.computed_safety_stock = self.env.company.safety_stock_qty
    # ------------------------------------------------------------- 


    @api.depends('create_date')
    def _compute_is_new_arrival(self):
        ICP = self.env['ir.config_parameter'].sudo()
        show_labels = ICP.get_param('tec_website_catalog_pro.show_smart_labels')
        for template in self:
            if not show_labels or not template.create_date:
                template.is_new_arrival = False
                continue
            template.is_new_arrival = template.create_date > fields.Datetime.now() - timedelta(days=30)

    def _compute_is_low_stock(self):
        ICP = self.env['ir.config_parameter'].sudo()
        show_labels = ICP.get_param('tec_website_catalog_pro.show_smart_labels')
        for template in self:
            if not show_labels:
                template.is_low_stock = False
                continue
            
            # Use sudo to prevent mrp.bom access errors on public users, or use website_stock
            qty = template.sudo().qty_available
            safety_stock = getattr(template, 'computed_safety_stock', 0.0)
            template.is_low_stock = (qty - safety_stock) < 5

    def _compute_discount_percent(self):
        ICP = self.env['ir.config_parameter'].sudo()
        show_labels = ICP.get_param('tec_website_catalog_pro.show_smart_labels')
        for template in self:
            if not show_labels:
                template.discount_percent = 0
                continue
            # Placeholder: True discount calculation normally happens in QWeb with combination_info.
            template.discount_percent = 0

    x_website_stock = fields.Float(
        string='Stock Web (Calculado)',
        compute='_compute_website_stock',
        store=False,
        help="Stock calculado para mostrar en la web (Max/Suma - Seguridad)."
    )

    def _compute_website_stock(self):
        website = self.env['website'].get_current_website()
        mode = website.sudo().stock_display_mode if website and hasattr(website, 'stock_display_mode') else 'max'
        
        for template in self:
            # 1. Get raw dropship stock (Use sudo to bypass supplierinfo restrictions for public users)
            sellers = template.sudo().seller_ids.filtered(lambda s: s.dropship_location_id)
            raw_stock = 0.0
            if not sellers:
                # Fallback to standard qty_available if no dropship sellers? 
                # Let's assume 0 if no dropship info.
                raw_stock = 0.0
            else:
                if mode == 'sum':
                    raw_stock = sum(s.x_vendor_stock for s in sellers)
                else: # max
                    raw_stock = max([s.x_vendor_stock for s in sellers] or [0])
            
            # 2. Subtract Safety Stock
            safety_stock = getattr(template, 'computed_safety_stock', 0.0)
            
            final_stock = raw_stock - safety_stock
            template.x_website_stock = max(0.0, final_stock)

