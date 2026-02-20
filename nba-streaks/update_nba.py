import requests
import json
from datetime import datetime
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def get_player_stats_hybrid(player_name, team_code):
    try:
        # -------------------------------
        # 1. SEARCH PLAYER ID
        # -------------------------------
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        s_res = requests.get(search_url, timeout=10).json()

        if not s_res.get('items'):
            print(f"❌ No search result for {player_name}")
            return None

        p_id = str(s_res['items'][0]['id'])

        # -------------------------------
        # 2. GET GAMELOG
        # -------------------------------
        log_url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{p_id}/gamelog?season=2026&seasontype=2"
        log_data = requests.get(log_url, timeout=10).json()

        # -------------------------------
        # 3. EXTRACT ENTRIES (ALL FORMATS)
        # -------------------------------
        entries = []

        if isinstance(log_data.get('entries'), list):
            entries = log_data['entries']

        elif isinstance(log_data.get('events'), list):
            entries = log_data['events']

        elif isinstance(log_data.get('log'), dict):
            if isinstance(log_data['log'].get('events'), list):
                entries = log_data['log']['events']

        elif isinstance(log_data.get('regularSeason'), dict):
            for group in log_data['regularSeason'].get('groups', []):
                if isinstance(group, dict):
                    entries.extend(group.get('entries', []))

        # Clean entries
        entries = [e for e in entries if isinstance(e, dict)]

        if not entries:
            print(f"❌ No entries for {player_name}")
            return None

        # Sort newest first
        entries.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_entries = entries[:10]

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        games_processed = 0
        last_game_date = ""

        # -------------------------------
        # 4. SCAN EACH GAME
        # -------------------------------
        for entry in recent_entries:
            game_id = entry.get('eventId') or entry.get('event', {}).get('id')
            if not game_id:
                continue

            summary_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
            game_data = requests.get(summary_url, timeout=10).json()

            players_data = game_data.get('boxscore', {}).get('players', [])

            for team_box in players_data:
                stats_block = team_box.get('statistics', [{}])[0]

                keys = [str(k).upper() for k in stats_block.get('keys', [])]
                athletes = stats_block.get('athletes', [])

                for p_entry in athletes:
                    if str(p_entry.get('athlete', {}).get('id')) == p_id:
                        stats = p_entry.get('stats', [])

                        def get_v(stat):
                            try:
                                stat = stat.upper()
                                if stat in keys:
                                    return float(stats[keys.index(stat)])
                                return 0.0
                            except:
                                return 0.0

                        if get_v('PTS') >= TARGETS['pts']:
                            hits['pts'] += 1
                        if get_v('REB') >= TARGETS['reb']:
                            hits['reb'] += 1
                        if get_v('AST') >= TARGETS['ast']:
                            hits['ast'] += 1
                        if get_v('3PM') >= TARGETS['tpm']:
                            hits['tpm'] += 1

                        if not last_game_date:
                            last_game_date = entry.get('gameDate', '')[:10]

                        games_processed += 1
                        break

            # Prevent rate limiting
            time.sleep(0.6)

        if games_processed == 0:
            print(f"❌ No valid games for {player_name}")
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


def main():
    player_data = []

    try:
        with open('nba-streaks/players.txt', 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
    except:
        print("❌ Could not read players.txt")
        return

    print(f"🏀 Syncing {len(lines)} players...")

    for line in lines:
        parts = line.split()
        team = parts[-1]
        name = " ".join(parts[:-1])

        stats = get_player_stats_hybrid(name, team)

        if stats:
            player_data.append(stats)
            print(f"✅ {name} ({stats['pts_heat']}% Heat)")
        else:
            print(f"⚠️ Skipped {name}")

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)

    print(f"🚀 DONE: {len(player_data)} players processed.")


if __name__ == "__main__":
    main()
