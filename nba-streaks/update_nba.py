import requests
import json
from datetime import datetime
import time

# Benchmarks for Heat Index
TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

# YOUR HARDCODED PLAYER LIST (Extracted from players.txt)
PLAYER_LIST = [
    "Stephen Curry GSW", 
    "Luka Doncic DAL", 
    "LeBron James LAL", 
    "Kevin Durant PHX", 
    "Victor Wembanyama SAS"
]

def get_player_stats(player_name, team_code):
    try:
        # Step 1: Search for Player ID
        search_url = f"https://site.web.api.espn.com/apis/search/v2?query={player_name}&limit=1"
        res = requests.get(search_url, timeout=10).json()
        if not res.get('results'): return None
        player_id = res['results'][0]['id']

        # Step 2: Get L10 Game Logs
        log_url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        logs = requests.get(log_url, timeout=10).json()
        events = logs.get('events', [])[:10]
        if not events: return None

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for event in events:
            stats = event['stats']
            if float(stats[3]) >= TARGETS['pts']: hits['pts'] += 1
            if float(stats[10]) >= TARGETS['reb']: hits['reb'] += 1
            if float(stats[11]) >= TARGETS['ast']: hits['ast'] += 1
            if float(stats[14]) >= TARGETS['tpm']: hits['tpm'] += 1

        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(events)) * 100),
            "reb_heat": int((hits['reb'] / len(events)) * 100),
            "ast_heat": int((hits['ast'] / len(events)) * 100),
            "tpm_heat": int((hits['tpm'] / len(events)) * 100),
            "last_game": f"{events[0]['gameDate'][:10]}"
        }
    except:
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
        
        time.sleep(0.2) # Prevent ESPN rate limiting

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    # Saves to the same folder for your GitHub Action
    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"🚀 SUCCESS: {len(player_data)} players processed.")

if __name__ == "__main__":
    main()
