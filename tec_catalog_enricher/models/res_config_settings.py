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

    use_lenovo_psref = fields.Boolean(string="Habilitar Lenovo PSREF", config_parameter='tec_catalog_enricher.use_lenovo_psref', default=True)

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

    # --- API Test Actions ---
    def action_test_gemini(self):
        self.ensure_one()
        api_key = self.gemini_api_key or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.gemini_api_key')
        model_name = self.gemini_model or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.gemini_model') or 'gemini-1.5-flash'
        if not api_key:
            return self._notify_error("Falta API Key de Gemini")
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            # Remove -exp if present for stable testing or just trust selection
            model = genai.GenerativeModel(model_name)
            res = model.generate_content("Ping")
            if res.text:
                return self._notify_success(f"Gemini ({model_name}): ¡Conexión Exitosa!")
        except Exception as e:
            return self._notify_error(f"Gemini Error: {str(e)}")

    def action_test_openai(self):
        self.ensure_one()
        api_key = self.openai_api_key or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.openai_api_key')
        model_name = self.openai_model or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.openai_model') or 'gpt-4o-mini'
        if not api_key:
            return self._notify_error("Falta API Key de OpenAI")
        try:
            import httpx
            headers = {"Authorization": f"Bearer {api_key}"}
            # Handle model naming for o4-mini etc if needed
            res = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={"model": model_name, "messages": [{"role": "user", "content": "Ping"}], "max_tokens": 5},
                timeout=10
            )
            if res.status_code == 200:
                return self._notify_success(f"OpenAI ({model_name}): ¡Conexión Exitosa!")
            return self._notify_error(f"OpenAI Error: {res.text}")
        except Exception as e:
            return self._notify_error(f"OpenAI Error: {str(e)}")

    def action_test_google_search(self):
        self.ensure_one()
        api_key = self.google_cse_key or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.google_cse_key')
        cx = self.google_cse_cx or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.google_cse_cx')
        if not api_key or not cx:
            return self._notify_error("Faltan API Key o CX de Google")
        try:
            import requests
            url = f"https://www.googleapis.com/customsearch/v1?q=odoo&cx={cx}&key={api_key}&num=1"
            res = requests.get(url, timeout=10).json()
            if 'items' in res:
                return self._notify_success("Google Search: ¡Conexión Exitosa!")
            if 'error' in res:
                return self._notify_error(f"Google Error: {res['error']['message']}")
            return self._notify_error(f"Google Error: Respuesta inesperada")
        except Exception as e:
            return self._notify_error(f"Google Search Error: {str(e)}")

    def action_test_icecat(self):
        self.ensure_one()
        method = self.icecat_auth_method or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.icecat_auth_method')
        try:
            import requests
            if method == 'token':
                api_token = self.icecat_api_token or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.icecat_api_token')
                content_token = self.icecat_content_token or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.icecat_content_token')
                if not content_token:
                    return self._notify_error("Falta Content Token de Icecat")
                
                # Test with a common MPN (Dell Monitor)
                url = "https://live.icecat.biz/api"
                # LIVE API requires UserName and lang
                username = self.icecat_username or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.icecat_username')
                
                params = {
                    'UserName': username,
                    'brand': 'Dell',
                    'part_code': '210-AXLQ',
                    'content_token': content_token,
                    'lang': 'es'
                }
                headers = {}
                if api_token:
                    headers['app_key'] = api_token
                
                res = requests.get(url, params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    return self._notify_success("Icecat JSON: ¡Conexión Exitosa!")
                return self._notify_error(f"Icecat JSON Error {res.status_code}: {res.text[:100]}")
            else:
                user = self.icecat_username or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.icecat_username')
                pwd = self.icecat_password or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.icecat_password')
                if not user or not pwd: return self._notify_error("Faltan credenciales de Icecat")
                import base64
                auth = base64.b64encode(f"{user}:{pwd}".encode()).decode()
                headers = {'Authorization': f'Basic {auth}'}
                url = "https://data.icecat.biz/xml_s3/xml_server.cgi?rebrand=openicecat;prod_id=210-AXLQ;vendor=Dell;lang=es;output=productxml"
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    return self._notify_success("Icecat Basic: ¡Conexión Exitosa!")
                return self._notify_error(f"Icecat XML Error: {res.status_code}")
        except Exception as e:
            return self._notify_error(f"Icecat Error: {str(e)}")
        return self._notify_error("Error desconocido probando Icecat")

    def action_test_youtube(self):
        self.ensure_one()
        api_key = self.youtube_api_key or self.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.youtube_api_key')
        if not api_key:
            return self._notify_error("Falta API Key de YouTube")
        try:
            import requests
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=odoo&key={api_key}&maxResults=1"
            res = requests.get(url, timeout=10).json()
            if 'items' in res:
                return self._notify_success("YouTube: ¡Conexión Exitosa!")
            if 'error' in res:
                return self._notify_error(f"YouTube Error: {res['error']['message']}")
        except Exception as e:
            return self._notify_error(f"YouTube Error: {str(e)}")
        return self._notify_error("Error desconocido probando YouTube")

    def action_test_lenovo_psref(self):
        self.ensure_one()
        try:
            import requests
            import time
            # Test with a well-known Lenovo MPN (e.g., 20XW004KUS - ThinkPad X1)
            search_url = "https://psref.lenovo.com/api/search/DefinitionFilterAndSearch/Suggest"
            params = {'kw': '20XW004KUS', 'SearchType': 'Model', 't': int(time.time() * 1000)}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://psref.lenovo.com/',
            }
            res = requests.get(search_url, params=params, headers=headers, timeout=15)
            
            if res.status_code != 200:
                return self._notify_error(f"Lenovo PSREF Error (HTTP {res.status_code})")

            try:
                json_data = res.json()
            except Exception:
                return self._notify_error("Lenovo PSREF: La respuesta no es un JSON válido.")

            if json_data.get('code') == 1 and json_data.get('data'):
                return self._notify_success("Lenovo PSREF: ¡Conexión Exitosa!")
            return self._notify_error("Lenovo PSREF: No se obtuvo respuesta del catálogo.")
        except Exception as e:
            return self._notify_error(f"Lenovo PSREF Error: {str(e)}")

    def action_test_pod(self):
        self.ensure_one()
        try:
            import requests
            # Test POD (Product Open Data) - Switched to Open Food Facts for reliability in pinging
            # URL format: https://world.openfoodfacts.org/api/v0/product/{gtin}.json
            url = "https://world.openfoodfacts.org/api/v0/product/737628064502.json"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return self._notify_success("Data Catalog (OFF/POD): ¡Conexión Exitosa!")
            return self._notify_error(f"POD Error {res.status_code}: El servidor no respondió correctamente.")
        except Exception as e:
            return self._notify_error(f"POD Error: {str(e)}")

    def _notify_success(self, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Éxito',
                'message': message,
                'sticky': False,
                'type': 'success',
            }
        }

    def _notify_error(self, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Error de Conexión',
                'message': message,
                'sticky': True,
                'type': 'danger',
            }
        }
