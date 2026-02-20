# Tec Dropshipping Core 📦 (The Logistic Hub)

The mission-critical logistics and financial backbone of the Tecnopolis Suite. It standardizes fragmented supplier data into a clean, searchable, and profitable catalog. Built for scale, handling 30k+ active SKUs and 34k+ brand variations.

## 🚀 Engineered for Precision

### 1. The Normalization Engine (Regex & Alias Mapping)
Supplier brand data is notoriously dirty. This module implements a robust **Alias Resolution Engine** that maps 34,700+ variations (e.g., "HEWLETT PACKARD", "HP INC", "H.P.") to normalized canonical records. 
- **DB Optimization**: Uses **stored computed fields** (`product_count`) and PostgreSQL indices on normalization keys to ensure that searching through 35,000 brands doesn't incur significant ORM overhead.
- **Auto-Discovery**: When the `get_normalized_brand()` method misses, it triggers an automated discovery flow, creating new entries and queuing them for branding enrichment.

### 2. Brand Identity & SVG Injection
Integrates with the **Simple Icons CDN** to fetch and store SVG signatures. 
- **Non-Storing Strategy**: Fetches official slugs and metadata to avoid bloating `ir.attachment` when possible, injecting high-res SVG logos directly into the UI for a premium, trustworthy look.
- **Metadata Cascade**: Once a brand is identified, it auto-populates `website_url` and generates an SEO-optimized HTML description via the `tec_catalog_enricher` bridge.

### 3. High-Precision Financials
- **Dynamic VAT Mapping**: Standardizes various supplier tax formats (10.5%, 21%, Excerpt) into Odoo's native `account.tax` engine.
- **Multicurrency Buffer**: Implements a safety-spread logic for USD-to-ARS price calculation, protecting the business from the volatility of the Argentinian Peso during synchronization lags.

## 📐 Technical Architecture
- **Model Inheritance**: Lean extensions on `product.template` and `product.brand` (if used) to maintain native compatibility.
- **Query Efficiency**: Uses Odoo's `_read_group` strategy for `product_count` triggers, avoiding the N+1 problem when rendering brand lists.

---
## 👤 Author
- **GitHub**: [francuello10](https://github.com/francuello10)
