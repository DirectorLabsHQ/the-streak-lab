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
        # 1. Search for ID
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        s_res = requests.get(search_url, timeout=10).json()
        if 'items' not in s_res or not s_res['items']: return None
        p_id = s_res['items'][0]['id']
        
        # 2. Fetch Gamelog (v3 Common API - the 2026 standard)
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{p_id}/gamelog"
        data = requests.get(url, timeout=10).json()

        # 3. Dynamic Index Matching (Fixes the 0% Heat issue)
        labels = data.get('labels', [])
        def find_idx(names):
            for n in names:
                if n in labels: return labels.index(n)
            return None

        idx = {
            'pts': find_idx(['PTS']),
            'reb': find_idx(['REB']),
            'ast': find_idx(['AST']),
            'tpm': find_idx(['3PM', '3PT'])
        }

        # 4. Extract Entries (Flexible path finding)
        entries = data.get('entries', [])
        if not entries and 'season' in data:
            entries = data['season'].get('entries', [])
        
        if not entries:
            # Last ditch effort: check for nested season groups
            rs = data.get('regularSeason', {})
            for group in rs.get('groups', []):
                entries.extend(group.get('entries', []))

        if not entries: return None

        # Sort and Filter
        valid_games = [e for e in entries if e.get('stats')]
        valid_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_games = valid_games[:10]
        
        if not recent_games: return None

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for game in recent_games:
            s = game.get('stats', [])
            # Use our dynamic indices to check targets
            if idx['pts'] is not None and safe_float(s[idx['pts']]) >= TARGETS['pts']: hits['pts'] += 1
            if idx['reb'] is not None and safe_float(s[idx['reb']]) >= TARGETS['reb']: hits['reb'] += 1
            if idx['ast'] is not None and safe_float(s[idx['ast']]) >= TARGETS['ast']: hits['ast'] += 1
            if idx['tpm'] is not None and safe_float(s[idx['tpm']]) >= TARGETS['tpm']: hits['tpm'] += 1

        count = len(recent_games)
        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / count) * 100),
            "reb_heat": int((hits['reb'] / count) * 100),
            "ast_heat": int((hits['ast'] / count) * 100),
            "tpm_heat": int((hits['tpm'] / count) * 100),
            "last_game": recent_games[0].get('gameDate', '')[:10]
        }
    except Exception:
        return None

def main():
    player_data = []
    with open('nba-streaks/players.txt', 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    print(f"🏀 Syncing {len(lines)} players via v3 Engine...")
    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])
        stats = get_player_stats(name, team)
        if stats:
            player_data.append(stats)
            print(f"✅ {name}: {stats['pts_heat']}% PTS Heat")
        time.sleep(0.5)

    output = {"last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"), "players": player_data}
    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"🚀 DONE: {len(player_data)} players processed.")

if __name__ == "__main__":
    main()
