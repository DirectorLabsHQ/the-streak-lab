import requests
import json
from datetime import datetime, timedelta
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

# -----------------------------------
# Get recent NBA game IDs
# -----------------------------------
def get_recent_game_ids(days=30):
    game_ids = []

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

        time.sleep(0.3)

    return list(set(game_ids))


# -----------------------------------
# Extract stats from games
# -----------------------------------
def get_player_stats(player_name, team_code, game_ids):
    try:
        # Get player ID
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        res = requests.get(search_url, timeout=10).json()

        if not res.get('items'):
            return None

        p_id = str(res['items'][0]['id'])

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        games_processed = 0
        last_game_date = ""

        # Loop through games
        for game_id in game_ids:
            try:
                url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
                data = requests.get(url, timeout=10).json()

                players = data.get('boxscore', {}).get('players', [])
                found_player = False

                for team in players:
                    stats_block = team.get('statistics', [{}])[0]

                    raw_keys = stats_block.get('keys', [])
                    keys = [str(k).upper() for k in raw_keys]

                    def find_idx(names):
                        for name in names:
                            if name.upper() in keys:
                                return keys.index(name.upper())
                        return None

                    p_idx = find_idx(['PTS', 'POINTS'])
                    r_idx = find_idx(['REB', 'REBOUNDS'])
                    a_idx = find_idx(['AST', 'ASSISTS'])
                    t_idx = find_idx(['3PM', '3PT', 'THREEPOINTFIELDGOALSMADE'])

                    for athlete in stats_block.get('athletes', []):
                        if str(athlete.get('athlete', {}).get('id')) == p_id:
                            found_player = True
                            stats = athlete.get('stats', [])

                            def get_val(idx):
                                try:
                                    if idx is not None and idx < len(stats):
                                        return float(stats[idx])
                                    return 0
                                except:
                                    return 0

                            if get_val(p_idx) >= TARGETS['pts']:
                                hits['pts'] += 1
                            if get_val(r_idx) >= TARGETS['reb']:
                                hits['reb'] += 1
                            if get_val(a_idx) >= TARGETS['ast']:
                                hits['ast'] += 1
                            if get_val(t_idx) >= TARGETS['tpm']:
                                hits['tpm'] += 1

                            games_processed += 1

                            if not last_game_date:
                                last_game_date = data.get('header', {}) \
                                    .get('competitions', [{}])[0] \
                                    .get('date', '')[:10]

                            break

                # ONLY count real games
                if not found_player:
                    continue

                # Stop at last 10 real games
                if games_processed >= 10:
                    break

                time.sleep(0.4)

            except:
                continue

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

    except Exception as e:
        print(f"❌ Error with {player_name}: {e}")
        return None


# -----------------------------------
# MAIN
# -----------------------------------
def main():
    player_data = []

    with open('nba-streaks/players.txt', 'r') as f:
        lines = [l.strip() for l in f if l.strip()]

    print("📡 Fetching recent NBA games...")
    game_ids = get_recent_game_ids(days=30)

    print(f"🏀 Processing {len(lines)} players across {len(game_ids)} games...")

    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])

        stats = get_player_stats(name, team, game_ids)

        if stats:
            player_data.append(stats)
            print(f"✅ {name} ({stats['pts_heat']}%)")
        else:
            print(f"⚠️ {name}")

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)

    print(f"🚀 DONE: {len(player_data)} players")


if __name__ == "__main__":
    main()
