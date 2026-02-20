import requests
import json
from datetime import datetime
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def safe_float(val):
    try:
        return float(str(val).strip()) if val else 0.0
    except:
        return 0.0

def find_label(labels, possible_names):
    if not isinstance(labels, list): return None
    for name in possible_names:
        if name in labels:
            return labels.index(name)
    return None

def get_player_stats(player_name, team_code):
    try:
        # STEP 1: Search
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=5&type=player"
        search_res = requests.get(search_url, timeout=10).json()
        
        player_id = None
        for item in search_res.get('items', []):
            if item.get('type') == 'player':
                player_id = item.get('id')
                break
        
        if not player_id: return None

        # STEP 2: Gamelog
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        res = requests.get(url, timeout=10).json()

        labels = res.get('labels')
        events = res.get('events')

        # TYPE SAFETY CHECK: Ensure these are lists, not dictionaries or None
        if not isinstance(labels, list) or not isinstance(events, list):
            print(f"⚠️ Invalid data format for {player_name}")
            return None

        # STEP 3: Map and Calculate
        idx = {
            'pts': find_label(labels, ['PTS']),
            'reb': find_label(labels, ['REB']),
            'ast': find_label(labels, ['AST']),
            'tpm': find_label(labels, ['3PM', '3PT'])
        }

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        recent_games = events[:10] 

        for game in recent_games:
            # Another safety check for the individual game stats
            stats = game.get('stats', [])
            if not isinstance(stats, list): continue
            
            if idx['pts'] is not None and len(stats) > idx['pts']:
                if safe_float(stats[idx['pts']]) >= TARGETS['pts']: hits['pts'] += 1
            if idx['reb'] is not None and len(stats) > idx['reb']:
                if safe_float(stats[idx['reb']]) >= TARGETS['reb']: hits['reb'] += 1
            if idx['ast'] is not None and len(stats) > idx['ast']:
                if safe_float(stats[idx['ast']]) >= TARGETS['ast']: hits['ast'] += 1
            if idx['tpm'] is not None and len(stats) > idx['tpm']:
                if safe_float(stats[idx['tpm']]) >= TARGETS['tpm']: hits['tpm'] += 1

        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(recent_games)) * 100) if recent_games else 0,
            "reb_heat": int((hits['reb'] / len(recent_games)) * 100) if recent_games else 0,
            "ast_heat": int((hits['ast'] / len(recent_games)) * 100) if recent_games else 0,
            "tpm_heat": int((hits['tpm'] / len(recent_games)) * 100) if recent_games else 0,
            "last_game": recent_games[0].get('gameDate', '')[:10] if recent_games else "N/A"
        }
    except Exception as e:
        print(f"❌ Error with {player_name}: {e}")
        return None

def main():
    player_data = []
    with open('nba-streaks/players.txt', 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    print(f"🏀 Syncing {len(lines)} players...")
    for line in lines:
        parts = line.split()
        team_code = parts[-1]
        player_name = " ".join(parts[:-1])
        stats = get_player_stats(player_name, team_code)
        if stats:
            player_data.append(stats)
            print(f"✅ {player_name}")
        time.sleep(0.7)

    output = {"last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"), "players": player_data}
    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"🚀 DONE: {len(player_data)} players saved.")

if __name__ == "__main__":
    main()
