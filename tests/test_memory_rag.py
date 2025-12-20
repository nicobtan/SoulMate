import os
import sys

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.memory_manager import MemoryManager

def test_memory():
    print("Initializing MemoryManager...")
    mm = MemoryManager()
    
    # 1. Log some interactions
    print("Logging interactions...")
    mm.log_interaction("私の好きな食べ物はカレーです。", "カレーですね、覚えておきます。", "default")
    mm.log_interaction("その次はラーメンが好き。", "麺類もお好きなんですね。", "default")
    mm.log_interaction("昨日はテニスをしました。", "運動は体に良いですね。", "default")
    
    # Allow some time for vector indexing if async (Chroma is usually sync locally)
    import time
    time.sleep(1)
    
    # 2. Retrieve
    query = "私が好きな食べ物は何？"
    print(f"\nQuery: {query}")
    context = mm.retrieve_context(query)
    print(f"Result:\n{context}")
    
    query2 = "最近どんな運動をした？"
    print(f"\nQuery: {query2}")
    context2 = mm.retrieve_context(query2)
    print(f"Result:\n{context2}")

if __name__ == "__main__":
    test_memory()
