import requests
import json
from datetime import datetime
import time
import os

# Benchmarks from your UI
TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def get_player_stats(player_name, team_code):
    try:
        # Search for the player on ESPN to get their ID
        search_url = f"https://site.web.api.espn.com/apis/search/v2?query={player_name}&limit=1"
        res = requests.get(search_url).json()
        if not res.get('results'): return None
        player_id = res['results'][0]['id']

        # Get their Last 10 Game Logs
        log_url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        logs = requests.get(log_url).json()
        
        events = logs.get('events', [])[:10]
        if not events: return None

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for event in events:
            stats = event['stats']
            # ESPN Index mapping: Pts(3), Reb(10), Ast(11), 3PM(14)
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
    
    # NEW: Reading directly from your uploaded players.txt
    try:
        with open('nba-streaks/players.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        # Fallback if path is different in your repo
        with open('players.txt', 'r') as f:
            lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Splits "Stephen Curry GSW" into "Stephen Curry" and "GSW"
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])
        
        stats = get_player_stats(name, team)
        if stats:
            player_data.append(stats)
            print(f"Synced: {name}")
        
        # Small delay to keep the connection stable
        time.sleep(0.1)

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"Total Players Synced: {len(player_data)}")

if __name__ == "__main__":
    main()
