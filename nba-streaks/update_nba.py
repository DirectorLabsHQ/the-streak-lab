import requests
import json
from datetime import datetime
import time

TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def get_player_stats(player_name, team_code):
    try:
        # 1. Search JSON (Capture the ID)
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        search_res = requests.get(search_url, timeout=10).json()
        if 'items' not in search_res or not search_res['items']: return None
        player_id = search_res['items'][0]['id']

        # 2. Gamelog JSON (Capture the Stats)
        log_url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        log_res = requests.get(log_url, timeout=10).json()
        
        labels = log_res.get('labels', [])
        events = log_res.get('events', [])[:10]
        if not labels or not events: return None

        # Map the labels to find the right column (e.g., PTS is index 3)
        idx = {
            'pts': labels.index('PTS') if 'PTS' in labels else None,
            'reb': labels.index('REB') if 'REB' in labels else None,
            'ast': labels.index('AST') if 'AST' in labels else None,
            'tpm': labels.index('3PM') if '3PM' in labels else None
        }

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for event in events:
            stats = event.get('stats', [])
            # Safely check each stat against your targets
            if idx['pts'] is not None and float(stats[idx['pts']]) >= TARGETS['pts']: hits['pts'] += 1
            if idx['reb'] is not None and float(stats[idx['reb']]) >= TARGETS['reb']: hits['reb'] += 1
            if idx['ast'] is not None and float(stats[idx['ast']]) >= TARGETS['ast']: hits['ast'] += 1
            if idx['tpm'] is not None and float(stats[idx['tpm']]) >= TARGETS['tpm']: hits['tpm'] += 1

        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(events)) * 100),
            "reb_heat": int((hits['reb'] / len(events)) * 100),
            "ast_heat": int((hits['ast'] / len(events)) * 100),
            "tpm_heat": int((hits['tpm'] / len(events)) * 100),
            "last_game": f"{events[0]['gameDate'][:10]}"
        }
    except Exception:
        return None

def main():
    player_data = []
    # Reads your players.txt (including the GSW ones we added)
    with open('nba-streaks/players.txt', 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    print(f"🏀 Syncing {len(lines)} athletes...")
    for line in lines:
        parts = line.split()
        team_code = parts[-1]
        player_name = " ".join(parts[:-1])
        
        stats = get_player_stats(player_name, team_code)
        if stats:
            player_data.append(stats)
            print(f"✅ {player_name} synced.")
        
        time.sleep(0.7) # Crucial delay for 100+ players

    # Push to your final site file
    output = {"last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"), "players": player_data}
    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"🚀 SUCCESS: JSON updated with {len(player_data)} players.")

if __name__ == "__main__":
    main()
