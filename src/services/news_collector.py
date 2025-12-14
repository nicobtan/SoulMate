import feedparser
import random
import logging
import json
import os
import datetime

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsCollector:
    def __init__(self):
        # Path to external config
        self.config_file = os.path.join(os.path.dirname(__file__), '../../news_sources.json')
        self.history_file = os.path.join(os.path.dirname(__file__), '../../logs/news_history.json')
        
        # Load Sources
        self.sources = self._load_sources()
        
        # Load History
        self.history_data = self._load_history()

    def _load_sources(self):
        """Loads news sources from JSON file."""
        if not os.path.exists(self.config_file):
            logger.error(f"News sources config not found: {self.config_file}")
            return {}
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load news sources: {e}")
            return {}

    def _load_history(self):
        """Loads the history of seen URLs."""
        if not os.path.exists(os.path.dirname(self.history_file)):
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {"seen_urls": []}
        return {"seen_urls": []}

    def _save_history(self):
        """Saves the seen URLs to history file."""
        try:
            # Keep history manageable (last 500 items)
            if len(self.history_data["seen_urls"]) > 500:
                self.history_data["seen_urls"] = self.history_data["seen_urls"][-500:]
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history_data, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def fetch_news(self, category=None, limit=2):
        """
        Fetches news with Random Selection and Deduplication.
        """
        # 1. Choose Categories
        if not category:
            # Pick a random category to focus on this time
            category = random.choice(list(self.sources.keys()))
        
        logger.info(f"Collector run. Category: {category}")
        
        # 2. Collect candidates from ALL sources in this category
        urls = self.sources.get(category, [])
        if isinstance(urls, str): urls = [urls] # Handle single string case if any
        
        candidates = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                source_name = feed.feed.get('title', 'Unknown')
                for entry in feed.entries:
                    link = entry.link
                    # DEDUPLICATION CHECK
                    if link in self.history_data["seen_urls"]:
                        continue
                        
                    candidate = {
                        "title": entry.title,
                        "link": link,
                        "summary": (entry.get('summary', '') or entry.get('description', ''))[:250],
                        "source": source_name,
                        "published": entry.get('published', '')
                    }
                    candidates.append(candidate)
            except Exception as e:
                logger.warning(f"Failed to parse source {url}: {e}")

        # 3. Random Selection
        if not candidates:
            logger.info("No new articles found in this category.")
            # Retry with another random category? Or just return empty
            return []
            
        # Shuffle and pick 'limit' items
        selected = random.sample(candidates, min(len(candidates), limit))
        
        # 4. Update History
        for item in selected:
            self.history_data["seen_urls"].append(item['link'])
        self._save_history()
        
        logger.info(f"Selected {len(selected)} new articles.")
        return selected

if __name__ == "__main__":
    # Test Run
    collector = NewsCollector()
    news = collector.fetch_news()
    for n in news:
        print(f"[{n['source']}] {n['title']}\n{n['link']}\n")
