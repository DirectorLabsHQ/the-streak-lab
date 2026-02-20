import requests
import json
from datetime import datetime
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}


def safe_float(val):
    try:
        return float(str(val).strip())
    except:
        return 0.0


def get_player_id(player_name):
    try:
        url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=5&type=player"
        res = requests.get(url, timeout=10).json()

        for item in res.get('items', []):
            if isinstance(item, dict) and item.get('type') == 'player':
                return item.get('id')

        return None
    except Exception as e:
        print(f"❌ ID error for {player_name}: {e}")
        return None


def get_stat_index(labels, keys):
    for key in keys:
        if key in labels:
            return labels.index(key)
    return None


def extract_data(data, player_name):
    labels = []
    entries = []

    # --- NEW ESPN STRUCTURE (SAFE) ---
    regular = data.get('regularSeason')

    if isinstance(regular, dict):
        groups = regular.get('groups', [])

        if isinstance(groups, list):
            for group in groups:
                if isinstance(group, dict):  # 🔥 prevents crash
                    if not labels:
                        labels = group.get('labels', [])
                    entries.extend(group.get('entries', []))

    # --- FALLBACKS ---
    if not entries:
        if isinstance(data.get('events'), list):
            entries = data.get('events', [])
            labels = data.get('labels', [])

    if not entries:
        if isinstance(data.get('entries'), list):
            entries = data.get('entries', [])
            labels = data.get('labels', [])

    if not entries:
        season = data.get('season', {})
        if isinstance(season, dict):
            entries = season.get('entries', [])
            labels = data.get('labels', [])

    # Final validation
    if not labels or not entries:
        print(f"⚠️ No valid data for {player_name}")
        return None, None

    return labels, entries


def get_player_stats(player_name, team_code):
    try:
        player_id = get_player_id(player_name)
        if not player_id:
            print(f"❌ No ID for {player_name}")
            return None

        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        data = requests.get(url, timeout=10).json()

        labels, entries = extract_data(data, player_name)

        if not labels or not entries:
            return None

        # Stat indices
        p_idx = get_stat_index(labels, ['PTS'])
        r_idx = get_stat_index(labels, ['REB'])
        a_idx = get_stat_index(labels, ['AST'])

        m_idx = get_stat_index(labels, ['3PM'])
        if m_idx is None:
            m_idx = get_stat_index(labels, ['3PT'])

        # Filter valid games
        valid_games = [e for e in entries if isinstance(e, dict) and e.get('stats')]

        valid_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_games = valid_games[:10]

        if not recent_games:
            print(f"⚠️ No recent games for {player_name}")
            return None

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}

        for game in recent_games:
            stats = game.get('stats', [])

            if p_idx is not None and len(stats) > p_idx:
                if safe_float(stats[p_idx]) >= TARGETS['pts']:
                    hits['pts'] += 1

            if r_idx is not None and len(stats) > r_idx:
                if safe_float(stats[r_idx]) >= TARGETS['reb']:
                    hits['reb'] += 1

            if a_idx is not None and len(stats) > a_idx:
                if safe_float(stats[a_idx]) >= TARGETS['ast']:
                    hits['ast'] += 1

            if m_idx is not None and len(stats) > m_idx:
                if safe_float(stats[m_idx]) >= TARGETS['tpm']:
                    hits['tpm'] += 1

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
        print("❌ Could not find nba-streaks/players.txt")
        return

    print(f"🏀 Syncing {len(lines)} players...")

    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])

        stats = get_player_stats(name, team)

        if stats:
            player_data.append(stats)
            print(f"✅ {name}")
        else:
            print(f"⚠️ Skipped {name}")

        time.sleep(0.6)

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)

    print(f"🚀 SUCCESS: {len(player_data)} players saved")


if __name__ == "__main__":
    main()
