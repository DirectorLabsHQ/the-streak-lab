import requests
import json
from datetime import datetime
import time

# Define the targets for your Heat Index (Last 10 Games)
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
        s_res = requests.get(search_url, timeout=10).json()
        if 'items' not in s_res or not s_res['items']:
            return None
        p_id = s_res['items'][0]['id']
        
        # 2. Fetch Gamelog (v3 is the 2026 standard)
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{p_id}/gamelog"
        data = requests.get(url, timeout=10).json()

        # 3. Dynamic Index Matching (SOLVES THE 0% HEAT BUG)
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

        # 4. Deep Extraction (SOLVES THE SKIPPING BUG)
        entries = []
        # Path A: Nested Groups (Primary 2026 Structure)
        if 'regularSeason' in data:
            groups = data['regularSeason'].get('groups', [])
            for group in groups:
                entries.extend(group.get('entries', []))
        
        # Path B: Standard Top-Level Fallback
        if not entries:
            entries = data.get('entries', []) or data.get('season', {}).get('entries', [])

        if not entries:
            return None

        # Sort by date (newest first) and filter for games with stats
        valid_games = [e for e in entries if e.get('stats')]
        valid_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_games = valid_games[:10]
        
        if not recent_games:
            return None

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for game in recent_games:
            s = game.get('stats', [])
            # Only count hits if the stat column was actually found
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
    try:
        with open('nba-streaks/players.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ Error: players.txt not found in nba-streaks/ directory.")
        return

    print(f"🏀 Syncing {len(lines)} athletes for The Streak Lab...")
    for line in lines:
        parts = line.split()
        if not parts: continue
        
        team = parts[-1]
        name = " ".join(parts[:-1])
        
        stats = get_player_stats(name, team)
        if stats:
            player_data.append(stats)
            print(f"✅ {name} ({stats['pts_heat']}% PTS Heat)")
        else:
            print(f"⚠️ Skipping {name}: No recent game data found.")
        
        # Respect the API rate limits
        time.sleep(0.5)

    # Prepare final JSON
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    
    print(f"\n🚀 SUCCESS: {len(player_data)} players processed and saved to streak_data.json")

if __name__ == "__main__":
    main()
