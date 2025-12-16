import json
import re

def _extract_json_from_text(text):
    """
    Extracts a JSON object from a string that might contain mixed text.
    Handles:
    - Pure JSON
    - Markdown ```json ... ```
    - Text with embedded JSON (starts with { and ends with })
    
    Returns:
        dict: Parsed JSON object, or None if failed.
    """
    if not text:
        return None

    # Case A: Markdown code blocks
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
            
    # Case B: Embedded JSON (find first { and last })
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1 and end > start:
        json_str = text[start : end + 1]
        try:
            return json.loads(json_str)
        except:
            pass

    # Case C: Pure JSON (try parsing assuming the whole text is JSON, loosely)
    try:
        return json.loads(text)
    except:
        return None
