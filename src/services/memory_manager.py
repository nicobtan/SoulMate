import os
import sys
import json
import time
import logging
from datetime import datetime

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, log_dir="logs"):
        # Handle path resolution
        if hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up levels: services -> src -> root
            while os.path.basename(base_dir) in ['services', 'src']:
                base_dir = os.path.dirname(base_dir)
            
        self.log_dir = os.path.join(base_dir, log_dir)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.history_file = os.path.join(self.log_dir, "chat_history.jsonl")
        self.mind_vault_file = os.path.join(self.log_dir, "mind_vault.jsonl")
        
        # Initialize Vector DB
        self.chroma_client = None
        self.collection = None
        try:
            import chromadb
            # Persistent Client
            db_path = os.path.join(base_dir, "chroma_db")
            self.chroma_client = chromadb.PersistentClient(path=db_path)
            self.collection = self.chroma_client.get_or_create_collection(name="soulmate_memory")
            logger.info(f"ChromaDB initialized at: {db_path}")
            logger.info(f"ChromaDB initialized at: {db_path}")
        except Exception as e:
            logger.warning(f"ChromaDB not available (installing?): {e}")

        self.rag_logger = None

    def set_rag_logger(self, callback):
        self.rag_logger = callback

    def _log_rag(self, msg):
        if self.rag_logger:
            self.rag_logger(msg)

    def log_interaction(self, user_text, ai_text, persona_id="default"):
        """Logs a chat interaction to JSONL file AND Vector DB."""
        timestamp = datetime.now().isoformat()
        entry = {
            "timestamp": timestamp,
            "user": user_text,
            "ai": ai_text,
            "persona": persona_id
        }
        
        # 1. JSONL Log
        try:
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to chat history: {e}")

        # 2. Vector DB Store
        if self.collection:
            try:
                # Store user input and AI response as separate or combined chunks?
                # For RAG, storing the Q&A pair is often good.
                text_to_embed = f"User: {user_text}\nSoulMate: {ai_text}"
                
                # Simple ID generation
                doc_id = f"mem_{int(time.time()*1000)}"
                
                self.collection.add(
                    documents=[text_to_embed],
                    metadatas=[{"timestamp": timestamp, "persona": persona_id, "type": "conversation"}],
                    ids=[doc_id]
                )
            except Exception as e:
                logger.error(f"Failed to add to Vector DB: {e}")

    def retrieve_context(self, query, n_results=3):
        """Retrieves relevant past conversations based on the query."""
        if not self.collection:
            return ""
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas"]
            )
            
            # Formatting results
            documents = results['documents'][0]  # list of lists
            metadatas = results['metadatas'][0]
            
            # LOGGING
            hit_count = len(documents) if documents else 0
            self._log_rag(f"📂 [Local RAG] Searching for: '{query}'")
            if hit_count > 0:
                self._log_rag(f"✅ [Hit] Found {hit_count} documents.")
                for i, doc in enumerate(documents):
                    meta = metadatas[i] if metadatas else {}
                    ts = meta.get('timestamp', 'Unknown')[:10] # Show Date only
                    snippet = (doc[:50] + "...") if len(doc) > 50 else doc
                    self._log_rag(f"📄 [Content ({ts})] {snippet}")
            else:
                self._log_rag(f"⚠️ [Miss] No relevant documents found.")

            
            if not documents:
                return ""
            
            context_str = "--- Relevant Past Conversations ---\n"
            for i, doc in enumerate(documents):
                meta = metadatas[i] if metadatas else {}
                ts = meta.get('timestamp', 'Unknown')
                context_str += f"- [{ts}] {doc}\n"
            return context_str
            
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return ""

    def get_recent_history(self, limit=10):
        """Retrieves the most recent chat history for context injection."""
        # Simple implementation: read last N lines
        # For production, might want something more efficient or cached
        history = []
        if not os.path.exists(self.history_file):
            return history
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        history.append(json.loads(line))
                    except:
                        continue
        except Exception as e:
            logger.error(f"Failed to read history: {e}")
            
        return history

    def save_mind_vault_entry(self, data: dict):
        """Saves a MindVault entry (philosophy, quotes, etc.)"""
        try:
            # Add timestamp if missing
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()

            with open(self.mind_vault_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            
            # Vector Store
            if self.collection:
                # Store the raw text and analysis
                text_block = f"[User Note] {data.get('source_text', '')}\n[Analysis] {json.dumps(data.get('analysis', {}), ensure_ascii=False)}"
                doc_id = f"mv_{int(time.time()*1000)}"
                
                self.collection.add(
                     documents=[text_block],
                     metadatas=[{"timestamp": data['timestamp'], "type": "mind_vault"}],
                     ids=[doc_id]
                )
            logger.info("MindVault entry saved.")
        except Exception as e:
            logger.error(f"Failed to save MindVault entry: {e}")

    def get_mind_vault_context(self):
        """Retrieves random or recent MindVault entries for context injection."""
        context = ""
        if not os.path.exists(self.mind_vault_file):
            return context
            
        try:
            entries = []
            with open(self.mind_vault_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Get last 5 for now
                for line in lines[-5:]:
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
            
            if entries:
                context += "[User MindVault (Recent Thoughts)]\n"
                for e in entries:
                    analysis = e.get('analysis', {})
                    philosophy = analysis.get('Philosophy', [])
                    quotes = analysis.get('Quotes', [])
                    
                    if philosophy:
                         context += f"- Philosophy: {', '.join(philosophy)}\n"
                    if quotes:
                         context += f"- Quotes: {', '.join(quotes)}\n"
        except Exception as e:
            logger.error(f"Failed to read MindVault: {e}")
            
        return context

    def exists_in_mind_vault(self, content_snippet: str) -> bool:
        """
        Checks if the content already exists in mind_vault.jsonl.
        Uses simple substring or hash check.
        """
        if not os.path.exists(self.mind_vault_file):
            return False
            
        try:
            # Hash check might be better for exact matches, but text file edits might change whitespace.
            # Let's do a simple check. If file allows scaling, we might need a better index.
            # For now (small user text file), reading lines is fine.
            with open(self.mind_vault_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        stored_text = record.get('source_text', '')
                        # Check strict equality of content or substring?
                        # MindLoader sends: "【Title】\nContent"
                        if content_snippet.strip() == stored_text.strip():
                            return True
                    except:
                        continue
        except Exception as e:
            logger.error(f"[Memory] Exists check failed: {e}")
        return False

    def get_random_mind_entry(self) -> dict:
        """Retrieves a random MindVault entry."""
        if not os.path.exists(self.mind_vault_file):
            return None
            
        try:
            import random
            # Reservoir sampling or load all if small
            # Assumption: MindVault is hundreds of lines, not millions. Load all keys.
            entries = []
            with open(self.mind_vault_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entries.append(line)
            
            if not entries: return None
            
            # Pick one
            rand_line = random.choice(entries)
            return json.loads(rand_line)
            
        except Exception as e:
            logger.error(f"[Memory] Random retrieval failed: {e}")
            return None

