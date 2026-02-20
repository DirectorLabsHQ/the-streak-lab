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

'pts': get_idx(['PTS']),
            'reb': get_idx(['REB']),
            'ast': get_idx(['AST']),
            'tpm': get_idx(['3PM', '3PT'])
        }

        # 3. Find Entries (Using your recursive or direct path)
        entries = data.get('entries', []) or data.get('season', {}).get('entries', [])
        if not entries: return None

        valid_games = [e for e in entries if e.get('stats')]
        valid_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_games = valid_games[:10]

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        
        for game in recent_games:
            s = game.get('stats', [])
            # Only check if we found a valid index for that stat
            if idx['pts'] is not None and safe_float(s[idx['pts']]) >= TARGETS['pts']: hits['pts'] += 1
            if idx['reb'] is not None and safe_float(s[idx['reb']]) >= TARGETS['reb']: hits['reb'] += 1
            if idx['ast'] is not None and safe_float(s[idx['ast']]) >= TARGETS['ast']: hits['ast'] += 1
            if idx['tpm'] is not None and safe_float(s[idx['tpm']]) >= TARGETS['tpm']: hits['tpm'] += 1

        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(recent_games)) * 100),
            "reb_heat": int((hits['reb'] / len(recent_games)) * 100),
            "ast_heat": int((hits['ast'] / len(recent_games)) * 100),
            "tpm_heat": int((hits['tpm'] / len(recent_games)) * 100),
            "last_game": recent_games[0].get('gameDate', '')[:10]
        }
    except:
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
