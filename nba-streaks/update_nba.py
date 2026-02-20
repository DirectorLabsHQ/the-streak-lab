import requests
import json
from datetime import datetime
import time

# Benchmarks for your Heat Index
TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

# Updated Roster (Hardcoded for maximum reliability)
PLAYER_LIST = [
    "Stephen Curry GSW", "Luka Doncic DAL", "LeBron James LAL", 
    "Kevin Durant PHX", "Victor Wembanyama SAS"
]

def get_player_stats(player_name, team_code):
    try:
        # STEP 1: Capture Athlete ID
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name}&limit=1&type=player"
        res = requests.get(search_url, timeout=10).json()
        
        if 'items' not in res or not res['items']:
            return None
        player_id = res['items'][0]['id']

        # STEP 2: Capture Gamelog JSON
        log_url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        logs = requests.get(log_url, timeout=10).json()
        
        events = logs.get('events', [])[:10]
        if not events:
            return None

        # STEP 3: The Fix (Access by key, not by slice index)
        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for event in events:
            # We must look for the "stats" dictionary inside each game event
            s = event.get('stats', {})
            
            # Use .get() to avoid errors if a stat is missing for a game
            if float(s.get('points', 0)) >= TARGETS['pts']: hits['pts'] += 1
            if float(s.get('rebounds', 0)) >= TARGETS['reb']: hits['reb'] += 1
            if float(s.get('assists', 0)) >= TARGETS['ast']: hits['ast'] += 1
            if float(s.get('threePointFieldGoalsMade', 0)) >= TARGETS['tpm']: hits['tpm'] += 1

        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(events)) * 100),
            "reb_heat": int((hits['reb'] / len(events)) * 100),
            "ast_heat": int((hits['ast'] / len(events)) * 100),
            "tpm_heat": int((hits['tpm'] / len(events)) * 100),
            "last_game": f"{events[0]['gameDate'][:10]}"
        }
    except Exception as e:
        print(f"⚠️ Error during capture for {player_name}: {e}")
        return None

def main():
    player_data = []
    print(f"🏀 Starting sync for {len(PLAYER_LIST)} players...")

    for entry in PLAYER_LIST:
        parts = entry.split()
        team = parts[-1]
        name = " ".join(parts[:-1])
        
        stats = get_player_stats(name, team)
        if stats:
            player_data.append(stats)
            print(f"✅ {name} synced.")
        
        time.sleep(0.5) # Increased delay to prevent ESPN rate-limiting

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"🚀 SUCCESS: {len(player_data)} players processed.")

if __name__ == "__main__":
    main()
