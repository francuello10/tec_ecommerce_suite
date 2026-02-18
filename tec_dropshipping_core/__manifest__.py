{
    'name': 'Tec Dropshipping Core',
    'version': '2.0',
    'category': 'Operations/Inventory',
    'summary': 'The Dropshipping Framework: Multi-Location, Multi-Currency & Mappings.',
    'description': """
        The master framework for the Tecnopolis eCommerce Suite.
        - **Logistics**: Multi-warehouse and multi-branch management.
        - **Finance**: Automated cost/price conversion with per-backend exchange rates.
        - **Mappings**: Robust supplier-to-local brand and tax mapping system.
    """,
    'author': 'Tecnopolis',
    'website': 'https://tecnopolis.com.ar',
    'depends': ['base', 'sale_management', 'purchase', 'stock'],
    'data': [
        'security/tec_dropshipping_security.xml',
        'security/ir.model.access.csv',
        'views/tec_catalog_brand_views.xml',
        'views/dropship_backend_views.xml',
        'views/dropship_location_views.xml',
        'views/dropship_log_views.xml',
        'views/dropship_tax_map_views.xml',
        'views/product_views.xml',
        'views/res_config_settings_view.xml',
        'views/dropship_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
