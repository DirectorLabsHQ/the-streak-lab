import requests
import json
from datetime import datetime
import time

# Targets for "Heat Index" (Last 10 Games)
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
        
        # 2. Fetch Gamelog (v3 Engine)
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{p_id}/gamelog"
        data = requests.get(url, timeout=10).json()

        # 3. 2026 Extraction Logic
        entries = []
        # ESPN 2026 structure: data -> regularSeason -> groups -> entries
        if 'regularSeason' in data:
            groups = data['regularSeason'].get('groups', [])
            for group in groups:
                entries.extend(group.get('entries', []))
        
        # Fallback for older formats or different season phases
        if not entries:
            entries = data.get('entries', []) or data.get('season', {}).get('entries', [])

        if not entries:
            return None

        # 4. Map Stat Labels to Indices
        labels = data.get('labels', [])
        def get_idx(key):
            return labels.index(key) if key in labels else None

        p_idx = get_idx('PTS')
        r_idx = get_idx('REB')
        a_idx = get_idx('AST')
        m_idx = get_idx('3PM') or get_idx('3PT')

        # Filter valid games and sort by date
        valid_games = [e for e in entries if e.get('stats')]
        valid_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_games = valid_games[:10]
        
        if not recent_games: return None

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for game in recent_games:
            s = game.get('stats', [])
            if p_idx is not None and safe_float(s[p_idx]) >= TARGETS['pts']: hits['pts'] += 1
            if r_idx is not None and safe_float(s[r_idx]) >= TARGETS['reb']: hits['reb'] += 1
            if a_idx is not None and safe_float(s[a_idx]) >= TARGETS['ast']: hits['ast'] += 1
            if m_idx is not None and safe_float(s[m_idx]) >= TARGETS['tpm']: hits['tpm'] += 1

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
    try:
        with open('nba-streaks/players.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except:
        print("❌ Could not find players.txt")
        return

    print(f"🏀 Syncing {len(lines)} athletes for The Streak Lab...")
    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])
        stats = get_player_stats(name, team)
        if stats:
            player_data.append(stats)
            print(f"✅ {name}")
        else:
            print(f"⚠️ Skipping {name}")
        time.sleep(0.5)

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    
    print(f"🚀 SUCCESS: {len(player_data)} players processed.")

if __name__ == "__main__":
    main()
