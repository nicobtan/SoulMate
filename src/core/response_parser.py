import json
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ResponseParser:
    """
    Parses AI responses into structured JSON.
    Ensures that raw thought processes are NEVER leaked as chat responses.
    """
    def parse(self, raw_text: str) -> Dict[str, Any]:
        text = raw_text.strip()
        data = {}

        # 1. Clean Markdown (```json ... ```)
        match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        
        # 2. Extract JSON Object ({ ... })
        if "{" in text:
            first_brace = text.find("{")
            last_brace = text.rfind("}")
            if last_brace > first_brace:
                text = text[first_brace : last_brace + 1]
        
        # 3. Try Strict Parsing
        try:
            data = json.loads(text)
            return self._validate_and_normalize(data)
        except json.JSONDecodeError:
            pass # Fallback
        
        # 4. Regex Fallback (Key: Value)
        logger.info("[ResponseParser] JSON decode failed. Trying regex fallback.")
        return self._regex_fallback(raw_text)

    def _regex_fallback(self, text: str) -> Dict[str, Any]:
        result = {}
        # Extract values using regex looking for "key: value" pattern
        def extract(key):
            m = re.search(rf"(?:^|\n)\s*{key}\s*[:=]\s*(.*?)(?=\n\s*(?:thought|response|emotion|suggestions|action_command)|$)", text, re.DOTALL | re.IGNORECASE)
            return m.group(1).strip().strip('"') if m else ""
        
        result["thought"] = extract("thought")
        result["response"] = extract("response") or extract("text")
        result["emotion"] = extract("emotion")
        result["action_command"] = extract("action_command")
        
        # Suggestions
        s_match = re.search(r"suggestions\s*[:=]\s*\[(.*?)\]", text, re.DOTALL | re.IGNORECASE)
        if s_match:
            result["suggestions"] = [s.strip().strip('"\'') for s in s_match.group(1).split(",") if s.strip()]
        
        return self._validate_and_normalize(result)

    def _validate_and_normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Normalize keys
        if "text" in data and "response" not in data: data["response"] = data["text"]
        
        # Defaults
        data.setdefault("response", "")
        data.setdefault("emotion", "neutral")
        data.setdefault("suggestions", [])
        data.setdefault("thought", data.get("expression_reason", ""))
        data.setdefault("action_command", "")
        
        # SAFETY: If response looks like internal thought (starts with "Category:" or "User is..."), clear it.
        resp = data["response"]
        
        # Robust check: Ensure resp is string
        if not isinstance(resp, str):
            if isinstance(resp, dict):
                # Try to extract text if it's a dict (e.g. nested {"text": "..."})
                resp = resp.get("text", resp.get("response", str(resp)))
            else:
                resp = str(resp)
            data["response"] = resp

        if resp and (resp.startswith("Category:") or "User is idle" in resp):
            logger.warning(f"[ResponseParser] Leaked thought detected in response. Clearing. Content: {resp[:20]}...")
            data["thought"] += f" (Leaked: {resp})"
            data["response"] = ""
            
        return data
