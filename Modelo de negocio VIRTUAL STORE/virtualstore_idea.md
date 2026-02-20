# 🚀 Master Plan: Virtual Store IT (Odoo v19)

## 📌 1. Visión General e Infraestructura
* **Marca/Dominio:** Virtual Store (`https://virtualstore.com.ar/`). 
* **Posicionamiento:** Actualmente rankea #1 en Google para su keyword principal.
* **Estado Actual:** Plataforma legacy en WordPress/WooCommerce (inactiva).
* **Objetivo Core:** Migración total a **Odoo v19 Enterprise** centralizando todas las operaciones (ERP, CRM, CMS y eCommerce) bajo una única mesa de trabajo unificada.
* **Infraestructura:** Alojado en instancia Oracle Ampere (4 vCores, 24GB RAM) para garantizar velocidad y procesamiento masivo a bajo costo.
* **Filosofía de Desarrollo:** Visión de negocio (Admin de Empresas) + Ejecución técnica (Coder). Uso de herramientas nativas de Odoo (Native-first). Cero sobreingeniería. Los desarrollos a medida se construyen como módulos genéricos con potencial B2B.

## 💼 2. Modelo de Negocio (Dropshipping Puro)
* **Capital de Trabajo:** Optimizado (Stock Cero).
* **Proveedores IT (Argentina):** Air Computers (MVP) -> Elite/Stylus -> Ingram Micro.
* **Flujo Operativo:** Sincronización -> Venta B2C -> SO Odoo -> PO Dropship interna -> Operador compra en B2B -> Proveedor despacha.

## 💵 3. Estrategia Multimoneda (USD a ARS)
Dados los catálogos en USD y la venta B2C en ARS:
* **`dolar_api_integration`:** Sincronización automática de tasas (Oficial, MEP, Blue) usando DolarAPI.com. Permite márgenes de seguridad para proteger contra la volatilidad.
* **Configuración Odoo:** Moneda base `ARS`, moneda puente `USD`. Impuestos y exhibición "Tax Included" para B2C.

## 🏆 4. La Ventaja Injusta: Odoo vs. CMS Tradicionales (WooCommerce / Shopify)
Dado que competir por precio es difícil al inicio, Virtual Store se diferenciará por ser una **operación de clase mundial a costo cero de licencias extra**.
1. **PIM Nativo (Product Info Management):** WooCommerce colapsa con 10,000 productos y atributos complejos. Odoo maneja millones de registros porque su base es PostgreSQL puro y duro.
2. **B2B + B2C Simultáneo:** Puedes habilitar un "Portal B2B" privado para empresas (con reglas de precios por volumen) usando el mismo Odoo, algo muy caro en Magento/Shopify.
3. **Omnicanalidad Operativa (ERP + CRM):** Odoo rastrea si un cliente dejó un carrito abandonado, le genera una oportunidad en el CRM y le puede enviar una cotización formal en PDF automáticamente. ¡Hardware as a Service!

## 🛠️ 5. El Diferencial (Catálogo, Scraping e IA)
Todos publican mal el hardware en Argentina (Nombres truncados, sin fotos, PDFs ilegibles). Virtual Store lo resuelve mediante la suite `tec_catalog_enricher`:

* **Ingesta:** Stock y precios base desde Air Computers.
* **Cascada de Enriquecimiento (Hard Data):** Lenovo PSREF -> Icecat -> BestBuy API -> Product Open Data -> Google Fallback. 
* **Traducción y Redacción (Soft Data - *Prioridad Actual*):** La data de BestBuy/Google viene cruda o en inglés. Se usa Gemini AI nativo en Odoo para:
    1. Traducir al Español Neutro / Argentino.
    2. Homogeneizar especificaciones técnicas en viñetas limpias.
    3. Redactar 'Marketing Descriptions' orientadas a beneficios.

## ⚙️ 6. Centros de Configuración (Hubs)
La suite se parametriza desde 4 *Hubs* lógicos (Inventario > Configuración):
1. **Data Hub (`tec_dropshipping_air`)**: Orígenes y crons.
2. **Logistic Hub (`tec_dropshipping_core`)**: Rutas cross-docking y Tax Maps.
3. **Intelligence Hub (`tec_catalog_enricher`)**: Motores, APIs externas y Prompts de Gemini.
4. **Experience Hub (`tec_website_catalog_pro`)**: UX Premium, badges de escasez (Low Stock), y reglas limitadoras de stock web.

## �️ 7. CTO Roadmap: Pasos a Seguir (Priorizados)

### Fase 1: Calidad de Catálogo y "Filtros de Búsqueda" (Semanas 1-2)
* **Enfoque High-Ticket:** Los esfuerzos de base de datos se centrarán en los productos que mueven la aguja del negocio: **Notebooks, PCs, Mini PCs, Servidores, Monitores, Impresoras y Periféricos Gamers**. Categorías de bajo valor (cables, insumos menores) se procesarán con menor prioridad ("de onda").
* **Atributos Dinámicos (Faceted Search):** El comprador técnico busca usando filtros exactos ("Notebook" > "RAM: 16GB" > "Procesador: Intel i7").
    * **Ejecución Técnica:** Enviaremos la información cruda recolectada (Icecat, BestBuy) al motor de Gemini (`ai_engine.py`), solicitándole que devuelva un **JSON estructurado**. El sistema leerá este JSON y creará/asignará automáticamente los `product.attribute` (ej: Memoria RAM) y sus valores (`product.attribute.value` ej: 16GB) nativos de Odoo.
* **Traducción y Unificación (Gemini "Cute"):** Toda la *hard data* (muchas veces en inglés) pasará por un embudo final donde Gemini la traducirá, limpiará y generará dos bloques listos para ecommerce: una *Technical Description* en tabla HTML y una *Marketing Description* SEO-friendly, persuasiva y estandarizada.

### Fase 2: Robustez y Escala (Semanas 3-4)
* **Job Queues (`queue_job`):** Correr la actualización de precios e imágenes en colas asíncronas de Odoo para evitar Timeouts de Nginx a medida que el catálogo crece a miles de SKUs de Air.
* **Regulación de API Calls:** Limitar solicitudes a Gemini e Icecat para no agotar cuotas gratuitas.

### Fase 3: Conversión y Logística (Mes 2)
* **Integración Logística Local:** Andreani / Correo Argentino / OCA para el cálculo de envíos reales dinámicos.
* **Medio de Pago B2B (Transferencia) y B2C (Pasarela Local):** Validar TodoPago / MercadoPago en ARS con Odoo v19.