import requests
import json
from datetime import datetime
import time

# Targets for your site's "Heat" mode
TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def get_player_stats(player_name, team_code):
    try:
        # STEP 1: CAPTURE THE SEARCH JSON
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        search_res = requests.get(search_url, timeout=10).json()
        
        if 'items' not in search_res or not search_res['items']:
            return None
        
        # Extract the Key ID
        player_id = search_res['items'][0]['id']

        # STEP 2: CAPTURE THE GAMELOG JSON
        log_url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        log_res = requests.get(log_url, timeout=10).json()
        
        # Pull the 'Labels' (Headers) and 'Events' (Last games)
        labels = log_res.get('labels', [])
        events = log_res.get('events', [])[:10]
        
        if not labels or not events:
            return None

        # STEP 3: MAP THE STATS DYNAMICALLY
        # This finds exactly where PTS, REB, etc., are located in the list
        idx = {
            'pts': labels.index('PTS') if 'PTS' in labels else None,
            'reb': labels.index('REB') if 'REB' in labels else None,
            'ast': labels.index('AST') if 'AST' in labels else None,
            'tpm': labels.index('3PM') if '3PM' in labels else None
        }

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        
        for event in events:
            stats = event.get('stats', [])
            # We check the mapped index and compare to our targets
            if idx['pts'] is not None and float(stats[idx['pts']]) >= TARGETS['pts']: hits['pts'] += 1
            if idx['reb'] is not None and float(stats[idx['reb']]) >= TARGETS['reb']: hits['reb'] += 1
            if idx['ast'] is not None and float(stats[idx['ast']]) >= TARGETS['ast']: hits['ast'] += 1
            if idx['tpm'] is not None and float(stats[idx['tpm']]) >= TARGETS['tpm']: hits['tpm'] += 1

        # Calculate the percentage for the dashboard
        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(events)) * 100),
            "reb_heat": int((hits['reb'] / len(events)) * 100),
            "ast_heat": int((hits['ast'] / len(events)) * 100),
            "tpm_heat": int((hits['tpm'] / len(events)) * 100),
            "last_game": f"{events[0]['gameDate'][:10]}"
        }
    except Exception as e:
        print(f"⚠️ Failed {player_name}: {e}")
        return None

def main():
    player_data = []
    # Read your .txt file with the 114+ players
    try:
        with open('nba-streaks/players.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ Could not find players.txt")
        return

    print(f"🏀 Starting sync for {len(lines)} athletes...")

    for line in lines:
        parts = line.split()
        team_code = parts[-1]
        player_name = " ".join(parts[:-1])
        
        stats = get_player_stats(player_name, team_code)
        if stats:
            player_data.append(stats)
            print(f"✅ {player_name} synced.")
        
        time.sleep(0.7) # Safety delay

    # Save the final capture to your JSON file
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    
    print(f"🚀 SUCCESS: {len(player_data)} players processed.")

if __name__ == "__main__":
    main()
