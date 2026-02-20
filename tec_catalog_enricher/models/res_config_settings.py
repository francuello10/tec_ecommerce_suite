from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # --- Hard Data Sources ---
    use_icecat = fields.Boolean(string="Habilitar Icecat", config_parameter='tec_catalog_enricher.use_icecat', default=False)
    icecat_username = fields.Char(string="Usuario Icecat", config_parameter='tec_catalog_enricher.icecat_username')
    icecat_password = fields.Char(string="Contraseña Icecat", config_parameter='tec_catalog_enricher.icecat_password')
    
    icecat_auth_method = fields.Selection(
        selection=[('basic', 'Basic Auth (Legacy)'), ('token', 'Token Auth (New API)')],
        string="Método de Autenticación",
        config_parameter='tec_catalog_enricher.icecat_auth_method',
        default='basic'
    )
    icecat_api_token = fields.Char(string="API Access Token", config_parameter='tec_catalog_enricher.icecat_api_token')
    icecat_content_token = fields.Char(string="Content Access Token", config_parameter='tec_catalog_enricher.icecat_content_token')
    
    use_google = fields.Boolean(string="Habilitar Google Fallback", config_parameter='tec_catalog_enricher.use_google', default=False)
    google_cse_key = fields.Char(string="API Key Google CSE", config_parameter='tec_catalog_enricher.google_cse_key')
    google_cse_cx = fields.Char(string="ID Motor de Búsqueda (CX)", config_parameter='tec_catalog_enricher.google_cse_cx')

    use_bestbuy = fields.Boolean(string="Habilitar Best Buy API", config_parameter='tec_catalog_enricher.use_bestbuy', default=False)
    bestbuy_api_key = fields.Char(string="API Key Best Buy", config_parameter='tec_catalog_enricher.bestbuy_api_key')

    use_pod = fields.Boolean(string="Habilitar Product Open Data", config_parameter='tec_catalog_enricher.use_pod', default=False)

    # --- AI Provider Selection ---
    ai_provider = fields.Selection(
        selection=[
            ('gemini', 'Google Gemini'),
            ('openai', 'OpenAI'),
        ],
        string="Proveedor IA Activo",
        config_parameter='tec_catalog_enricher.ai_provider',
        default='gemini'
    )

    # --- Soft Data / Gemini ---
    use_gemini = fields.Boolean(string="Habilitar Gemini AI", config_parameter='tec_catalog_enricher.use_gemini', default=False)
    gemini_api_key = fields.Char(string="API Key Gemini", config_parameter='tec_catalog_enricher.gemini_api_key')
    gemini_model = fields.Selection(
        selection=[
            ('gemini-2.0-flash', 'Gemini 2.0 Flash 🚀 (Recomendado)'),
            ('gemini-2.0-flash-exp', 'Gemini 2.0 Flash Experimental'),
            ('gemini-1.5-flash', 'Gemini 1.5 Flash (Rápido)'),
        ],
        string="Modelo Gemini",
        config_parameter='tec_catalog_enricher.gemini_model',
        default='gemini-2.0-flash'
    )

    # --- Soft Data / OpenAI ---
    openai_api_key = fields.Char(string="API Key OpenAI", config_parameter='tec_catalog_enricher.openai_api_key')
    openai_model = fields.Selection(
        selection=[
            ('gpt-4.1-nano', 'GPT-4.1 Nano ⚡ (Recomendado)'),
            ('gpt-4o-mini', 'GPT-4o Mini'),
            ('o4-mini', 'o4-mini (Razonamiento)'),
        ],
        string="Modelo OpenAI",
        config_parameter='tec_catalog_enricher.openai_model',
        default='gpt-4.1-nano'
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
        default="""Actúas como un Ingeniero de Hardware y Senior Product Manager de e-commerce de tecnología en Argentina.
Tu objetivo es analizar la información técnica cruda de un producto IT y devolver ÚNICAMENTE un objeto JSON válido, parseable directamente por json.loads(). NO uses bloques de código Markdown ni texto introductorio.

El JSON debe respetar esta estructura:
{
  "seo_name": "Nombre comercial optimizado para SEO",
  "marketing_description": "<p>Descripción persuasiva en español argentino, enfocada en los beneficios B2C/B2B. Mínimo 2 párrafos. Usa etiquetas HTML básicas como <b> y <br>.</p>",
  "technical_html": "<table class='table table-sm'>...</table> (Tabla HTML limpia con las especificaciones. Opcional si no hay datos técnicos estructurados)",
  "attributes": {
    "Clave Dinámica 1": "Valor Específico 1",
    "Clave Dinámica 2": "Valor Específico 2"
  }
}

REGLAS ESTRICTAS PARA LA EXTRACCIÓN DE ATRIBUTOS TÉCNICOS:
1. Eres un experto: Tienes total libertad para crear las claves ("keys") en el objeto "attributes" que consideres vitales para ese producto (Ej: "Tipo de Panel", "Frecuencia de Actualización", "Generación de Procesador", "Factor de Forma").
2. Precisión Quirúrgica en RAM y Almacenamiento: 
   - NUNCA pongas solo la capacidad. 
   - Para RAM, especifica tecnología y velocidad (Ej: "16GB DDR5 4800MHz" o "8GB LPDDR4x").
   - Para almacenamiento, distingue la interfaz (Ej: "1TB M.2 NVMe PCIe 4.0" vs "512GB SSD SATA").
3. Precisión en Pantallas: Incluye tecnología del panel, resolución y tasa de refresco si aplica.
4. Normalización: Mantén los valores concisos (Faceted Search), pero completos.
5. Cero Alucinaciones: Extrae entre 5 y 12 atributos. Si un dato vital no está, OMÍTELO. No inventes.

Insumos: {inputs}"""
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
