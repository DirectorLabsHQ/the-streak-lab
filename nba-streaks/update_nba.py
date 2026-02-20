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

def get_player_stats(player_name, team_code):
    try:
        # 1. Search for Player ID
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        res = requests.get(search_url, timeout=10).json()
        if 'items' not in res or not res['items']: return None
        p_id = res['items'][0]['id']
        
        # 2. Fetch Gamelog (v2 Site API)
        url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/athletes/{p_id}/gamelog"
        data = requests.get(url, timeout=10).json()

        # 3. 2026 Path Extraction
        entries = []
        # ESPN 2026 Structure: regularSeason -> groups -> entries
        if 'regularSeason' in data:
            groups = data['regularSeason'].get('groups', [])
            for group in groups:
                group_entries = group.get('entries', [])
                if group_entries:
                    entries.extend(group_entries)
        
        # Fallback if regularSeason is empty
        if not entries:
            entries = data.get('season', {}).get('entries', [])

        if not entries:
            return None

        # Sort by date and take last 10
        entries.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_games = entries[:10]
        
        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for game in recent_games:
            s = game.get('stats', [])
            # Index Map for v2: 3=PTS, 10=REB, 11=AST, 14=3PM
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
    except Exception as e:
        print(f"❌ Error with {player_name}: {e}")
        return None

def main():
    player_data = []
    try:
        with open('nba-streaks/players.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except:
        print("❌ Could not find players.txt")
        return

    print(f"🏀 Syncing {len(lines)} athletes...")
    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])
        stats = get_player_stats(name, team)
        if stats:
            player_data.append(stats)
            print(f"✅ {name} synced.")
        time.sleep(0.7)

    # Save results
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    
    print(f"🚀 SUCCESS: {len(player_data)} players processed.")

if __name__ == "__main__":
    main()
