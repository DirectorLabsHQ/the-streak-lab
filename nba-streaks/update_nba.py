import requests
import json
from datetime import datetime
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def get_player_stats_deep(player_name, team_code):
    try:
        # 1. Search for Player ID
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        s_res = requests.get(search_url, timeout=10).json()
        p_id = s_res['items'][0]['id']

        # 2. Get the Event IDs (Last 10 Regular Season games)
        events_url = f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/seasons/2026/types/2/athletes/{p_id}/events?limit=10"
        events_data = requests.get(events_url, timeout=10).json()
        
        event_items = events_data.get('items', [])
        if not event_items: return None
        
        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        last_game_date = ""
        games_processed = 0

        # 3. Drill into each Game Summary
        for item in event_items:
            game_id = item['$ref'].split('/')[-1].split('?')[0]
            summary_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
            game_data = requests.get(summary_url, timeout=10).json()

            # Find player in the boxscore
            for team_box in game_data.get('boxscore', {}).get('players', []):
                stats_group = team_box.get('statistics', [{}])[0]
                keys = stats_group.get('keys', [])
                
                for p_entry in stats_group.get('athletes', []):
                    if p_entry.get('athlete', {}).get('id') == p_id:
                        s = p_entry.get('stats', [])
                        
                        def get_v(key):
                            return float(s[keys.index(key)]) if key in keys else 0.0

                        if get_v('pts') >= TARGETS['pts']: hits['pts'] += 1
                        if get_v('reb') >= TARGETS['reb']: hits['reb'] += 1
                        if get_v('ast') >= TARGETS['ast']: hits['ast'] += 1
                        if get_v('3pm') >= TARGETS['tpm']: hits['tpm'] += 1
                        
                        if not last_game_date:
                            last_game_date = game_data.get('header', {}).get('competitions', [{}])[0].get('date', '')[:10]
                        games_processed += 1
            
            time.sleep(1) # Crucial: prevents ESPN from blocking your GitHub Action IP

        if games_processed == 0: return None
        return {
            "name": player_name, "team_code": team_code,
            "pts_heat": int((hits['pts']/games_processed)*100),
            "reb_heat": int((hits['reb']/games_processed)*100),
            "ast_heat": int((hits['ast']/games_processed)*100),
            "tpm_heat": int((hits['tpm']/games_processed)*100),
            "last_game": last_game_date
        }
    except: return None

def main():
    player_data = []
    with open('nba-streaks/players.txt', 'r') as f:
        lines = [l.strip() for l in f if l.strip()]

    print(f"🚀 Deep Scan started for {len(lines)} athletes...")
    for line in lines:
        parts = line.split()
        team, name = parts[-1], " ".join(parts[:-1])
        stats = get_player_stats_deep(name, team)
        if stats:
            player_data.append(stats)
            print(f"✅ {name}")
        else: print(f"❌ {name}")

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump({"last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"), "players": player_data}, f, indent=4)

if __name__ == "__main__":
    main()
