import random
from collections import deque

class TopicSelector:
    """
    Selects random topics, switching between "Comfort Zone" (User Interests) 
    and "Discovery Zone" (Serendipity/Chaos), avoiding recent duplicates.
    """
    
    # Chaos/Serendipity Topics (The "Unknown" List)
    # Topics that are likely clearly distinct from typical Tech/Game interests.
    SERENDIPITY_TOPICS = [
        "Antarctic Expeditions (南極探検)",
        "The History of Cheese (チーズの歴史)",
        "Quantum Entanglement (量子もつれ)",
        "Sumerian Clay Tablets (シュメール人の粘土板)",
        "Deep Sea Bioluminescence (深海生物の発光)",
        "The Voynich Manuscript (ヴォイニッチ手稿)",
        "Extreme Ironing (エクストリーム・アイロン掛け)",
        "Tardigrades (クマムシ)",
        "The Library of Alexandria (アレクサンドリア図書館)",
        "Bioluminescent Fungi (光るキノコ)",
        "Dugong/Manatee Conservation (ジュゴンの保護)",
        "Medieval Castles (中世の城)",
        "Origami Engineering (折り紙工学)",
        "Fermentation Science (発酵の科学)"
    ]

    def __init__(self, history_size=5):
        self.recent_topics = deque(maxlen=history_size)

    def decide_topic(self, candidates: list) -> dict:
        """
        Decides a topic using Chaos Logic.
        Returns a dict: {"topic": str, "source": "comfort" | "chaos"}
        """
        # 1. Determine Mode (30% Chaos, 70% Comfort)
        # However, if candidates is empty, force Chaos.
        is_chaos = random.random() < 0.3 or not candidates
        
        if is_chaos:
            topic_list = self.SERENDIPITY_TOPICS
            source = "chaos"
        else:
            topic_list = candidates
            source = "comfort"

        # 2. Filter out recently used topics
        available = [t for t in topic_list if t not in self.recent_topics]
        
        # 3. Fallback: If all used, reset available to full list (allow repeat)
        if not available:
            available = topic_list
        
        # 4. Pick Randomly
        chosen_topic = random.choice(available)
        self.recent_topics.append(chosen_topic)
        
        return {
            "topic": chosen_topic,
            "source": source
        }

    def get_instruction(self, topic: str, source: str) -> str:
        """Generates the system instruction for the chosen topic."""
        
        base = f"Talk about '{topic}'."
        
        if source == "chaos":
            return f"""
[Serendipity Mode 🎲]
The user did NOT ask for this. You are surprising them with a random, interesting topic: "{topic}".
Start deeply and passionately about this topic.
Connect it to a philosophical lesson or a fun trivial fact.
"Did you know...?" or "I was just reading about..."
"""
        else:
            return f"""
[Comfort Zone 🏠]
Topic: "{topic}" (User's Interest).
Share the latest news or a deep fact about this.
Relate it to the user's known profile (e.g. if Dev, relate to code/logic).
"""
