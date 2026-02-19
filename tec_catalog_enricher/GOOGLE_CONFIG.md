# 🌐 Configuración de Google Custom Search & YouTube

Este documento detalla los pasos para obtener las credenciales necesarias para el motor de **Google Fallback** (búsqueda de imágenes y PDFs) y **YouTube Reviews** en el Enriquecedor de Catálogo.

---

## 1. Obtener la API Key (Google Cloud)

La **API Key** es la "llave" maestra que permite a Odoo hablar con los servicios de Google.

1.  Ve a [Google Cloud Console](https://console.cloud.google.com/).
2.  Crea un nuevo proyecto (ej: "Odoo Catalog").
3.  En el menú lateral, ve a **APIs y servicios > Biblioteca**.
4.  Busca y **Habilita** las siguientes dos APIs:
    *   `Custom Search API` (Para buscar imágenes y PDFs).
    *   `YouTube Data API v3` (Para buscar videos de reviews).
5.  Ve a **APIs y servicios > Credenciales**.
6.  Haz clic en **Crear credenciales > Clave de API**.
7.  **Copia el valor** (Esta es tu `google_cse_key` y `youtube_api_key`).

---

## 2. Obtener el ID del Buscador (CX)

El **CX** (Search Engine ID) define *dónde* y *qué* buscar en Google.

1.  Ve a [Google Programmable Search Engine](https://cse.google.com/cse/all).
2.  Haz clic en **Añadir**.
3.  **Configuración inicial**:
    *   **Nombre**: Odoo Product Search.
    *   **¿Qué buscar?**: Selecciona "Buscar en toda la Web".
4.  Una vez creado, entra en el motor de búsqueda y busca el interruptor:
    *   **Búsqueda de imágenes**: Cámbialo a **ON**.
5.  Copia el **ID del motor de búsqueda** (Este es tu `google_cse_cx`).

---

## 3. Cargar en Odoo

Ve a tu instancia de Odoo y entra en:
**Ajustes > Ajustes Generales > Enriquecimiento de Catálogo**

*   **API Key Google CSE**: Pega la API Key del Paso 1.
*   **ID Motor (CX)**: Pega el ID del Paso 2.
*   **API Key YouTube**: Pega la misma API Key del Paso 1.
*   **Habilitar Google Fallback**: ✅ Check.
*   **Habilitar YouTube Reviews**: ✅ Check.

---

## 💡 Tips de Uso
*   **Google Fallback**: Solo se activa si los motores oficiales (Lenovo/Icecat) fallan o si no hay imagen de producto.
*   **PDFs**: El sistema buscará específicamente archivos `.pdf` de especificaciones y los adjuntará automáticamente en la pestaña de "Documentos" del producto.
