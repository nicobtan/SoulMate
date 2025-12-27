import json
import logging
from google.genai import types

class SuggestionEngine:
    """
    Generates diverse conversation suggestions ("Galge" style).
    Generates exactly 8 dynamic suggestions based on categories.
    """
    
    def __init__(self, ai_engine):
        self.ai_engine = ai_engine
        self.logger = logging.getLogger(__name__)

    def generate(self, history_text, user_profile, user_name="あなた") -> list:
        """
        Generates 8 dynamic suggestions.
        Returns a list of strings (Japanese).
        """
        if not self.ai_engine:
            self.logger.warning("AIEngine not available for suggestions.")
            return []

        # System Prompt for Suggestions
        prompt = f"""
[Role]
You are a specialized UI assistant generating "Response Candidates" for a "Galge" (Dating Sim) interface.
The user wants to progress the conversation by clicking buttons, not typing.

[Context]
- User Name: {user_name}
- User Profile: {user_profile}
- Conversation History:
{history_text}

[Task]
Generate exactly 8 dynamic response options for the USER to say next.
Ensure the tone matches the User's personality (if known) or natural polite/casual Japanese.
Use "{user_name}" instead of placeholders like "〇〇さん".

[Categories (Total 8)]
1. Agreement (Positive)
2. Question (Deep Dive)
3. Tsukkomi (Playful/Teasing)
4. Ask Persona's Opinion ("What do you think?")
5. Debate/Counter-argument (Critical thinking)
6. Request Criticism ("Critique my view")
7. Personal Interest (Based on user profile/history)
8. Unexpected/Funny/Chaos

[Constraint]
- Language: JAPANESE ONLY.
- Output MUST be a strict JSON Array of 8 strings.
- NO explanatory text.

[Example Output]
["なるほど、それは一理あるね", "具体的にはどういうこと？", "またそうやって誤魔化す！w", "{user_name}はどう思うの？", "でも、リスクについてはどう考える？", "私の考え、甘いかな？", "それってRustの所有権概念に似てるかも", "いきなりだけどお腹すいた"]
"""
        
        suggestions = []
        try:
            # Use raw generation or structured if AIEngine supports it easily
            # We use generate_content with JSON mime type
            response = self.ai_engine.client.models.generate_content(
                model=self.ai_engine.reasoning_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7 # High variety
                )
            )
            
            if response.text:
                data = json.loads(response.text)
                if isinstance(data, list):
                    suggestions = data
                elif isinstance(data, dict):
                    # Sometimes returns {"suggestions": [...]} despite prompt?
                    suggestions = list(data.values())[0] if data else []
            
        except Exception as e:
            self.logger.error(f"Suggestion Generation Failed: {e}")
            
        # Fallback if AI fails or returns empty
        # Returns 8 diverse static suggestions to ensure UI stability (Total 10 with fixed)
        fallback = [
             "なるほど、面白いね",           # Agreement
             "詳しく教えて？",               # Question
             "それは意外だなぁ",             # Surprise
             f"{user_name}はどう思う？",     # Opinion (Dynamic Name)
             "ちょっと違うかも？",           # Soft Debate
             "私の考え、変かな？",           # Self-reflection
             "最近あった良いことは？",       # Topic Change
             "いきなりだけど、お腹すいた"     # Chaos
        ]
        
        # Robust Filling: Ensure exactly 8 items
        if not suggestions:
            suggestions = fallback
        elif len(suggestions) < 8:
            # Append from fallback (avoiding duplicates if possible, but simple slice is safer for order)
            needed = 8 - len(suggestions)
            suggestions.extend(fallback[:needed])
            
        return suggestions[:8]
