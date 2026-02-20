import requests
import json
from datetime import datetime
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

# --- SAFE REQUEST HELPER ---
def safe_get_json(url, retries=3):
    """Fetches JSON with retry logic and type checking to prevent crashes."""
    for i in range(retries):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, dict):
                    return data
            elif res.status_code == 429:
                print(f"⚠️ Rate limited. Waiting {2 * (i+1)}s...")
                time.sleep(2 * (i+1))
        except Exception:
            pass
        time.sleep(1.2)
    return None

def get_player_stats_hybrid(player_name, team_code):
    try:
        # 1. SEARCH PLAYER
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        s_data = safe_get_json(search_url)
        if not s_data or not s_data.get('items'):
            return None

        p_id = str(s_data['items'][0]['id'])

        # 2. GET GAMELOG (Season 2026, Regular Season type 2)
        log_url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{p_id}/gamelog?season=2026&seasontype=2"
        log_data = safe_get_json(log_url)
        if not log_data:
            return None

        # 3. ROBUST ENTRY EXTRACTION (Handles all ESPN variations)
        entries = []
        if isinstance(log_data.get('entries'), list):
            entries = log_data['entries']
        elif isinstance(log_data.get('regularSeason'), dict):
            for group in log_data['regularSeason'].get('groups', []):
                entries.extend(group.get('entries', []))
        
        entries = [e for e in entries if isinstance(e, dict)]
        if not entries:
            return None

        # Sort newest first & take last 10
        entries.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_entries = entries[:10]

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        games_processed = 0
        last_game_date = ""

        # 4. SCAN EACH GAME SUMMARY
        for entry in recent_entries:
            game_id = entry.get('eventId') or entry.get('event', {}).get('id')
            if not game_id: continue

            summary_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
            game_data = safe_get_json(summary_url)
            if not game_data: continue

            box = game_data.get('boxscore', {})
            for team_box in box.get('players', []):
                stats_list = team_box.get('statistics', [])
                if not stats_list: continue

                # ESPN statistics is usually a list; we want the first block
                stats_block = stats_list[0]
                keys = [str(k).upper() for k in stats_block.get('keys', [])]
                athletes = stats_block.get('athletes', [])

                for p_entry in athletes:
                    if str(p_entry.get('athlete', {}).get('id')) == p_id:
                        s = p_entry.get('stats', [])

                        def get_v(stat_name):
                            try:
                                return float(s[keys.index(stat_name.upper())])
                            except (ValueError, IndexError): return 0.0

                        if get_v('PTS') >= TARGETS['pts']: hits['pts'] += 1
                        if get_v('REB') >= TARGETS['reb']: hits['reb'] += 1
                        if get_v('AST') >= TARGETS['ast']: hits['ast'] += 1
                        if get_v('3PM') >= TARGETS['tpm']: hits['tpm'] += 1

                        if not last_game_date:
                            last_game_date = entry.get('gameDate', '')[:10]
                        games_processed += 1
                        break

            time.sleep(0.8) # Critical for stability

        if games_processed == 0: return None

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
    except Exception:
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
            print(f"✅ {name} ({stats['pts_heat']}% Pts Heat)")
        else:
            print(f"⚠️ Skipped {name}")

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)

    print(f"🚀 DONE: {len(player_data)} players saved.")

if __name__ == "__main__":
    main()
