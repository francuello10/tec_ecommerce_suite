from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_brand_id = fields.Many2one('tec.catalog.brand', string='Marca')
    tec_product_image_ids = fields.One2many('tec.product.image', 'product_tmpl_id', string='Imágenes Adicionales (Backend)')
    tec_enriched_description = fields.Html(string='Descripción Enriquecida (IA)', translate=True, help='Contenido de marketing generado por IA.')
    original_part_number = fields.Char(string='PN Fabricante (MPN)', index=True, help='Part Number Original del Fabricante (Backup inmutable).')
    virtual_available_web = fields.Float(
        string='Stock Disponible Web',
        compute='_compute_virtual_available_web',
        help='Stock total disponible sumando todos los proveedores para mostrar en la web'
    )
    stock_cba = fields.Float(string='Stock CBA', compute='_compute_stock_by_node', store=False)
    stock_bsas = fields.Float(string='Stock BSAS', compute='_compute_stock_by_node', store=False)

    # --- Air Computers Data (Supplier-Native) ---
    air_description_raw = fields.Text(string='Descripción Air (Raw)', help='Características técnicas crudas desde Air Computers')
    air_has_description = fields.Boolean(string='Tiene Descripción Air', compute='_compute_air_flags', store=True)
    air_has_images = fields.Boolean(string='Tiene Imágenes Air', help='Indica si se encontraron imágenes en el origen de Air')
    air_source_image_urls = fields.Text(string='URLs Imágenes Air (Sync Cache)', help='Cache de URLs de imágenes procesadas para evitar re-descargas.')

    x_usd_price = fields.Float(string='Precio Venta (USD)', digits=(16, 2), help='Precio de venta base en Dólares')
    x_usd_cost = fields.Float(string='Costo (USD)', digits=(16, 2), help='Costo base del proveedor en Dólares')
    usd_currency_id = fields.Many2one('res.currency', string='USD', default=lambda self: self.env.ref('base.USD'))

    @api.onchange('x_usd_price', 'x_usd_cost')
    def _onchange_usd_prices(self):
        """ Update standard ARS prices when USD prices change manually """
        for product in self:
            usd_curr = self.env.ref('base.USD')
            comp_curr = self.env.company.currency_id
            if comp_curr != usd_curr:
                product.list_price = usd_curr._convert(product.x_usd_price, comp_curr, self.env.company, fields.Date.today())
                product.standard_price = usd_curr._convert(product.x_usd_cost, comp_curr, self.env.company, fields.Date.today())
            else:
                product.list_price = product.x_usd_price
                product.standard_price = product.x_usd_cost

    @api.depends('air_description_raw')
    def _compute_air_flags(self):
        for product in self:
            product.air_has_description = bool(product.air_description_raw)

    @api.depends('seller_ids.x_vendor_stock', 'seller_ids.dropship_location_id.name')
    def _compute_stock_by_node(self):
        for product in self:
            stock_cba = 0.0
            stock_bsas = 0.0
            for seller in product.seller_ids:
                if not seller.dropship_location_id:
                    continue
                loc_name = (seller.dropship_location_id.name or '').upper()
                # Rules for Córdoba
                if any(x in loc_name for x in ['CBA', 'CÓRDOBA', 'CORDOBA']):
                    stock_cba += seller.x_vendor_stock
                # Rules for Buenos Aires / Lugano
                # Updated to match "Buenos Aires", "BS AS", "BSAS", "LUGANO"
                if any(x in loc_name for x in ['LUG', 'LUGANO', 'BSAS', 'BS AS', 'BS.AS', 'BUENOS AIRES', 'BAIRES']):
                    stock_bsas += seller.x_vendor_stock
            product.stock_cba = stock_cba
            product.stock_bsas = stock_bsas


    @api.depends('seller_ids.x_vendor_stock')
    def _compute_virtual_available_web(self):
        for product in self:
            # Sum stock from all supplier info lines that have x_vendor_stock set
            # We assume x_vendor_stock is added to product.supplierinfo by the provider module or core
            # Note: We need to ensure x_vendor_stock exists on supplierinfo first.
            total = 0.0
            for seller in product.seller_ids:
                if hasattr(seller, 'x_vendor_stock'):
                    total += seller.x_vendor_stock
            product.virtual_available_web = total

class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    x_vendor_stock = fields.Float(string='Stock del Proveedor', default=0.0)
    dropship_location_id = fields.Many2one('dropship.location', string='Ubicación Dropship', help='Sucursal/Depósito de origen de este stock')
    x_last_update_date = fields.Datetime(string='Última Actualización', help='Fecha y hora de la última sincronización de stock con el proveedor.')
