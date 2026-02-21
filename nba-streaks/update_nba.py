import requests
import json
from datetime import datetime, timedelta
import time
import unicodedata

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}


def normalize(text):
    return unicodedata.normalize('NFKD', text)\
        .encode('ascii', 'ignore')\
        .decode('ascii')\
        .lower()


def get_all_recent_boxscores(days=21):
    game_ids = set()
    all_boxscores = []

    print(f"📡 Gathering game IDs for last {days} days...")

    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
       url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/boxscore?event={gid}"

        try:
            data = requests.get(url, timeout=10).json()
            for event in data.get('events', []):
                if event.get('id'):
                    game_ids.add(event['id'])
        except:
            continue

        time.sleep(0.2)

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

        except:
            continue

        time.sleep(0.35)

    all_boxscores.sort(key=lambda x: x['date'], reverse=True)
    return all_boxscores


def get_correct_stat_block(team):
    for block in team.get('statistics', []):
        keys = [str(k).upper() for k in block.get('keys', [])]
        if 'PTS' in keys:
            return block
    return None


def get_player_stats(player_name, team_code, boxscores):
    hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
    games_processed = 0
    last_game_date = ""

    player_name_normalized = normalize(player_name)

    for game in boxscores:
        if games_processed >= 10:
            break

        found = False

        for team in game['players']:

            stats_block = get_correct_stat_block(team)
            if not stats_block:
                continue

            keys = [str(k).upper() for k in stats_block.get('keys', [])]
            athletes = stats_block.get('athletes', [])

            def find_key(options):
                for opt in options:
                    if opt in keys:
                        return keys.index(opt)
                return None

            p_idx = find_key(['PTS'])
            r_idx = find_key(['REB', 'TREB'])
            a_idx = find_key(['AST'])
            t_idx = find_key(['3PM', 'FG3M'])

            for athlete in athletes:
                raw_name = athlete.get('athlete', {}).get('displayName', '')
                name = normalize(raw_name)

                if name == player_name_normalized:
                    stats = athlete.get('stats', [])

                    def val(i):
                        try:
                            if i is None:
                                return 0
                            v = stats[i]
                            if v in ("", None):
                                return 0
                            return float(v)
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
                    found = True
                    break

            if found:
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


def main():
    try:
        with open('nba-streaks/players.txt', 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
    except:
        print("❌ players.txt not found")
        return

    all_boxscores = get_all_recent_boxscores(days=21)

    print(f"\n🔥 Calculating Heat for {len(lines)} players...")

    results = []

    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])

        stats = get_player_stats(name, team, all_boxscores)

        if stats:
            results.append(stats)
            print(f"✅ {name} ({stats['pts_heat']}%)")
        else:
            print(f"⚠️ {name} (No games found)")

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "players": results
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)

    print(f"\n🚀 DONE: {len(results)} players processed")


if __name__ == "__main__":
    main()
