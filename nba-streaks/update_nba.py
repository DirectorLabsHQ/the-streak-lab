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

def find_entries_recursive(data):
    """Deep searches the JSON for any list of game entries."""
    if isinstance(data, list):
        # If it's a list and the first item looks like a game, we found it!
        if len(data) > 0 and isinstance(data[0], dict) and 'stats' in data[0]:
            return data
        # Otherwise, check items in the list
        for item in data:
            found = find_entries_recursive(item)
            if found: return found
    elif isinstance(data, dict):
        for key, value in data.items():
            found = find_entries_recursive(value)
            if found: return found
    return None

def get_player_stats(player_name, team_code):
    try:
        # 1. Search for Player ID
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        res = requests.get(search_url, timeout=10).json()
        if 'items' not in res or not res['items']: return None
        p_id = res['items'][0]['id']
        
        # 2. Fetch Gamelog (v3 is preferred in 2026)
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{p_id}/gamelog"
        data = requests.get(url, timeout=10).json()

        # 3. Recursive Path Finding
        entries = find_entries_recursive(data)

        if not entries:
            # Fallback to the Site v2 API if v3 fails
            v2_url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/athletes/{p_id}/gamelog"
            v2_data = requests.get(v2_url, timeout=10).json()
            entries = find_entries_recursive(v2_data)

        if not entries: return None

        # 4. Filter and Sort
        valid_games = [e for e in entries if e.get('stats') and len(e.get('stats')) > 10]
        valid_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_games = valid_games[:10]
        
        if not recent_games: return None

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for game in recent_games:
            s = game.get('stats', [])
            # In v3/v2 Gamelog, the standard indices are:
            # PTS: 3, REB: 10, AST: 11, 3PM: 14
            if len(s) > 14:
                if safe_float(s[3]) >= TARGETS['pts']: hits['pts'] += 1
                if safe_float(s[10]) >= TARGETS['reb']: hits['reb'] += 1
                if safe_float(s[11]) >= TARGETS['ast']: hits['ast'] += 1
                if safe_float(s[14]) >= TARGETS['tpm']: hits['tpm'] += 1

        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(recent_games)) * 100),
            "reb_heat": int((hits['reb'] / len(recent_games)) * 100),
            "ast_heat": int((hits['ast'] / len(recent_games)) * 100),
            "tpm_heat": int((hits['tpm'] / len(recent_games)) * 100),
            "last_game": recent_games[0].get('gameDate', '')[:10]
        }
    except Exception:
        return None

def main():
    player_data = []
    with open('nba-streaks/players.txt', 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    print(f"🏀 Syncing {len(lines)} athletes for The Streak Lab...")
    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])
        stats = get_player_stats(name, team)
        if stats:
            player_data.append(stats)
            print(f"✅ {name}")
        time.sleep(0.5)

    output = {"last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"), "players": player_data}
    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"🚀 SUCCESS: {len(player_data)} players processed.")

if __name__ == "__main__":
    main()
