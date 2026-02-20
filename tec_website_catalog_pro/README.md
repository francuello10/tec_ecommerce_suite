# Tec Website Pro ✨ (The Experience Hub)

The premium frontend layer for the Tecnopolis Suite. It bridges the gap between "Corporate ERP" and "Elite eCommerce," transforming Odoo's website builder into a high-performance **World-Class CMS**.

## 🎨 Frontend Engineering

### 1. SVG Identity Injection
Instead of heavy bitmap logos, we use **SVG Signatures** for brands.
- **Performance**: Injects vector logos via CDN (Simple Icons), reducing page weight and ensuring pixel-perfect clarity on Retina displays.
- **UI Consistency**: Standardizes the "Visual Weight" of different brand logos (e.g., Apple vs ASUS) through CSS normalization.

### 2. Conversional UX Architecture
- **QWeb Template Inheritance**: Cleanly overrides Odoo's native `website_sale` templates to inject professional-grade tabs, manufacturer badges, and rich technical specifications without breaking core compatibility.
- **Smart Logic Badges**: Driven by real-time business data:
  - `HOT DEALS`: Triggered by dynamic `price_extra` or discount rules.
  - `LAST UNITS`: Real-time stock scarcity warning based on **Stock Shield** thresholds.

### 3. The "Stock Shield" Protocol
A cascading safety-net to prevent the "Double-Sell" nightmare in high-volatility dropshipping:
- **Safety Levels**: `Global` -> `Category` -> `Product`. 
- **Business Logic**: Automatically hides or disables the "Add to Cart" button when stock levels hit a defined "Fear Threshold" (e.g., 2 units), protecting the business from the 15-minute sync lag of supplier stocks.

## 🚀 Speed & SEO
- **Lazy Image Loading**: Full support for Odoo's native lazy-loading and WebP conversion to maintain a **Lighthouse Score of 90+**.
- **Dynamic Meta-Descriptions**: Programmatic injection of brand and product metadata into the `<head>` to ensure top ranking for high-ticket keywords (Notebooks, Servers).

## 📐 Implementation Detail
- **SCSS/CSS**: Uses Odoo's asset bundle system for efficient delivery. No external, heavy CSS frameworks.
- **Pure JavaScript**: Minimal footprint, using Odoo's `public_widget` system for interactive elements (Video modals, tab switching).

---
## 👤 Author
- **GitHub**: [francuello10](https://github.com/francuello10)
