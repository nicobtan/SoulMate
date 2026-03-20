
import json
import re
import sys
from datetime import datetime
from collections import defaultdict
import os

INPUT_FILE = "logs/mind_vault.jsonl"
OUTPUT_FILE = "logs/mind_vault_clean.jsonl"

def normalize_text(text):
    """Normalize text for comparison (remove whitespace, lowercase)."""
    if not text:
        return ""
    text = re.sub(r'\s+', '', text)
    return text.lower()

def estimate_category(text):
    """Simple keyword matching for tagging."""
    text_lower = text.lower()
    if any(k in text_lower for k in ["philosoph", "生きる", "存在", "魂", "意識"]):
        return "Philosophy"
    if any(k in text_lower for k in ["d&d", "dungeon", "dragon", "game", "rpg", "trpg"]):
        return "Idea (Game)"
    if any(k in text_lower for k in ["python", "code", "ai", "gemini", "api", "tech"]):
        return "Technology"
    return "General"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        sys.exit(1)

    print(f"Reading from {INPUT_FILE}...")
    
    entries = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON: {line[:50]}...")

    print(f"Total entries loaded: {len(entries)}")

    # Deduplication Logic
    # Map normalized_text -> best_entry
    unique_map = {}
    
    # Process mostly chronologically, but we want to key by text
    for entry in entries:
        text = entry.get('source_text', '')
        if not text: 
            # Fallback to category/analysis if source_text is missing?
            # Or just use raw JSON match?
            # For now, if no source_text, use analysis as key
            text = entry.get('analysis', {}).get('summary', str(entry))
            
        norm_key = normalize_text(text)
        
        if norm_key not in unique_map:
            unique_map[norm_key] = entry
        else:
            existing = unique_map[norm_key]
            
            # Compare timestamps
            # Format usually: "2026-01-11 04:00:00" or ISO
            ts_new = entry.get('timestamp', '')
            ts_old = existing.get('timestamp', '')
            
            # Simple string comparison works for ISO-like dates (YYYY-MM-DD...)
            is_newer = ts_new > ts_old
            
            base = entry if is_newer else existing
            other = existing if is_newer else entry
            
            # Merge Metadata (keep base, fill missing from other)
            # 1. Analysis
            if not base.get('analysis') and other.get('analysis'):
                base['analysis'] = other['analysis']
                
            # 2. Tags/Category
            if not base.get('category') and other.get('category'):
                base['category'] = other['category']
                
            unique_map[norm_key] = base

    cleaned_entries = list(unique_map.values())
    
    # Optional Tagging
    for entry in cleaned_entries:
        if 'category' not in entry or not entry['category']:
            entry['category'] = estimate_category(entry.get('source_text', ''))
            
    # Sort by Timestamp Descending
    cleaned_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    print(f"Unique entries: {len(cleaned_entries)}")
    print(f"Removed duplicates: {len(entries) - len(cleaned_entries)}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for entry in cleaned_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
