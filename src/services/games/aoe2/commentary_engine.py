
import json
try:
    from .db_manager import AoE2DatabaseManager
except ImportError:
    from db_manager import AoE2DatabaseManager

class AoE2CommentaryEngine:
    def __init__(self, db_manager: AoE2DatabaseManager):
        self.db = db_manager
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        """Loads configuration from DB."""
        # Default to 45s as per user request for "Active" commentary
        self.settings['vision_interval'] = int(self.db.get_config('vision_interval_sec', 45))
        self.settings['target_player'] = self.db.get_config('target_player_name', 'Player')
        self.settings['proactive_mode'] = self.db.get_config('proactive_mode', 'true').lower() == 'true'

    def analyze_situation(self, vision_result_json):
        """
        Analyzes vision data and returns a context dict for AI Prompt.
        """
        # Parsing Vision JSON (Assuming structure from Vision Service)
        # { "players": [{"name": "NicoBtan", "civ": "Franks", "score": 1200, "units": ["Knight"]}], "time": "20:00" }
        
        try:
            data = vision_result_json if isinstance(vision_result_json, dict) else json.loads(vision_result_json)
        except:
            return {"error": "Invalid JSON input"}

        target_name = self.settings['target_player']
        
        # 1. Identify User & Enemy
        user_status = None
        enemies = []
        
        players = data.get("players", [])
        for p in players:
            p_name = p.get("name", "Unknown")
            # Simple match (In real world, OCR might be fuzzy)
            if target_name in p_name:
                user_status = p
            else:
                enemies.append(p)
        
        if not user_status:
            return {"status": "User not found", "target": target_name}

        # 2. Tactical Analysis (Counter Logic)
        advice_list = []
        
        # Use a set to avoid advising same thing multiple times
        seen_advice = set()

        for enemy in enemies:
            enemy_name = enemy.get("name", "Enemy")
            enemy_civ = enemy.get("civ", "Unknown")
            enemy_units = enemy.get("units", []) # List of unit names seen
            
            for e_unit_name in enemy_units:
                # Resolve unit ID
                unit_data = self.db.get_unit_by_name(e_unit_name)
                
                if unit_data:
                    # Find Counters
                    counters = self.db.find_best_counters(unit_data['id'], limit=2)
                    
                    if counters:
                        best_counter = counters[0]['unit']
                        advice = f"{best_counter}"
                        
                        if advice not in seen_advice:
                            advice_list.append({
                                "enemy": enemy_name,
                                "threat": e_unit_name,
                                "counter": best_counter
                            })
                            seen_advice.add(advice)
                else:
                    pass # Unknown unit name

        return {
            "user": user_status,
            "enemies": enemies,
            "tactical_alerts": advice_list,
            "time": data.get("time", "Unknown")
        }

    def generate_commentary_prompt(self, analysis_result):
        """
        Generates the System Prompt for Gemini based on analysis.
        """
        if "error" in analysis_result:
            return None
            
        user = analysis_result.get("user", {})
        alerts = analysis_result.get("tactical_alerts", [])
        time_str = analysis_result.get("time", "Unknown")
        
        prompt = f"""
[AoE2 Proactive Commentary Mode]
Role: You are an expert AoE2 coach and partner.
Current Situation: 
- User ({user.get('name')}) is playing as {user.get('civ')}.
- Score: {user.get('score')}
- Time: {time_str}

[Tactical Intel]
"""
        if not alerts:
            prompt += "No immediate threats/counters found.\n"
        else:
            for alert in alerts:
                prompt += f"- Enemy ({alert['enemy']}) has {alert['threat']}. -> Suggest making {alert['counter']}.\n"

        prompt += """
[Instruction]
Based on the info, act as a supportive partner.
1. Be brief (1-2 sentences).
2. If tactical intel exists, advice on using the counter unit.
3. If no threats, cheer for the economy or score.
4. Output specific Japanese text only. No JSON.
"""
        return prompt

# Test Execution Helper
if __name__ == "__main__":
    # Mock DB
    mgr = AoE2DatabaseManager()
    engine = AoE2CommentaryEngine(mgr)
    
    # Mock Vision Data
    mock_vision = {
        "time": "25:00",
        "players": [
            {"name": "NicoBtan", "civ": "Britons", "score": 3500, "units": ["Archer"]},
            {"name": "Viper", "civ": "Franks", "score": 3800, "units": ["Knight", "Paladin"]}
        ]
    }
    
    # Test
    print("--- Loaded Settings ---")
    print(engine.settings)
    
    print("\n--- Analyzing Situation ---")
    # Set target to match mock
    engine.settings['target_player'] = "NicoBtan" 
    
    result = engine.analyze_situation(mock_vision)
    print("Analysis:", json.dumps(result, indent=2))
    
    print("\n--- Generated Prompt ---")
    prompt = engine.generate_commentary_prompt(result)
    print(prompt)
