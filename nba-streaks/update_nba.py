import requests
import json
from datetime import datetime, timedelta
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}


def get_all_recent_boxscores(days=14):
    """Downloads every boxscore from the last X days ONCE."""
    game_ids = []
    all_boxscores = []

    print(f"📡 Gathering game IDs for the last {days} days...")

    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}"

        try:
            data = requests.get(url, timeout=10).json()
            for event in data.get('events', []):
                gid = event.get('id')
                if gid:
                    game_ids.append(gid)
        except:
            continue

        time.sleep(0.2)

    game_ids = list(set(game_ids))
    print(f"📦 Downloading {len(game_ids)} boxscores...")

    for gid in game_ids:
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={gid}"
            data = requests.get(url, timeout=10).json()

            game_date = data.get('header', {}).get('competitions', [{}])[0].get('date', '')[:10]
            players = data.get('boxscore', {}).get('players', [])

            if players:
                all_boxscores.append({
                    "date": game_date,
                    "players": players
                })

            print(f"✔️ Loaded Game {gid}", end="\r")

        except:
            continue

        time.sleep(0.4)

    # Sort newest first
    all_boxscores.sort(key=lambda x: x['date'], reverse=True)

    return all_boxscores


def get_stat_index(keys, stat_name):
    """Safely find stat index"""
    try:
        return keys.index(stat_name)
    except ValueError:
        return None


def safe_stat_value(stats, idx):
    """Safely extract stat value"""
    try:
        if idx is None:
            return 0
        return float(stats[idx])
    except:
        return 0


def get_player_stats_optimized(player_name, team_code, p_id, boxscores):
    hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
    games_processed = 0
    last_game_date = ""

    for game in boxscores:
        if games_processed >= 10:
            break

        found_in_game = False

        for team_data in game['players']:
            stats_blocks = team_data.get('statistics', [])

            if not stats_blocks:
                continue

            stats_block = stats_blocks[0]

            keys = [str(k).upper() for k in stats_block.get('keys', [])]

            p_idx = get_stat_index(keys, 'PTS')
            r_idx = get_stat_index(keys, 'REB')
            a_idx = get_stat_index(keys, 'AST')
            t_idx = get_stat_index(keys, '3PM')

            for athlete in stats_block.get('athletes', []):
                athlete_id = str(athlete.get('athlete', {}).get('id'))

                if athlete_id == p_id:
                    stats = athlete.get('stats', [])

                    if safe_stat_value(stats, p_idx) >= TARGETS['pts']:
                        hits['pts'] += 1
                    if safe_stat_value(stats, r_idx) >= TARGETS['reb']:
                        hits['reb'] += 1
                    if safe_stat_value(stats, a_idx) >= TARGETS['ast']:
                        hits['ast'] += 1
                    if safe_stat_value(stats, t_idx) >= TARGETS['tpm']:
                        hits['tpm'] += 1

                    if not last_game_date:
                        last_game_date = game['date']

                    games_processed += 1
                    found_in_game = True
                    break

            if found_in_game:
                break

    if games_processed == 0:
        return None

    return {
        "name": player_name,
        "team_code": team_code,
        "pts_heat": int((hits['pts'] / games_processed) * 100),
        "reb_heat": int((hits['reb'] / games_processed) * 100),
        "ast_heat": int((hits['ast'] / games_processed) * 100),
        "tpm_heat": int((hits['tpm'] / games_processed) * 100),
        "last_game": last_game_date
    }


def get_player_id(name):
    """Fetch player ID from ESPN"""
    try:
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={name.replace(' ', '%20')}&limit=1&type=player"
        data = requests.get(search_url, timeout=10).json()
        return str(data['items'][0]['id'])
    except:
        return None


def main():
    with open('nba-streaks/players.txt', 'r') as f:
        lines = [l.strip() for l in f if l.strip()]

    # Step 1: Load all games once
    all_boxscores = get_all_recent_boxscores(days=14)

    final_data = []

    print(f"\n🔥 Calculating Heat for {len(lines)} players...")

    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])

        p_id = get_player_id(name)

        if not p_id:
            print(f"❌ {name} (ID not found)")
            continue

        stats = get_player_stats_optimized(name, team, p_id, all_boxscores)

        if stats:
            final_data.append(stats)
            print(f"✅ {name} ({stats['pts_heat']}%)")
        else:
            print(f"⚠️ {name} (No games found)")

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump({
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "players": final_data
        }, f, indent=4)


if __name__ == "__main__":
    main()
