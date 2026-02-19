{
    'name': 'Tec Dropshipping Air',
    'version': '2.0',
    'category': 'Operations/Inventory',
    'summary': 'Air Computers Connector: Seamless Catalog & Content Sync.',
    'description': """
        Specific adaptor for Air Computers (Argentina).
        - **Real-time Sync**: Automated fetching of catalog, prices and stock.
        - **Rich Content**: Integration with characteristics and high-res media.
        - **Branch Support**: Specific mapping for CBA and BSAS stocks.
    """,
    'author': 'Francisco Cuello',
    'website': 'https://github.com/francuello10',
    'depends': ['tec_dropshipping_core'],
    'data': [
        'views/dropship_backend_views.xml',
        'views/res_config_settings_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
