# Tec Catalog Brain 🧠 (The Intelligence Hub)

The ultra-lean PIM (Product Information Management) engine. It leverages Generative AI (Google Gemini) to transform raw, fragmented supplier data into high-converting, professional commerce assets.

## 🤖 AI Orchestration (Gemini Pro Native)

### 1. Transactional Atomic Batches
Enriching 500+ products with AI is risky for server performance. We implemented a **Safe-Batching Logic**:
- **Atomic Commits**: For every block of processed products, the system executes an `env.cr.commit()`. If the cron task is interrupted by a server restart or timeout, work is never lost.
- **Savepoint Isolation**: Each individual product enrichment is wrapped in a `savepoint`, preventing a single "malformed AI response" from rolling back the entire batch.

### 2. Structured JSON Attribute Extraction
Beyond simple text, the "Brain" requests **Structured JSON** from Gemini:
- **Trait Mining**: Extracts specific technical values (e.g., `RAM: 16GB`, `CPU: i7-13700H`, `Screen: 15.6" IPS`) from raw descriptions.
- **Auto-Attribute Creation**: Maps these JSON keys to Odoo's `product.attribute` model automatically, enabling **Faceted Search (Filters)** on the frontend without any manual data entry.

### 3. Multi-Source Metadata Cascade
Implements a "Best-Data-Wins" logic:
1. **Official Channel**: Lenovo PSREF / HP Metadata.
2. **Standard API**: Icecat (Technical Specs).
3. **AI Generation**: Gemini translates and unifies the style into "Argentinian-Neutral" Spanish.
4. **Fallback**: Google Search / Media Discovery for missing images.

## ⚙️ Technical Specs
- **Prompt Engineering**: Highly optimized system prompts that force Gemini to act as a **Technical Hardware Analyst**, ensuring descriptions are factual and devoid of "marketing fluff".
- **Media Prioritization**: Smart logic to download and store only the best representation of a product, using `ir.attachment` management to preserve storage on the cloud instance.

---
## 👤 Maintainer
- **GitHub**: [francuello10](https://github.com/francuello10)

