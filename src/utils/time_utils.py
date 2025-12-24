import datetime

def get_time_context():
    """
    Returns time-based instructions for the AI.
    Rules:
    - 05:00 - 02:00 (Next Day): ACTIVE (No sleep warnings)
    - 02:00 - 05:00: LATE_NIGHT (Gentle sleep suggestion allowed)
    """
    now = datetime.datetime.now()
    hour = now.hour
    
    # 02:00 <= hour < 05:00 is Late Night
    if 2 <= hour < 5:
        return {
            "status": "LATE_NIGHT",
            "instruction": "[Time Context: Late Night (02:00-05:00)]\nIt is very late. You may GENTLY suggest sleep ONCE if the user seems tired. Do NOT be persistent. Be soft and caring."
        }
    else:
        # All other times (05:00 - 24:00, 00:00 - 02:00)
        return {
            "status": "ACTIVE",
            "instruction": "[Time Context: Active Time]\nIt is active time (until 02:00 AM). Do NOT warn about sleep. Support the user's work or play enthusiastically."
        }
