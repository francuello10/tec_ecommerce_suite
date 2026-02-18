import requests
import logging

_logger = logging.getLogger(__name__)

def enrich_video(product):
    """
    Searches YouTube for a review video.
    """
    api_key = product.env['ir.config_parameter'].sudo().get_param('tec_catalog_enricher.youtube_api_key')
    
    if not api_key:
         _logger.warning("YouTube API Key missing.")
         return False

    if product.video_url:
        return True # Already has video

    query = f"{product.product_brand_id.name} {product.name} review español"
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&key={api_key}&type=video&maxResults=1"
    
    try:
        res = requests.get(url).json()
        if 'items' in res and len(res['items']) > 0:
            video_id = res['items'][0]['id']['videoId']
            product.video_url = f"https://www.youtube.com/watch?v={video_id}"
            return True
    except Exception as e:
        _logger.error(f"YouTube Search Failed: {e}")
        
    return False
