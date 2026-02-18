import requests
import logging
import time

_logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    _logger.warning("BeautifulSoup library not found. Lenovo scraping will be disabled.")
    BeautifulSoup = None

def enrich_product(product, mpn):
    """
    Scrapes Lenovo PSREF for technical data.
    Rate Limit: 1 request/sec
    """
    time.sleep(1) # Rate Limiting
    
    url = f"https://psref.lenovo.com/syspool/Sys/GetSearchItems?search={mpn}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                item = data[0]
                product_url = f"https://psref.lenovo.com/Detail/{item.get('Url')}"
                product.external_product_url = product_url
                
                # Fetch details page
                page_response = requests.get(product_url, timeout=10)
                if page_response.status_code == 200:
                    soup = BeautifulSoup(page_response.content, 'html.parser')
                    
                    # Image
                    img_tag = soup.find('img', {'id': 'myimage'})
                    if img_tag:
                         img_url = img_tag.get('src')
                         if not img_url.startswith('http'):
                             img_url = f"https://psref.lenovo.com{img_url}"
                         # Download and set image (simplified)
                         img_content = requests.get(img_url).content
                         product.image_1920 = img_content
                    
                    # Specs (Simplified parsing logic)
                    # Ideally we parse the table and map to attributes
                    
                    return True
    except Exception as e:
        _logger.error(f"Lenovo Enrichment Failed for {mpn}: {e}")
    
    return False
