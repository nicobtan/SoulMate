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
        except Exception as e:
            logger.warning(f"ChromaDB not available (installing?): {e}")

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
                n_results=n_results
            )
            
            # Formatting results
            documents = results['documents'][0]  # list of lists
            
            if not documents:
                return ""
            
            context_str = "--- Relevant Past Conversations ---\n"
            for doc in documents:
                context_str += f"- {doc}\n"
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
