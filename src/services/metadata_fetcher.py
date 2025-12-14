import requests
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetadataFetcher:
    def fetch_metadata(self, url):
        """
        Fetches Title and Image from a URL.
        Returns: { 'title': str, 'image': str, 'url': str } or None
        """
        try:
            # Lightweight header to look like a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            html = response.text
            
            # Extract Title
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else "No Title"
            
            # Extract OG Image
            image_match = re.search(r'<meta property="og:image" content="(.*?)"', html, re.IGNORECASE)
            image_url = image_match.group(1).strip() if image_match else None
            
            # Fallback to Twitter Image if no OG
            if not image_url:
                twitter_match = re.search(r'<meta name="twitter:image" content="(.*?)"', html, re.IGNORECASE)
                image_url = twitter_match.group(1).strip() if twitter_match else None
                
            return {
                'title': title,
                'image': image_url,
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Metadata Fetch Failed for {url}: {e}")
            return None
