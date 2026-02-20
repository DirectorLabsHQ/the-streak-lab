import requests
import json
from datetime import datetime
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

def find_label(labels, possible):
    for name in possible:
        if name in labels:
            return labels.index(name)
    return None

def get_player_id(player_name):
    url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=5&type=player"
    res = requests.get(url, timeout=10).json()

    for item in res.get('items', []):
        if item.get('type') == 'player':
            return item.get('id')

    return None

def get_player_stats(player_name, team_code):
    try:
        player_id = get_player_id(player_name)
        if not player_id:
            print(f"❌ No ID for {player_name}")
            return None

        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        res = requests.get(url, timeout=10).json()

        labels = res.get('labels', [])
        events = res.get('events', [])

        if not labels or not events:
            print(f"⚠️ No games for {player_name}")
            return None

        events = events[:10]

        idx = {
            'pts': find_label(labels, ['PTS']),
            'reb': find_label(labels, ['REB']),
            'ast': find_label(labels, ['AST']),
            'tpm': find_label(labels, ['3PM', '3PT'])
        }

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}

        for event in events:
            stats = event.get('stats', [])

            if idx['pts'] is not None and len(stats) > idx['pts']:
                if safe_float(stats[idx['pts']]) >= TARGETS['pts']:
                    hits['pts'] += 1

            if idx['reb'] is not None and len(stats) > idx['reb']:
                if safe_float(stats[idx['reb']]) >= TARGETS['reb']:
                    hits['reb'] += 1

            if idx['ast'] is not None and len(stats) > idx['ast']:
                if safe_float(stats[idx['ast']]) >= TARGETS['ast']:
                    hits['ast'] += 1

            if idx['tpm'] is not None and len(stats) > idx['tpm']:
                if safe_float(stats[idx['tpm']]) >= TARGETS['tpm']:
                    hits['tpm'] += 1

        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(events)) * 100),
            "reb_heat": int((hits['reb'] / len(events)) * 100),
            "ast_heat": int((hits['ast'] / len(events)) * 100),
            "tpm_heat": int((hits['tpm'] / len(events)) * 100),
            "last_game": events[0].get('gameDate', '')[:10]
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

        time.sleep(0.6)

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)

    print(f"🚀 DONE: {len(player_data)} players saved")


if __name__ == "__main__":
    main()
