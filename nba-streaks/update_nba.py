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
        # STEP 1: Better Search (v2)
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        res = requests.get(search_url, timeout=10).json()
        if 'items' not in res or not res['items']: return None
        p_id = res['items'][0]['id']

        # STEP 2: The "Site" Gamelog (v2 is more stable for L10)
        # This endpoint is designed for the web dashboard and is almost never 'nested'
        url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/athletes/{p_id}/gamelog"
        data = requests.get(url, timeout=10).json()

        # In v2, the path is: entries -> stats
        # We look for the most recent regular season entries
        season_data = data.get('season', {})
        entries = season_data.get('entries', [])
        
        if not entries:
            print(f"⚠️ No games in v2 log for {player_name}")
            return None

        # Stats in v2 are often pre-labeled in a list
        # Standard Index: 3=PTS, 10=REB, 11=AST, 14=3PM
        recent_games = entries[:10]
        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}

        for game in recent_games:
            s = game.get('stats', [])
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
    with open('nba-streaks/players.txt', 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    print(f"🏀 Syncing {len(lines)} athletes via v2 Engine...")
    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])
        stats = get_player_stats(name, team)
        if stats:
            player_data.append(stats)
            print(f"✅ {name}")
        time.sleep(0.6)

    output = {"last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"), "players": player_data}
    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"🚀 SUCCESS: {len(player_data)} players processed.")

if __name__ == "__main__":
    main()
