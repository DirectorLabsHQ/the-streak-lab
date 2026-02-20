import requests
import json
from datetime import datetime
import time

# Betting Benchmarks for the "Heat Index"
TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def safe_float(val):
    try:
        # ESPN stats often come as strings, sometimes with empty spaces
        return float(str(val).strip()) if val else 0.0
    except:
        return 0.0

def get_player_stats(player_name, team_code):
    try:
        # STEP 1: Search for Player ID
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        search_res = requests.get(search_url, timeout=10).json()
        
        if 'items' not in search_res or not search_res['items']:
            return None
        player_id = search_res['items'][0]['id']

        # STEP 2: Capture Gamelog JSON
        log_url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        log_res = requests.get(log_url, timeout=10).json()
        
        labels = log_res.get('labels', [])
        events = log_res.get('events', [])
        
        if not labels or not events:
            return None

        # STEP 3: Map Stat Columns Dynamically (Bulletproof Indexing)
        idx = {
            'pts': labels.index('PTS') if 'PTS' in labels else None,
            'reb': labels.index('REB') if 'REB' in labels else None,
            'ast': labels.index('AST') if 'AST' in labels else None,
            'tpm': labels.index('3PM') if '3PM' in labels else None
        }

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        games_to_check = events[:10] # Last 10 games

        for game in games_to_check:
            stats = game.get('stats', [])
            # Check each stat against targets using our dynamic map
            if idx['pts'] is not None and safe_float(stats[idx['pts']]) >= TARGETS['pts']: hits['pts'] += 1
            if idx['reb'] is not None and safe_float(stats[idx['reb']]) >= TARGETS['reb']: hits['reb'] += 1
            if idx['ast'] is not None and safe_float(stats[idx['ast']]) >= TARGETS['ast']: hits['ast'] += 1
            if idx['tpm'] is not None and safe_float(stats[idx['tpm']]) >= TARGETS['tpm']: hits['tpm'] += 1

        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(games_to_check)) * 100),
            "reb_heat": int((hits['reb'] / len(games_to_check)) * 100),
            "ast_heat": int((hits['ast'] / len(games_to_check)) * 100),
            "tpm_heat": int((hits['tpm'] / len(games_to_check)) * 100),
            "last_game": games_to_check[0].get('gameDate', '')[:10]
        }
    except Exception as e:
        print(f"⚠️ Skipping {player_name}: {e}")
        return None

def main():
    player_data = []
    print("🏀 Starting Streak Lab Sync...")

    # Load your updated players.txt
    try:
        with open('nba-streaks/players.txt', 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print("❌ Error: nba-streaks/players.txt not found.")
        return

    for line in lines:
        parts = line.split()
        team_code = parts[-1]
        name = " ".join(parts[:-1])
        
        stats = get_player_stats(name, team_code)
        if stats:
            player_data.append(stats)
            print(f"✅ {name} ({team_code})")
        
        time.sleep(0.65) # Safety buffer for 100+ players

    # Save to your site's data file
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    
    print(f"🚀 SUCCESS: {len(player_data)} players processed for the dashboard.")

if __name__ == "__main__":
    main()
