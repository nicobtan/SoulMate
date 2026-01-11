import os
import logging
import re
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

class MindLoader:
    def __init__(self, services_container):
        self.services = services_container
        # Assume usage: self.services.memory_manager

    def sync_mind_vault(self, file_path):
        """
        Reads a user text/md file and synchronizes it with the MindVault (DB).
        Parses granularity: Bullet points as individual entries.
        """
        if not os.path.exists(file_path):
            logger.warning(f"[MindLoader] File not found: {file_path}")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            entries = self._parse_content(content)
            count = 0
            
            # Check dependency
            if hasattr(self.services, '_memory_manager'):
                mgr = self.services._memory_manager
            elif hasattr(self.services, 'memory_manager'):
                mgr = self.services.memory_manager
            else:
                logger.error("[MindLoader] MemoryManager not found in services.")
                return
            
            for entry in entries:
                # Check for existence of content (bullet point text)
                if mgr.exists_in_mind_vault(entry['source_text']):
                    continue
                
                # Save to DB
                mgr.save_mind_vault_entry(entry)
                count += 1
            
            if count > 0:
                logger.info(f"[MindLoader] Imported {count} new entries from {file_path}")
            else:
                logger.info(f"[MindLoader] No new entries found in {file_path}")

        except Exception as e:
            logger.error(f"[MindLoader] Sync failed: {e}", exc_info=True)

    def _parse_content(self, text):
        """
        Parses Markdown content STRICTLY.
        - [Archived: ...] -> Updates current_timestamp
        - ## Category     -> Updates current_category
        - - Text          -> New Entry (MindVault source)
        - ### Header      -> IGNORED (System headers)
        """
        valid_entries = []
        
        lines = text.replace('\r\n', '\n').split('\n')
        
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        current_category = "General"
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Timestamp Header
            if line.startswith('[Archived:'):
                m = re.search(r'\[Archived: (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]', line)
                if m:
                    current_timestamp = m.group(1)
                continue
            
            # Ignore System Headers (###)
            if line.startswith('###'):
                continue

            # Category Header (##)
            if line.startswith('##'):
                current_category = line.replace('##', '').strip()
                continue
                
            # Bullet Point (Entry) - Must start with "- "
            if line.startswith('- '):
                content = line[2:].strip() # Remove "- "
                if not content: continue
                
                entry_data = {
                    "source_text": content,
                    "analysis": {
                        "Category": [current_category],
                        "Philosophy": [],
                        "Quotes": []
                    },
                    "timestamp": current_timestamp
                }
                valid_entries.append(entry_data)
            
        return valid_entries
