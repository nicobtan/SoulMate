
import requests
from bs4 import BeautifulSoup
import re
import datetime
import time
from .db_manager import AoE2DatabaseManager

class RivalScout:
    def __init__(self, db_manager: AoE2DatabaseManager):
        self.db = db_manager
        self.base_url = "https://www.aoe2insights.com"
        # Japanese character range (Hiragana, Katakana, Kanji)
        self.jp_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]')

    def ensure_tables(self):
        """Creates/Updates DB schema for Rivals."""
        print("--- Ensuring DB Schema for Rivals ---")
        with self.db._get_conn() as conn:
            # 1. Rivals Table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rivals (
                    name TEXT PRIMARY KEY,
                    insights_id TEXT,
                    first_met DATETIME,
                    last_met DATETIME,
                    total_matches INTEGER DEFAULT 0,
                    memo TEXT
                )
            ''')
            
            # 2. Match Logs Update (Add columns if missing)
            # SQLite doesn't support IF NOT EXISTS for columns, need check
            try:
                conn.execute("ALTER TABLE match_logs ADD COLUMN external_match_id TEXT")
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_match_logs_external_id ON match_logs(external_match_id)")
                conn.execute("ALTER TABLE match_logs ADD COLUMN lobby_name TEXT")
                conn.execute("ALTER TABLE match_logs ADD COLUMN enemy_name TEXT")
            except Exception as e:
                pass # Already exists or partial failure (safe to ignore if columns exist) 
                
            conn.commit()

    def parse_date(self, date_str):
        """Parses AoE2Insights date string: 'Jan. 15, 2026, 3:03 p.m.'"""
        try:
            # Clean up: "p.m." -> "PM", "a.m." -> "AM" for strptime
            clean_str = date_str.replace("p.m.", "PM").replace("a.m.", "AM").replace(".", "") 
            # "Jan 15, 2026, 3:03 PM" (Periods removed after Jan) - wait, Jan. might lose dot.
            # actually replace only p.m./a.m. 
            # Pattern: %b. %d, %Y, %I:%M %p. (Note the dot after %b might be variable or handled)
            # Safe way: use dateparser lib or manual mapping.
            # Let's try strptime with manual adjustment.
            
            # Remove dots from month abbr if present? "Jan." -> "Jan"
            # Standardizing: "Jan. 15, 2026, 3:03 PM"
            # Remove "p.m." -> "PM"
            s = date_str.replace("p.m.", "PM").replace("a.m.", "AM")
            # "Jan. 15, 2026, 3:03 PM"
            
            return datetime.datetime.strptime(s, "%b. %d, %Y, %I:%M %p")
        except:
            try:
                # Fallback / retry without dot in month? 
                s = date_str.replace("p.m.", "PM").replace("a.m.", "AM")
                return datetime.datetime.strptime(s, "%b %d, %Y, %I:%M %p")
            except:
                return datetime.datetime.now() # Fallback

    def fetch_matches(self, user_id, target_year=None):
        """Scrapes match history. If target_year is set (e.g. 2025), fetches untill that year is covered."""
        all_matches = []
        page = 1
        
        print(f"Scouting matches for {user_id} (Target Year: {target_year or 'Latest Only'})...")
        
        while True:
            url = f"{self.base_url}/user/{user_id}/matches/?page={page}"
            print(f"Fetching Page {page}: {url}")
            
            try:
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
            except Exception as e:
                print(f"Fetch failed: {e}")
                break

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find all match tiles
            tiles = soup.find_all('div', class_='match-tile')
            if not tiles:
                print("No matches found on this page. Stopping.")
                break
            
            print(f"  - Found {len(tiles)} tiles.")
            page_has_valid_matches = False
            stop_scouting = False
            
            for tile in tiles:
                try:
                    # 1. Lobby & ID
                    link_tag = tile.select_one('.col-md-3 a.stretched-link')
                    if not link_tag: continue
                    
                    lobby_name = link_tag.get_text(strip=True)
                    match_id = link_tag['href'].split('/')[-2]
                    
                    # 2. Date
                    date_div = tile.select_one('.col-md-3 .mt-2 div:nth-child(2) span')
                    if date_div and 'title' in date_div.attrs:
                        dt = self.parse_date(date_div['title'])
                        date_str = str(dt)
                        
                        # Check Year Limit
                        if target_year:
                             # If we reached a year BEFORE target (e.g. 2024), we can stop entirely?
                             # Matches are ordered newest first.
                             # If dt.year < target_year => We went too far. Stop.
                             if dt.year < target_year:
                                 stop_scouting = True
                                 # print(f"    - Reached {dt.year}, stopping.")
                                 # We continue formatting this tile? No, skip past data.
                                 continue 
                    else:
                        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                    
                    # === Filter: Custom Games Only ===
                    badges = tile.select('.badge')
                    is_custom = False
                    for b in badges:
                        if "Custom" in b.get_text(strip=True):
                            is_custom = True
                            break
                    
                    if not is_custom:
                        continue 
                        
                    page_has_valid_matches = True
                    
                    # 3. Teams & Players
                    teams = tile.select('.teams ul.team')
                    my_team_idx = -1
                    team_data = [] 
                    
                    for t_idx, team_ul in enumerate(teams):
                        players = []
                        is_winner = 'won' in team_ul.get('class', [])
                        
                        for li in team_ul.find_all('li'):
                            player_div = li.select_one('.team-player')
                            if not player_div: continue
                            
                            a_tag = player_div.select_one('a')
                            if not a_tag: continue
                            
                            p_name = a_tag.get_text(strip=True)
                            p_id = a_tag['href'].split('/')[-2]
                            
                            civ_icon = player_div.select_one('i.image-icon')
                            civ_name = civ_icon['title'] if civ_icon and 'title' in civ_icon.attrs else "Unknown"
                            
                            players.append({"name": p_name, "id": p_id, "civ": civ_name})
                            
                            if str(p_id) == str(user_id):
                                my_team_idx = t_idx
                        
                        team_data.append({"players": players, "won": is_winner})
                    
                    if my_team_idx == -1: continue
                        
                    my_team = team_data[my_team_idx]
                    my_info = next(p for p in my_team['players'] if str(p['id']) == str(user_id))
                    result = "Win" if my_team['won'] else "Loss"
                    
                    enemies = []
                    for idx, t in enumerate(team_data):
                        if idx != my_team_idx:
                            enemies.extend(t['players'])
                            
                    enemy_names_str = ", ".join([e['name'] for e in enemies])
                    enemy_civs_str = ", ".join([e['civ'] for e in enemies])
                    
                    map_img = tile.select_one('.col-md-3 picture img')
                    map_name = "Unknown"
                    if map_img:
                        src = map_img.get('src', '')
                        map_name = src.split('/')[-1].split('.')[0].capitalize()

                    match_data = {
                        "id": match_id,
                        "lobby": lobby_name,
                        "date": date_str,
                        "enemy_name": enemy_names_str, 
                        "enemy_list": enemies,        
                        "result": result,
                        "map": map_name,
                        "my_civ": my_info['civ'],
                        "enemy_civ": enemy_civs_str
                    }
                    all_matches.append(match_data)
                    
                except Exception as e:
                    print(f"Tile error: {e}")
                    continue

            if stop_scouting:
                print("Reached matches older than target year. Stopping.")
                break
                
            page += 1
            if not target_year and page > 1: # Default behavior: just 1 page
                break
                
            if page > 50: # Safety cap
                print("Page limit (50) reached.")
                break
                
            time.sleep(1) # Be polite

        return all_matches


    def sync_db(self, matches):
        """Updates DB with match data."""
        print(f"Syncing {len(matches)} matches to DB...")
        new_count = 0
        updated_rivals = set()
        
        with self.db._get_conn() as conn:
            for m in matches:
                try:
                    # 1. Insert Match Log
                    # Check existence
                    cursor = conn.execute("SELECT 1 FROM match_logs WHERE external_match_id = ?", (m['id'],))
                    if cursor.fetchone():
                        continue # Skip existing
                        
                    conn.execute('''
                        INSERT INTO match_logs (
                            timestamp, my_civ, enemy_civ, enemy_name, map_name, result, external_match_id, lobby_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        m['date'], m['my_civ'], m['enemy_civ'], m['enemy_name'], 
                        m['map'], m['result'], m['id'], m['lobby']
                    ))
                    new_count += 1
                    
                    # 2. Update Rivals (Iterate ALL enemies in the match)
                    for enemy in m.get('enemy_list', []):
                         curr_name = enemy['name']
                         curr_id = enemy['id']
                         
                         conn.execute('''
                            INSERT OR IGNORE INTO rivals (name, insights_id, first_met, last_met, total_matches, memo)
                            VALUES (?, ?, ?, ?, 0, "")
                        ''', (curr_name, curr_id, datetime.datetime.now(), datetime.datetime.now()))
                        
                         # Update stats
                         conn.execute('''
                            UPDATE rivals 
                            SET last_met = ?, 
                                total_matches = total_matches + 1
                            WHERE name = ?
                        ''', (datetime.datetime.now(), curr_name))
                        
                         updated_rivals.add(curr_name)
                        
                except Exception as e:
                    print(f"Sync error for match {m['id']}: {e}")
            
            conn.commit()
            
        print(f"Done. Added {new_count} new matches.")
        print(f"Updated rivals: {list(updated_rivals)}")

