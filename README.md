# Tecnopolis eCommerce Suite (Odoo v19)

Professional-grade centralized toolkit for Odoo e-commerce, designed to manage high-volume catalogs, dropshipping integrations, and AI-driven content.

## 🚀 Core Features
- **Centralized Dashboard**: A single enterprise settings panel to control all suite functionalities.
- **Provider-Agnostic Dropshipping**: Robust engine for supplier synchronization (`tec_dropshipping_core`).
- **Air Computers Integration**: Native connector for Air Computers catalog and stock synchronization (`tec_dropshipping_air`).
- **Brain (AI Enrichment)**: Automated highlights, product descriptions, and technical specs (`tec_catalog_enricher`).
- **Website Pro (UX/UI)**: Smart badges (New, Low Stock, OFF), official brand links, and product video support (`tec_website_catalog_pro`).
- **Stock Shield**: Cascading safety stock logic (Product > Category > Global) to prevent overselling.

## 📦 Suite Modules
| Module | Name | Hub Type |
| --- | --- | --- |
| `tec_catalog_enricher` | **Tec Catalog Brain** | Intelligence Hub |
| `tec_website_catalog_pro` | **Tec Website Pro** | Experience Hub |
| `tec_dropshipping_core` | **Tec Dropshipping Core** | Logistic Hub |
| `tec_dropshipping_air` | **Tec Dropshipping Air** | Data Hub |

## 🛠️ Configuration
All settings are managed via:
**Inventory > Configuration > Tec Suite Settings**
*(Or via the "Tec Suite" section in the primary Odoo Settings)*

## 📐 Architecture
Organized as a cohesive suite under `enterprise/custom/tec_ecommerce_suite/` for maximum maintainability.
- **Brain**: Absorbed MELI category mapping and AI generation.
- **Pro**: Absorbed Safety Stock and Enrichment display logic.

---
## 👤 Author
- **Francisco Cuello**
- **GitHub**: [francuello10](https://github.com/francuello10)
