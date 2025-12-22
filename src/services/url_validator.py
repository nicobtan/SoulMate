import re
import requests
import threading
import logging

logger = logging.getLogger(__name__)

class UrlValidator:
    """
    Validates URLs in text to prevent 404/Dead links.
    """
    
    @staticmethod
    def validate_and_clean(text: str) -> str:
        """
        Scans text for URLs, checks their liveness (HEAD request),
        and replaces dead links with a placeholder.
        """
        # Regex for URLs (HTTP/HTTPS)
        url_pattern = r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
        urls = re.findall(url_pattern, text)
        
        if not urls:
            return text
            
        # We need to check each URL. 
        # Since this needs to happen before responding, we want it fast.
        # However, Python requests is blocking. We can use threads for parallel checks.
        
        dead_links = []
        lock = threading.Lock()
        
        def check_url(url):
            try:
                # 2 second timeout is strict but good for UX
                response = requests.head(url, timeout=2, allow_redirects=True)
                if response.status_code >= 400:
                    # Double check with GET if HEAD fails (some servers block HEAD)
                    # But for speed, maybe just mark as suspicious?
                    # Let's try a quick GET stream verify
                    try:
                        r2 = requests.get(url, timeout=2, stream=True)
                        if r2.status_code >= 400:
                            raise Exception("Dead link")
                        r2.close()
                    except:
                        raise Exception("Dead link confirm")
                        
            except Exception as e:
                with lock:
                    dead_links.append(url)
                    logger.warning(f"[UrlValidator] Dead link detected: {url} ({e})")

        threads = []
        for url in urls:
            t = threading.Thread(target=check_url, args=(url,))
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
            
        # Replace dead links
        cleaned_text = text
        for dead_url in dead_links:
            # Replace markdown link [text](url) -> [text](リンク切れ)
            # OR just the URL -> (リンク切れ)
            
            # Simple replace logic
            # Case 1: (http...) inside markdown parens
            if f"({dead_url})" in cleaned_text:
                cleaned_text = cleaned_text.replace(f"({dead_url})", "(リンク切れ)")
            # Case 2: Raw URL
            else:
                cleaned_text = cleaned_text.replace(dead_url, "(リンク切れ)")
                
        return cleaned_text
