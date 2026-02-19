{
    'name': 'Tec Website Pro',
    'version': '2.0',
    'category': 'Website/eCommerce',
    'summary': 'The Frontend Hub: Premium UX, Smart Badges & Stock Shield.',
    'description': """
        The ultimate eCommerce Frontend engine for Odoo v19.
        - **Visual UX**: Clean tabs, responsive brands and rich media.
        - **Trust Building**: Smart labels (New, Low Stock, OFF) and Safety Stock protection.
        - **Content**: Integrated manufacturer links and support documentation.
    """,
    'author': 'Francisco Cuello',
    'website': 'https://github.com/francuello10',
    'depends': ['website_sale', 'tec_dropshipping_core'],
    'data': [
        'views/tec_catalog_brand_views.xml',
        'views/product_template_views.xml',
        'views/product_category_view.xml',
        'views/website_sale_templates.xml',
        'views/res_config_settings_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'tec_website_catalog_pro/static/src/css/styles.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
