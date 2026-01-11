import os
import logging
import datetime
from src.services.external.google_auth_manager import GoogleAuthManager

logger = logging.getLogger(__name__)

class DocsSyncService:
    def __init__(self, api_container=None):
        self.auth_manager = GoogleAuthManager()
        self.api = api_container

    def fetch_and_sync(self, doc_title="MindVault", local_path="settings/MindVault.md"):
        """
        Fetches content from a Google Doc, formats it via AI, 
        prepends to local file, and moves content to Archive section in Google Doc.
        """
        try:
            # 1. Get Drive Service for Search
            drive_service = self.auth_manager.get_service('drive', 'v3')
            docs_service = self.auth_manager.get_service('docs', 'v1')
            
            if not drive_service or not docs_service:
                logger.warning("[DocsSync] Auth failed or cancelled.")
                return

            # 2. Search for the file
            query = f"name = '{doc_title}' and mimeType = 'application/vnd.google-apps.document' and trashed = false"
            results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = results.get('files', [])

            if not files:
                logger.info(f"[DocsSync] Document '{doc_title}' not found in Drive. Skipping sync.")
                return

            file_id = files[0]['id']
            doc_name = files[0]['name']

            # 3. Fetch Document Content
            doc = docs_service.documents().get(documentId=file_id).execute()
            
            # Identify Active Region (Before "### 保存済み")
            active_text, split_index = self._parse_active_content(doc)
            
            if not active_text.strip():
                logger.info("[DocsSync] No new content found (Active region empty).")
                return

            logger.info(f"[DocsSync] Fetched {len(active_text)} chars from Active Region.")

            # 4. Format with Gemini
            formatted_content = self._format_with_gemini(active_text)
            
            # 5. Archive (Prepend) to Local File
            self._save_to_local_mindvault(formatted_content, local_path)
            
            # 6. Move processed content to Archive Section in Google Doc
            self._move_content_to_archive(docs_service, file_id, split_index, active_text, doc)
            
        except Exception as e:
            logger.error(f"[DocsSync] Sync failed: {e}", exc_info=True)

    def _parse_active_content(self, doc):
        """
        Extracts text ONLY before the '### 保存済み' header.
        Returns (active_text, split_index).
        """
        text_output = []
        content = doc.get('body').get('content')
        split_index = None
        
        for element in content:
            if 'paragraph' in element:
                para_text = ""
                elements = element.get('paragraph').get('elements')
                start_idx = element.get('startIndex')
                
                for elem in elements:
                    if 'textRun' in elem:
                        para_text += elem.get('textRun').get('content')
                
                # Check for Marker
                if "### 保存済み" in para_text:
                    split_index = start_idx
                    break
                
                text_output.append(para_text)
            
            elif 'table' in element:
                # Basic table handling (just flatten text)
                # ... (Tables usually not used for this, skipping complex logic for brevity)
                pass

        if split_index is None:
            # Marker not found, treated as whole doc. 
            # End index is effectively the end of content minus 1 (trailing newline)
            try:
                split_index = content[-1]['endIndex'] - 1
            except:
                split_index = 1
                
        return "".join(text_output), split_index

    def _format_with_gemini(self, text: str) -> str:
        """Structures the raw text using AI."""
        if not self.api or not hasattr(self.api, '_ai_engine'):
            logger.warning("[DocsSync] AI Engine not available. Using raw text.")
            return text

        prompt = f"""
以下のテキストを分析し、内容ごとに適切な見出し（## カテゴリ名）を付けてMarkdown形式で整理してください。
箇条書きは - に統一してください。
カテゴリ例: ## マインド, ## 技術, ## アイデア, ## 趣味, ## 語録 など。
出力は整形後のMarkdownテキストのみ。余計な挨拶は不要です。

[Input Text]
{text}
"""
        try:
            response = self.api._ai_engine.generate_response(prompt)
            if isinstance(response, dict):
                if 'text' in response: return str(response['text']).strip()
                if 'response' in response: return str(response['response']).strip()
                if 'content' in response: return str(response['content']).strip()
                return str(response)
            return str(response).strip()
        except Exception as e:
            logger.error(f"[DocsSync] AI Formatting failed: {e}")
            return text

    def _save_to_local_mindvault(self, content_text: str, local_path: str):
        """Prepends content to local MD file with timestamp."""
        params = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        timestamp_header = f"\n[Archived: {params['timestamp']}]\n"
        
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        existing_content = ""
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()

        new_blocks = timestamp_header + content_text + "\n" + existing_content
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(new_blocks)
        logger.info(f"[DocsSync] Saved formatted content to {local_path}")

    def _move_content_to_archive(self, docs_service, file_id, split_index, active_text, doc):
        """
        Moves the processed content to the end of the document under '### 保存済み'.
        """
        try:
            requests = []
            
            # 1. Determine if header exists (split_index found means it existed)
            # But wait, split_index could be end of doc if not found.
            # We need to check exact condition.
            
            content = doc.get('body').get('content')
            end_of_doc_index = content[-1]['endIndex'] - 1
            
            header_exists = False
            # Re-check locally if header was found 'inside' body or at end
            if split_index < end_of_doc_index:
                 # It was found somewhere in the middle (or top)
                 # However, if it was found, _parse_active_content sets split_index TO the header position.
                 # So split_index < end_of_doc_index is likely true.
                 # Let's verify text again to be safe? No, expensive.
                 # Just assume if split_index != end_of_doc_index roughly.
                 pass

            # Timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            archive_block = f"\n\n[Archived: {timestamp}]\n{active_text}"

            # If header didn't exist (split_index implies whole doc), we append header too.
            # Logic: If split_index matches end of doc, we didn't find the header.
            # (Note: _parse_active_content sets it to end-1 if not found)
            if split_index >= end_of_doc_index - 5: # Fuzziness for trailing chars
                 archive_block = f"\n\n### 保存済み\n{archive_block}"
            
            # Operation Order:
            # 1. Insert at End
            requests.append({
                'insertText': {
                    'text': archive_block,
                    'endOfSegmentLocation': {'segmentId': ''} # Target Body
                }
            })
            
            # 2. Delete from Start (Active Region)
            # Only delete if there was text
            if split_index > 1:
                requests.append({
                    'deleteContentRange': {
                        'range': {
                            'startIndex': 1,
                            'endIndex': split_index
                        }
                    }
                })

            docs_service.documents().batchUpdate(documentId=file_id, body={'requests': requests}).execute()
            logger.info("[DocsSync] Active content moved to Archive section.")
            
        except Exception as e:
            logger.error(f"[DocsSync] Failed to move content to archive: {e}")
