# Tec Dropshipping Air 🔌 (The Data Hub)

A specialized ingestion engine for **Air Computers (Argentina)**. This module acts as the "Heavy Lifter" for data, transitioning from simple API calls to a robust **Dual-Speed Synchronization Strategy**.

## ⚡ Sync Strategy: Flash vs. Deep

### 1. Flash Ingestion (Inventory & Price)
High-frequency cycles (every 15-60 mins) that only update `list_price` and `qty_available`. 
- **Latency Optimization**: Bypasses heavy ORM logic and `write()` calls where possible to ensure that a 10,000-product catalog can be updated in seconds.
- **Stock Priority**: Maps the Air `S_CBA` and `S_BUE` warehouses to Odoo's priority locations.

### 2. Deep Enrichment (Characteristics & Attributes)
Low-frequency cycles that fetch metadata: high-resolution images, technical specs, and dimensions.
- **Master Identifier: `CODPROV`**: We deprecated the `Part Number` as the primary key. Using the Supplier SKU (`CODPROV`) ensures that multiple configurations or bundles of the same manufacturer PN are treated as distinct, sellable SKUs without collisions.

## 📊 Observability: The "Emoji-Pulse" Log System
Traditional Odoo logs are either too verbose (console) or too messy (HTML chatter).
- **Lightweight Traceability**: Uses a standardized emoji-based string format stored in a simple Char field. This allows the admin to see the sync health (`✅ Success`, `⚠️ No Stock`, `❌ API Error`) directly on the backend list view without loading heavy attachments or logs.
- **Transactional Safety**: Each sync cycle is wrapped in a controlled environment that logs the exact failure point if an API timeout occurs.

## 🛠️ Performance Tuning
- **Parallel Requests**: (WIP) Investigating concurrent API fetching for the characteristics endpoint to further reduce total sync duration.
- **Memory Management**: Uses python generators and `lazy` loading for large XML/JSON responses to maintain a low memory footprint on the Oracle Ampere instance.

---
## 👤 Author
- **GitHub**: [francuello10](https://github.com/francuello10)
