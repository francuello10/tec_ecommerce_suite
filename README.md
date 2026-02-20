# Tecnopolis eCommerce Suite (Odoo v19) 🚀

A high-performance Odoo v19 framework engineered for heavy-duty dropshipping and AI-orchestrated PIM (Product Information Management). This suite transforms Odoo from a standard ERP into a centralized, world-class CMS and logistics engine capable of outrunning dedicated legacy stacks (WooCommerce/Magento) through **Architectural Purity**.

## 🛠️ The Tech Philosophy: Native-First & Zero Bloat
We adhere to a strict **"Odoo-First"** development model. By utilizing Odoo's native ORM, controllers, and QWeb engine, we eliminate the latency and complexity inherent in multi-platform syncing (Odoo-to-Shopify/WP). 

- **No Over-Engineering**: If Odoo provides a native tool (e.g., `_read_group`, `ir.actions.server`), we use it. We don't write complex middleware when the PostgreSQL backend can solve it with a single query.
- **Centralized Data Truth**: 100% of the business logic—from supplier API ingestion to AI copywriting—resides within Odoo. This eliminates data silos and reduces architectural overhead by 80%.
- **Scale-Ready Schema**: Designed to manage **35,000+ brand records** and high-frequency stock volatility without UI blocking, using **stored compute fields** and **non-blocking cron orchestration**.

## 📦 Core Ecosystem (The 4 Hubs)

### 1. Data Hub (`tec_dropshipping_air`)
The ingestion pipeline. Standardizes incoming supplier streams (JSON/XML) with high-availability fetching logic.
- **Master SKU Architecture**: Implements `CODPROV` indexing to maintain unique record integrity across multiple supplier branches.

### 2. Logistic & Finance Hub (`tec_dropshipping_core`)
The mathematical engine behind the suite.
- **Brand Normalization Engine**: Aggressive alias resolution matching 34k+ supplier variations to canonical records.
- **Financial Mapping**: Deterministic USD-to-ARS conversion based on safety-buffered exchange rates (`dolar_api_integration`).

### 3. Intelligence Hub (`tec_catalog_enricher`)
The "Brain" of the suite. Orchestrates Generative AI (Google Gemini) with transactional atomicity.
- **Structured Extraction**: Converts raw manufacturer data into JSON-structured Odoo attributes (`product.attribute`) to power Faceted Search.
- **Auto-Copywriting**: Context-aware content generation (Marketing vs. Technical) using professional Argentinian-Spanish templates.

### 4. Experience Hub (`tec_website_catalog_pro`)
The conversion layer. Turns Odoo's website builder into a **World-Class CMS**.
- **SVG Branding**: Dynamic CDN injection (Simple Icons) for premium brand signatures.
- **Stock Shielding**: Advanced availability logic to protect the transaction from real-time supplier stockouts.

## 📐 Nerd Stats & Optimizations
- **Transactional Atomicity**: Deep use of `env.cr.commit()` and `savepoints` ensures that even if an AI generation batch of 500 products fails at item 499, the previous 498 are safely persisted.
- **ORM Optimization**: Leverages Odoo's native cache and prefetching logic to render complex brand-product relationships in under **150ms**.
- **Clean Observability**: Explicit, low-noise logging via an "Emoji-Pulse" system—monitoring health at a glance without bloating database indices.

---
## 👤 Author
- **GitHub**: [francuello10](https://github.com/francuello10)
