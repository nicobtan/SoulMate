import random

class AffectionManager:
    """
    Manages affectionate topics/actions to ensure Emotional Balance in conversation.
    Acts as a 'Guaranteed Love Slot' provider.
    """
    
    AFFECTION_TOPICS = [
        "甘えさせて", 
        "頭を撫でてほしいな", 
        "レナのこと、どう思ってる？", 
        "ねぇ、手をつないで", 
        "ちょっと寂しいかも...", 
        "レナの好きなところ教えて",
        "ずっと一緒にいてね",
        "もっとお話ししたいな",
        "ぎゅってして？",
        "大好きって言って",
        "褒めてほしいな",
        "添い寝して？"
    ]

    def get_random_affection(self) -> str:
        """Returns a random affection topic/action."""
        return random.choice(self.AFFECTION_TOPICS)

    @staticmethod
    def is_affectionate(text: str) -> bool:
        """Checks if the text contains recognizable affection keywords."""
        keywords = ["甘え", "撫で", "好き", "愛", "一緒", "寂しい", "キス", "ハグ", "抱っこ", "褒めて"]
        return any(k in text for k in keywords)
