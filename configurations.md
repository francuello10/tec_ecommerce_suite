# 🛠️ Hub Configuration Guide

The `tec_ecommerce_suite` centralizes all options in 4 logical hubs within a single professional panel.

## 📍 Unified Access
Go to **Settings > Tecnopolis Suite** or **Inventory > Configuration > Tec Suite Settings**.

### 1. Data Hub (`tec_dropshipping_air`)
*   **Air Computers Adapter**: Configure URLs for Catalog CSV and Characteristics CSV.
*   **Auto-Sync**: Standard crons for stock and content updates.
*   **Auto-Creation**: Option to auto-create brands found in supplier files.

### 2. Logistic Hub (`tec_dropshipping_core`)
*   **Backends**: Manage multiple providers and their specific margin rules.
*   **Locations**: Map supplier branches/warehouses to local inventory locations.
*   **Tax Maps**: Define how supplier VAT (10.5/21) translates to local Odoo taxes.

### 3. Intelligence Hub (`tec_catalog_enricher`)
*   **Tec Catalog Brain**: Centralizes all AI and enrichment settings.
*   **Engines**: Icecat, Google CSE, and Gemini AI.
*   **MELI Mapping**: Automated logic to map supplier taxonomies to MercadoLibre Argentina categories.

### 4. Experience Hub (`tec_website_catalog_pro`)
*   **Premium UX**: Toggle tabs, brands, and videos display.
*   **Conversion Badges**: Smart labels for "New", "Low Stock", and "OFF".
*   **Stock Shield**: Configure safety stock buffers to prevent overselling on the web.

---

## ⚙️ Recommended Odoo v19 Base Config (ARS)

| Section | Recommended Action |
| --- | --- |
| **Currency** | Set `ARS` as default and enable `USD` for reference. |
| **Taxes** | Set **Website > Settings > Tax Display: Tax Included** for consumer-facing shops. |
| **Safety Stock** | Use `inherit` mode on products to rely on Category-level defaults. |

---
> [!IMPORTANT]
> **Single Source of Truth**: All API Keys (Gemini, Icecat) are now managed globally within the Brain Hub to avoid duplication.
