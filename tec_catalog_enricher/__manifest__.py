{
    'name': 'Tec Catalog Brain',
    'version': '2.0',
    'category': 'Inventory/Products',
    'summary': 'The Intelligence Hub: AI Content & Smart Category Mapping.',
    'description': """
        The core intelligence engine of the Tecnopolis eCommerce Suite.
        - **Enrichment**: Lenovo, Icecat, Google, YouTube.
        - **AI Copywriting**: Gemini-powered product content.
        - **Smart Mapping**: AI-driven categorization for Marketplaces (MELI).
    """,
    'author': 'Francisco Cuello',
    'website': 'https://github.com/francuello10',
    'depends': ['base', 'product', 'tec_dropshipping_core'],
    'external_dependencies': {
        'python': ['requests', 'bs4', 'google.generativeai'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/res_config_settings_view.xml',
        'views/product_template_views.xml',
        'views/product_public_category_view.xml',
        'views/category_mapping_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
