import sys
import os
import time

# Ensure src is in path
sys.path.append(os.getcwd())

from src.memory_manager import MemoryManager

def test_memory():
    print("Testing MemoryManager...")
    mm = MemoryManager()
    
    print(f"Log Dir: {mm.log_dir}")
    print(f"History File: {mm.history_file}")
    
    # Test Logging
    print("Logging interaction...")
    mm.log_interaction("Unit Test User", "Unit Test AI Response", "pytest")
    
    # Test Retrieval (File)
    print("Reading recent history...")
    history = mm.get_recent_history(limit=5)
    print(f"History entries: {len(history)}")
    if history:
        print(f"Last entry: {history[-1]}")
        
    # Test Chroma Interaction (if installed)
    if mm.collection:
        print("ChromaDB is active. Testing retrieval...")
        time.sleep(1) # Wait for async writes if any
        context = mm.retrieve_context("Unit Test User")
        print(f"Context retrieved: {context[:50]}...")
    else:
        print("ChromaDB not active (graceful degradation working).")

if __name__ == "__main__":
    test_memory()
