import os
import yaml
import logging
import threading
from src.services.ai_engine import AIEngine

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self, ai_engine: AIEngine = None):
        """
        Initialize MemoryService.
        Args:
            ai_engine: Instance of AIEngine for extraction.
        """
        self.ai_engine = ai_engine
        
        # Define paths as per requirement
        # Assumes running from project root
        self.profile_path = "settings/user_profile.yaml"
        self.facts_path = "settings/learned_facts.yaml"
        
        # Ensure memory directory exists
        self._ensure_paths()

    def set_ai_engine(self, ai_engine):
        """Setter for AI Engine if not available at init."""
        self.ai_engine = ai_engine

    def _ensure_paths(self):
        """Ensure necessary directories and files exist."""
        # memory dir
        mem_dir = os.path.dirname(self.facts_path)
        if mem_dir and not os.path.exists(mem_dir):
            os.makedirs(mem_dir, exist_ok=True)
            logger.info(f"Created memory directory: {mem_dir}")
            
        # learned_facts.yaml (create if missing)
        if not os.path.exists(self.facts_path):
            self._save_facts_to_file([])
            logger.info(f"Created initial memory file: {self.facts_path}")

        # user_profile (warning if missing, but read-only)
        if not os.path.exists(self.profile_path):
            logger.warning(f"User profile not found at {self.profile_path}")

    def _load_yaml(self, path):
        try:
            if not os.path.exists(path):
                return {}
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load YAML {path}: {e}")
            return {}

    def _save_facts_to_file(self, facts_list):
        try:
            data = {'learned_facts': facts_list}
            with open(self.facts_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save facts to {self.facts_path}: {e}")
            return False

    def get_combined_context(self):
        """
        Read User Profile and Learned Facts, return formatted context string.
        """
        # 1. Read User Profile (Basic)
        profile_data = self._load_yaml(self.profile_path)
        
        # 2. Read Learned Facts (Dynamic)
        facts_data = self._load_yaml(self.facts_path)
        learned_facts = facts_data.get('learned_facts', [])

        # Format Text
        context_str = ""

        # Profile Section
        if profile_data:
            context_str += "[User Profile (Basic)]\n"
            for key, val in profile_data.items():
                if isinstance(val, list):
                    val_str = ", ".join(map(str, val))
                    context_str += f"- {key}: {val_str}\n"
                elif isinstance(val, dict):
                    # Flat string for simple dict
                    context_str += f"- {key}: {json.dumps(val, ensure_ascii=False)}\n"
                else:
                    context_str += f"- {key}: {val}\n"
            context_str += "\n"

        # Memory Section
        if learned_facts:
            context_str += "[Learned Memory (Facts & Habits)]\n"
            for fact in learned_facts:
                context_str += f"- {fact}\n"
            context_str += "\n"

        return context_str.strip()

    def extract_and_save_memory(self, chat_history):
        """
        Extract new facts from chat history and save them.
        Should be run in a separate thread.
        """
        if not self.ai_engine:
            logger.warning("AI Engine not set in MemoryService. Skipping extraction.")
            return

        # 1. Analyze
        try:
            prompt = f"""
[Memory Extraction Task]
Analyze the following conversation log.
Extract any NEW facts about the user's preferences, dislikes, habits, plan, or status.
Focus on long-term info (e.g. "User likes coffee", "User is studying Python").
Ignore trivial info (e.g. "User is saying hello").

[Conversation Log]
{chat_history}

[Output Requirement]
- Return ONLY the extracted fact as a short sentence.
- If multiple facts, separate them with newlines.
- If nothing new/notable is found, return "None".
"""
            # Call AI
            response = self.ai_engine.generate_response(prompt)
            
            # Parse response (handle dict if engine returns JSON object usually)
            text_result = ""
            if isinstance(response, dict):
                text_result = response.get('response', '')
            else:
                text_result = str(response)

            text_result = text_result.strip()

            if not text_result or text_result.lower() == "none":
                return # Nothing to save

            # 2. Save
            # Load existing
            facts = self._load_yaml(self.facts_path).get('learned_facts', [])
            
            # Add new facts (split by newline)
            new_facts = [line.strip() for line in text_result.split('\n') if line.strip()]
            
            updated = False
            for f in new_facts:
                if f not in facts:
                    facts.append(f)
                    logger.info(f"Memory Learned: {f}")
                    updated = True
            
            if updated:
                self._save_facts_to_file(facts)
        
        except Exception as e:
            logger.error(f"Memory Extraction Error: {e}")
