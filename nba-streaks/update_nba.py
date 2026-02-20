import requests
import json
from datetime import datetime

def get_nba_stats():
    # Makes the script look like a browser to avoid being flagged as a bot
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # 1. Fetch today's scoreboard to get current Game IDs
    score_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    
    try:
        response = requests.get(score_url, headers=headers)
        data = response.json()
    except Exception as e:
        print(f"Error fetching scoreboard: {e}")
        return

    streak_list = []
    
    # 2. Loop through each game to get the player boxscore
    for event in data.get('events', []):
        game_id = event['id']
        summary_url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
        
        try:
            game_data = requests.get(summary_url, headers=headers).json()
            
            # Navigate to boxscore -> players -> statistics
            # statistics[0] is usually the 'Box Score' category
            for team_box in game_data.get('boxscore', {}).get('players', []):
                team_name = team_box['team']['displayName']
                
                for player in team_box['statistics'][0]['athletes']:
                    name = player['athlete']['displayName']
                    stats_list = player['stats']
                    
                    if stats_list:
                        # Index -1 is consistently Points (PTS) in ESPN's JSON format
                        pts = int(stats_list[-1]) if stats_list[-1].isdigit() else 0
                        
                        # LOGIC: Only save players who scored 25+ points
                        if pts >= 25:
                            streak_list.append({
                                "player": name,
                                "team": team_name,
                                "points": pts,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
        except Exception:
            # Skip games that are either postponed or haven't started yet
            continue 

    # 3. Save as 'nba_live_streaks.json' for your legacy site to read
    with open('streak_data.json', 'w') as f:
        json.dump(streak_list, f, indent=2)
    
    print(f"Update Complete: Captured {len(streak_list)} player performances.")

if __name__ == "__main__":
    get_nba_stats()
