from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # --- Hard Data Sources ---
    use_icecat = fields.Boolean(string="Habilitar Icecat", config_parameter='tec_catalog_enricher.use_icecat', default=False)
    icecat_username = fields.Char(string="Usuario Icecat", config_parameter='tec_catalog_enricher.icecat_username')
    icecat_password = fields.Char(string="Contraseña Icecat", config_parameter='tec_catalog_enricher.icecat_password')
    
    use_google = fields.Boolean(string="Habilitar Google Fallback", config_parameter='tec_catalog_enricher.use_google', default=False)
    google_cse_key = fields.Char(string="API Key Google CSE", config_parameter='tec_catalog_enricher.google_cse_key')
    google_cse_cx = fields.Char(string="ID Motor de Búsqueda (CX)", config_parameter='tec_catalog_enricher.google_cse_cx')

    # --- Soft Data / Soft Data ---
    use_gemini = fields.Boolean(string="Habilitar Gemini AI", config_parameter='tec_catalog_enricher.use_gemini', default=False)
    gemini_api_key = fields.Char(string="API Key Gemini", config_parameter='tec_catalog_enricher.gemini_api_key')
    gemini_model = fields.Selection(
        selection=[
            ('gemini-1.5-flash', 'Gemini 1.5 Flash (Fast & Cheap)'),
            ('gemini-2.0-flash', 'Gemini 2.0 Flash (Next Gen)'),
            ('gemini-1.5-pro', 'Gemini 1.5 Pro (Powerful)'),
        ],
        string="Gemini Model",
        config_parameter='tec_catalog_enricher.gemini_model',
        default='gemini-2.0-flash'
    )

    # --- AI Enrichment Fine-Tuning ---
    ai_input_name = fields.Boolean(string="Input: Nombre", config_parameter='tec_catalog_enricher.ai_input_name', default=True)
    ai_input_brand = fields.Boolean(string="Input: Marca", config_parameter='tec_catalog_enricher.ai_input_brand', default=True)
    ai_input_category = fields.Boolean(string="Input: Categoría", config_parameter='tec_catalog_enricher.ai_input_category', default=False)
    ai_input_description_air = fields.Boolean(string="Input: Descripción Air", config_parameter='tec_catalog_enricher.ai_input_description_air', default=True)
    ai_input_description_enrich = fields.Boolean(string="Input: Especificaciones (Técnicas)", config_parameter='tec_catalog_enricher.ai_input_description_enrich', default=True)
    ai_input_thumbnail = fields.Boolean(string="Input: Thumbnail (Visión)", config_parameter='tec_catalog_enricher.ai_input_thumbnail', default=False)
    
    ai_custom_prompt = fields.Char(
        string="Master Prompt", 
        config_parameter='tec_catalog_enricher.ai_custom_prompt',
        default="""Actúa como un Copywriter Experto en E-commerce de Hardware al estilo MercadoLibre Argentina.
Insumos: {inputs}

TAREA:
1. Genera un 'Friendly Name' SEO (Ej: 'Notebook HP 250 G9 i5 8GB SSD').
2. Redacta una 'Marketing Description' (HTML) con Storytelling, Emojis y beneficios. Tono cercano.
3. Redacta una 'Technical Description' (HTML) bien estructurada en tablas o listas técnicas limpias.
4. Genera 5 'Usage Tags'.

Devuelve un JSON con claves: 'seo_name', 'marketing_html', 'technical_html', 'tags'.
Do not use markdown code blocks. Just raw JSON."""
    )

    # MELI Settings (Migrated from tec_catalog_meli_categories)
    tec_meli_api_url = fields.Char(
        string="MELI API URL",
        config_parameter='tec_catalog_enricher.meli_api_url',
        default='https://api.mercadolibre.com'
    )

    tec_meli_enable_ai_mapping = fields.Boolean(
        string="Enable AI Category Mapping",
        config_parameter='tec_catalog_enricher.meli_enable_ai',
        default=True
    )
    use_youtube = fields.Boolean(string="Habilitar YouTube Reviews", config_parameter='tec_catalog_enricher.use_youtube', default=False)
    youtube_api_key = fields.Char(string="API Key YouTube", config_parameter='tec_catalog_enricher.youtube_api_key', help="Puede ser la misma que Google CSE.")

    # --- Governance ---
    max_images_limit = fields.Integer(string="Límite Máximo de Imágenes", config_parameter='tec_catalog_enricher.max_images_limit', default=3)
