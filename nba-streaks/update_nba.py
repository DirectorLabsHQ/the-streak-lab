import requests
import json
from datetime import datetime
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def safe_float(val):
    try:
        # Trims spaces and handles 'DNP' or '--' by returning 0.0
        return float(str(val).strip()) if val else 0.0
    except:
        return 0.0

def find_label(labels, possible_names):
    for name in possible_names:
        if name in labels:
            return labels.index(name)
    return None

def get_player_id(player_name):
    # STEP 1: Search for active NBA players specifically
    url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=5&type=player"
    try:
        res = requests.get(url, timeout=10).json()
        for item in res.get('items', []):
            # Filtering for 'player' type ensures we don't get team results or retired legends
            if item.get('type') == 'player':
                return item.get('id')
    except Exception as e:
        print(f"❌ Search Error for {player_name}: {e}")
    return None

def get_player_stats(player_name, team_code):
    try:
        player_id = get_player_id(player_name)
        if not player_id:
            print(f"❌ No Active ID found for {player_name}")
            return None

        # STEP 2: Fetch Gamelog JSON
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        res = requests.get(url, timeout=10).json()

        labels = res.get('labels', [])
        events = res.get('events', [])

        if not labels or not events:
            print(f"⚠️ No recent games for {player_name} (likely inactive/injured)")
            return None

        # Get the 10 most recent games
        recent_games = events[:10]

        # STEP 3: Map labels to indices (Handles 3PM vs 3PT)
        idx = {
            'pts': find_label(labels, ['PTS']),
            'reb': find_label(labels, ['REB']),
            'ast': find_label(labels, ['AST']),
            'tpm': find_label(labels, ['3PM', '3PT'])
        }

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}

        for game in recent_games:
            stats = game.get('stats', [])
            # Only count if the index exists AND the stat value is numeric
            if idx['pts'] is not None and safe_float(stats[idx['pts']]) >= TARGETS['pts']: hits['pts'] += 1
            if idx['reb'] is not None and safe_float(stats[idx['reb']]) >= TARGETS['reb']: hits['reb'] += 1
            if idx['ast'] is not None and safe_float(stats[idx['ast']]) >= TARGETS['ast']: hits['ast'] += 1
            if idx['tpm'] is not None and safe_float(stats[idx['tpm']]) >= TARGETS['tpm']: hits['tpm'] += 1

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
        print(f"❌ Critical Error with {player_name}: {e}")
        return None

def main():
    player_data = []
    try:
        with open('nba-streaks/players.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except:
        print("❌ Could not open players.txt")
        return

    print(f"🏀 Syncing {len(lines)} athletes for The Streak Lab...")

    for line in lines:
        parts = line.split()
        team_code = parts[-1]
        player_name = " ".join(parts[:-1])

        stats = get_player_stats(player_name, team_code)
        if stats:
            player_data.append(stats)
            print(f"✅ {player_name} synced.")
        
        # Slightly longer sleep to be respectful of the API with 100+ players
        time.sleep(0.7)

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)

    print(f"🚀 DONE: {len(player_data)} players saved to JSON.")

if __name__ == "__main__":
    main()
