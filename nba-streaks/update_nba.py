import requests
import json
from datetime import datetime, timedelta
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def get_recent_game_ids(days=7):
    game_ids = []
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}"
        
        try:
            data = requests.get(url, timeout=10).json()
            events = data.get('events', [])
            
            for event in events:
                game_ids.append(event.get('id'))
        except:
            continue
        
        time.sleep(0.3)
    
    return list(set(game_ids))


def get_player_stats_from_games(player_name, team_code, game_ids):
    hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
    games_processed = 0
    last_game_date = ""

    try:
        # Get player ID once
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        res = requests.get(search_url, timeout=10).json()
        if not res.get('items'):
            return None

        p_id = str(res['items'][0]['id'])

        for game_id in game_ids:
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
            
            try:
                data = requests.get(url, timeout=10).json()
                players = data.get('boxscore', {}).get('players', [])

                for team in players:
                    stats_block = team.get('statistics', [{}])[0]
                    keys = [str(k).upper() for k in stats_block.get('keys', [])]

                    for athlete in stats_block.get('athletes', []):
                        if str(athlete.get('athlete', {}).get('id')) == p_id:
                            stats = athlete.get('stats', [])

                            def get_v(stat):
                                try:
                                    if stat in keys:
                                        return float(stats[keys.index(stat)])
                                    return 0
                                except:
                                    return 0

                            if get_v('PTS') >= TARGETS['pts']:
                                hits['pts'] += 1
                            if get_v('REB') >= TARGETS['reb']:
                                hits['reb'] += 1
                            if get_v('AST') >= TARGETS['ast']:
                                hits['ast'] += 1
                            if get_v('3PM') >= TARGETS['tpm']:
                                hits['tpm'] += 1

                            games_processed += 1

                            if not last_game_date:
                                last_game_date = data.get('header', {}).get('competitions', [{}])[0].get('date', '')[:10]

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

    except:
        return None


def main():
    player_data = []

    with open('nba-streaks/players.txt', 'r') as f:
        lines = [l.strip() for l in f if l.strip()]

    print("📡 Fetching recent NBA games...")
    game_ids = get_recent_game_ids(days=7)

    print(f"🏀 Processing {len(lines)} players across {len(game_ids)} games...")

    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])

        stats = get_player_stats_from_games(name, team, game_ids)

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
