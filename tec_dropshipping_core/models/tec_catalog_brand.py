import logging
import csv
import io
import base64

from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ─── Known aliases: Air brand name → Icecat canonical brand name ───
# This dictionary maps supplier-specific brand variations to their
# official Icecat name. Keep it simple, no fuzzy matching needed.
KNOWN_ALIASES = {
    'HEWLET PACKARD ENTERPRISE': 'HPE',
    'HEWLETT PACKARD ENTERPRISE': 'HPE',
    'PHILLIPS': 'Philips',
    'ASUS NB': 'ASUS',
    'SAMSUNG IMPRESORAS': 'Samsung',
    'KINGSTON PROPIETARIAS': 'Kingston',
    'DELL ENTERPRISE': 'DELL',
    'DELL COMPUTOS': 'DELL',
    'LENOVO DCG': 'Lenovo',
    'REPUESTOS HASAR': 'Hasar',
    'REPUESTO HASAR': 'Hasar',
    'REPUSTOS EPSON': 'Epson',
    'REPUESTO EPSON': 'Epson',
    'REPUESTOS EPSON': 'Epson',
    'LITE ON': 'Lite-On',
    'GENERAL ELECTRIC': 'GE',
    'ACCESORIOS CX': 'CX',
    'PC AIR / PC ARM': 'CX',
}


class TecCatalogBrandAlias(models.Model):
    _name = 'tec.catalog.brand.alias'
    _description = 'Alias de Marca'

    name = fields.Char(string='Nombre Alias', required=True, index=True)
    brand_id = fields.Many2one('tec.catalog.brand', string='Marca Oficial', required=True, ondelete='cascade')


class TecCatalogBrand(models.Model):
    _name = 'tec.catalog.brand'
    _description = 'Marca de Producto'
    _order = 'name'

    name = fields.Char(string='Nombre de la Marca', required=True, index=True)
    logo = fields.Image(string='Logo')
    description = fields.Html(string='Descripción')
    website_url = fields.Char(string='URL del Sitio Web')

    is_icecat_brand = fields.Boolean(string='Es Marca Oficial Icecat', default=False)
    alias_ids = fields.One2many('tec.catalog.brand.alias', 'brand_id', string='Alias')
    product_template_ids = fields.One2many('product.template', 'product_brand_id', string='Productos')

    product_count = fields.Integer(string='Productos', compute='_compute_product_count', store=True)

    @api.depends('product_template_ids')
    def _compute_product_count(self):
        data = self.env['product.template'].sudo()._read_group(
            [('product_brand_id', 'in', self.ids)],
            ['product_brand_id'],
            ['__count'],
        )
        count_map = {brand.id: count for brand, count in data}
        for brand in self:
            brand.product_count = count_map.get(brand.id, 0)



    @api.model
    def get_normalized_brand(self, raw_name, auto_create=True):
        """
        Resolves a raw brand name to a canonical tec.catalog.brand record.
        Resolution order:
          1. Exact match in brands (case insensitive)
          2. Match in aliases (case insensitive)
          3. KNOWN_ALIASES dictionary lookup → find canonical, create alias
          4. Create new brand (if auto_create=True)
        """
        if not raw_name:
            return False
        raw_name_clean = str(raw_name).strip()
        if not raw_name_clean or raw_name_clean.lower() in ['nan', 'none', 'null', '0', 'false']:
            return False

        # 1. Exact match in Brands (case insensitive)
        brand = self.search([('name', '=ilike', raw_name_clean)], limit=1)
        if brand:
            return brand

        # 2. Match in Aliases
        alias = self.env['tec.catalog.brand.alias'].search([('name', '=ilike', raw_name_clean)], limit=1)
        if alias and alias.brand_id:
            return alias.brand_id

        # 3. KNOWN_ALIASES dictionary — map to canonical name
        canonical = KNOWN_ALIASES.get(raw_name_clean.upper())
        if canonical:
            brand = self.search([('name', '=ilike', canonical)], limit=1)
            if brand:
                # Auto-create the alias for future lookups
                self.env['tec.catalog.brand.alias'].create({
                    'name': raw_name_clean,
                    'brand_id': brand.id,
                })
                _logger.info(f"Auto-created alias '{raw_name_clean}' → '{brand.name}'")
                return brand

        # 4. Create if not found and auto_create is True
        if auto_create:
            _logger.info(f"Brand '{raw_name_clean}' not found in canonicals, aliases, or dictionary. Creating new one.")
            return self.create({'name': raw_name_clean, 'is_icecat_brand': False})

        return False

    @api.model
    def action_import_icecat_brands_from_local_file(self, file_path='/mnt/extra-addons/tec_ecommerce_suite/icecat_brands.csv'):
        """ Imports canonical brands from the static Icecat CSV """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                to_create = []
                existing_names = set(self.search([]).mapped(lambda b: b.name.lower()))

                for row in reader:
                    brand_name = row.get('Brand', '').strip()
                    if brand_name and brand_name.lower() not in existing_names:
                        to_create.append({
                            'name': brand_name,
                            'is_icecat_brand': True,
                        })
                        existing_names.add(brand_name.lower())

                if to_create:
                    batch_size = 1000
                    for i in range(0, len(to_create), batch_size):
                        batch = to_create[i:i+batch_size]
                        self.create(batch)
                        self.env.cr.commit()
                        _logger.info(f"Imported Icecat brands batch {i} to {i+len(batch)}")
            return True
        except Exception as e:
            _logger.error(f"Failed to import Icecat Brands: {e}")
            raise UserError(_("Error importando marcas oficiales: %s") % str(e))

    @api.model
    def action_import_air_brand_mapping_from_local_file(self, file_path='/mnt/extra-addons/tec_ecommerce_suite/Marcas Air - Marcas.csv'):
        """
        Imports Air brands. For each:
          - If it matches an Icecat brand → skip (already exists)
          - If it's in KNOWN_ALIASES → create alias linking to the canonical Icecat brand
          - Otherwise → create as a new non-Icecat brand
        """
        Alias = self.env['tec.catalog.brand.alias']
        created = 0
        aliased = 0
        skipped = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    air_brand_name = row.get('MARCA', '').strip()
                    if not air_brand_name or air_brand_name.lower() in ['nan', 'none', '']:
                        continue

                    # Already exists as a brand?
                    brand = self.search([('name', '=ilike', air_brand_name)], limit=1)
                    if brand:
                        skipped += 1
                        continue

                    # Already exists as an alias?
                    alias = Alias.search([('name', '=ilike', air_brand_name)], limit=1)
                    if alias:
                        skipped += 1
                        continue

                    # Check KNOWN_ALIASES dictionary
                    canonical = KNOWN_ALIASES.get(air_brand_name.upper())
                    if canonical:
                        canonical_brand = self.search([('name', '=ilike', canonical)], limit=1)
                        if canonical_brand:
                            Alias.create({
                                'name': air_brand_name,
                                'brand_id': canonical_brand.id,
                            })
                            aliased += 1
                            _logger.info(f"Created alias '{air_brand_name}' → '{canonical_brand.name}'")
                            continue

                    # Not in Icecat, not aliased → create as new brand
                    self.create({
                        'name': air_brand_name,
                        'is_icecat_brand': False,
                    })
                    created += 1

            self.env.cr.commit()
            _logger.info(f"Air Brand Import: created={created}, aliased={aliased}, skipped={skipped}")
            return True
        except Exception as e:
            _logger.error(f"Failed to import Air Brands: {e}")
            raise UserError(_("Error importando marcas de Air: %s") % str(e))
