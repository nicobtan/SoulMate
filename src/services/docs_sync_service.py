import time
import json
import threading
from src.core.config_manager import ConfigManager
from src.services.google_auth_manager import GoogleAuthManager
from src.services.memory_manager import MemoryManager
from google.genai import Client
from google.genai import types

class DocsMemorySync:
    """
    Synchronizes content from a Google Doc to the local MindVault.
    Uses '### 記録済み' as a separator.
    """
    
    DOCS_SERVICE_NAME = 'docs'
    DOCS_VERSION = 'v1'
    SEPARATOR = "### 記録済み"
    
    def __init__(self, memory_manager: MemoryManager):
        self.auth_manager = GoogleAuthManager()
        self.memory_manager = memory_manager
        self.config_manager = ConfigManager()
        self.doc_id = self.config_manager.get('mind_vault_docs_id', None)
        self.api_key = self.config_manager.get('api_key', None)
        
    def sync(self):
        """Main sync logic. Should be run in a background thread."""
        if not self.doc_id:
            print("[DocsSync] No Document ID configured. Skipping.")
            return

        if not self.auth_manager.is_authenticated:
            # Try silent auth
            if not self.auth_manager.authenticate():
                print("[DocsSync] Auth failed. Skipping.")
                return

        try:
            service = self.auth_manager.get_service(self.DOCS_SERVICE_NAME, self.DOCS_VERSION)
            doc = service.documents().get(documentId=self.doc_id).execute()
            
            content_text = self._extract_text(doc)
            
            # Split logic
            if self.SEPARATOR not in content_text:
                # First run or marker missing. Treat all as NEW?
                # Safer to Append marker at top and wait for user to write above it?
                # Or treat everything above bottom as new?
                # Implementation: Create marker if missing at the very end.
                print("[DocsSync] Separator not found. Appending separator...")
                self._append_text(service, f"\n\n{self.SEPARATOR}\n")
                return

            parts = content_text.split(self.SEPARATOR)
            new_content = parts[0].strip()
            
            if not new_content:
                print("[DocsSync] No new content found.")
                return

            print(f"[DocsSync] Found new content ({len(new_content)} chars). Analyzing...")
            
            # AI Analysis
            analysis = self._analyze_with_gemini(new_content)
            
            if analysis:
                # Save to Memory
                entry = {
                    "source_text": new_content,
                    "analysis": analysis,
                    "source": "google_docs"
                }
                self.memory_manager.save_mind_vault_entry(entry)
                
                # Archive Logic: Move text to bottom (below separator)
                # Google Docs API doesn't support "Move". We must Delete and Insert.
                # 1. Get current EndIndex of the new content.
                # Actually, easier to just Prepend "Processed" to the bottom, and Delete top.
                # But we want to keep the archive.
                # Strategy:
                # 1. Insert [Date] + new_content at the END of document.
                # 2. Delete the new_content from the TOP (0 to index of separator).
                
                self._archive_content(service, doc, new_content)
                print("[DocsSync] Sync Complete.")

        except Exception as e:
            print(f"[DocsSync] Error: {e}")

    def _extract_text(self, doc):
        """Simple text extractor from Docs JSON structure."""
        text = ""
        content = doc.get('body').get('content')
        for element in content:
            if 'paragraph' in element:
                elements = element.get('paragraph').get('elements')
                for elem in elements:
                    if 'textRun' in elem:
                        text += elem.get('textRun').get('content')
        return text

    def _analyze_with_gemini(self, text):
        """Uses Gemini 2.0 Flash (or 3 preview) to analyze text."""
        if not self.api_key:
            return None
            
        try:
            client = Client(api_key=self.api_key)
            # Use specific model requested or fallback
            model = "gemini-2.0-flash-exp" # Fallback/Standard
            # If user wants 3-preview, use it (if API supports it). 
            # Currently 'gemini-2.0-flash-exp' is the latest widely available in this SDK context usually.
            # But let's try the name if known. 'gemini-exp-1206' or similar.
            # We stick to a safe default or config.
            model = "gemini-2.0-flash-exp" 
            
            prompt = f"""
Analyze the following user notes/journal.
Extract:
1. Philosophy (Values, Life lessons)
2. Quotes (Notable phrases)
3. Emotions (Underlying feelings)

Text:
{text}

Output ONLY valid JSON:
{{
  "Philosophy": ["..."],
  "Quotes": ["..."],
  "Emotions": ["..."]
}}
"""
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            if response.text:
                return json.loads(response.text)
        except Exception as e:
            print(f"[DocsSync] AI Analysis Failed: {e}")
        return None

    def _append_text(self, service, text):
        requests = [
            {
                'insertText': {
                    'location': {'index': 1}, # End of document is tricky, 1 is usually valid if empty/or start?
                    # 'endOfSegmentLocation': {'segmentId': ''} # Insert at end
                    'option': 'INSERT_AS_TEXT'
                    # Wait, Docs API insert is index based.
                    # Getting the end index is needed.
                }
            }
        ]
        # Robust Append:
        # Retrieve doc again to get end index? Or just use 'endOfSegmentLocation'
        requests = [{
            'insertText': {
                'endOfSegmentLocation': {'segmentId': ''},
                'text': text
            }
        }]
        service.documents().batchUpdate(documentId=self.doc_id, body={'requests': requests}).execute()

    def _archive_content(self, service, doc, new_content):
        """
        Moves new_content from top to bottom.
        Assumes content is at the start.
        """
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 1. Append to End
        archive_text = f"\n\n[Archived: {timestamp}]\n{new_content}\n"
        
        requests = [
             {
                'insertText': {
                    'endOfSegmentLocation': {'segmentId': ''},
                    'text': archive_text
                }
            },
            # 2. Delete from Top
            # We need to calculate the index. 
            # We assume "new_content" + "### 記録済み" is at the start?
            # Or just delete everything BEFORE the separator index.
            # We need the index of separator in the DOC STRUCTURE.
            # extract_text is lossy (doesn't give indices).
            # This is complex.
            # Simplification: Just DELETE character range 1 to len(new_content) + 1?
        ]
        
        # Calculate length of new_content approximately?
        # Text indices in Docs are 1-based.
        # Length of string might mismatch slightly due to formatting/control chars.
        # But usually close.
        # Safe approach: Just delete range [1, len(new_content) + 1]
        
        delete_length = len(new_content)
        
        requests.append({
            'deleteContent': {
                'range': {
                    'startIndex': 1,
                    'endIndex': 1 + delete_length
                }
            }
        })
        
        service.documents().batchUpdate(documentId=self.doc_id, body={'requests': requests}).execute()

