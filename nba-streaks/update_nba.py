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

            all_boxscores.append({
                "date": game_date,
                "players": players
            })

            print(f"✔️ Loaded Game {gid}", end="\r")

        except:
            continue

        time.sleep(0.4)

    all_boxscores.sort(key=lambda x: x['date'], reverse=True)
    return all_boxscores


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

            # ✅ FIX: select "totals" block only
            stats_block = None
            for block in stats_blocks:
                if isinstance(block, dict) and str(block.get('name', '')).lower() == 'totals':
                    stats_block = block
                    break

            if not stats_block:
                continue

            keys = [str(k).upper() for k in stats_block.get('keys', [])]

            # Index mapping
            p_idx = keys.index('PTS') if 'PTS' in keys else None
            r_idx = keys.index('REB') if 'REB' in keys else None
            a_idx = keys.index('AST') if 'AST' in keys else None

            # ✅ FIX: handle 3PM vs FG3M
            t_idx = None
            if '3PM' in keys:
                t_idx = keys.index('3PM')
            elif 'FG3M' in keys:
                t_idx = keys.index('FG3M')

            for athlete in stats_block.get('athletes', []):
                if str(athlete.get('athlete', {}).get('id')) == p_id:
                    stats = athlete.get('stats', [])

                    def val(idx):
                        try:
                            return float(stats[idx]) if idx is not None else 0
                        except:
                            return 0

                    if val(p_idx) >= TARGETS['pts']:
                        hits['pts'] += 1
                    if val(r_idx) >= TARGETS['reb']:
                        hits['reb'] += 1
                    if val(a_idx) >= TARGETS['ast']:
                        hits['ast'] += 1
                    if val(t_idx) >= TARGETS['tpm']:
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


def get_player_id(player_name):
    try:
        url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        res = requests.get(url, timeout=10).json()
        return str(res['items'][0]['id'])
    except:
        return None


def main():
    with open('nba-streaks/players.txt', 'r') as f:
        lines = [l.strip() for l in f if l.strip()]

    # STEP 1: load all games once
    all_boxscores = get_all_recent_boxscores(days=14)

    # STEP 2: process players
    final_data = []

    print(f"\n🔥 Calculating Heat for {len(lines)} players...")

    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])

        p_id = get_player_id(name)
        if not p_id:
            print(f"⚠️ {name} (No ID)")
            continue

        stats = get_player_stats_optimized(name, team, p_id, all_boxscores)

        if stats:
            final_data.append(stats)
            print(f"✅ {name} ({stats['pts_heat']}%)")
        else:
            print(f"⚠️ {name} (No games)")

    # STEP 3: save output
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "players": final_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)

    print(f"\n🚀 DONE: {len(final_data)} players updated.")


if __name__ == "__main__":
    main()
