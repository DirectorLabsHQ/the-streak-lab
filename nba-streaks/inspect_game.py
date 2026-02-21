import requests
import json
from datetime import datetime

def get_latest_game_id():
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={today}"
    
    data = requests.get(url).json()
    events = data.get("events", [])
    
    if not events:
        print("No games found today. Trying yesterday...")
        from datetime import timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yesterday}"
        data = requests.get(url).json()
        events = data.get("events", [])
    
    if not events:
        print("No recent games found.")
        return None
    
    return events[0]["id"]


def inspect_game(game_id):
    print(f"\nInspecting Game ID: {game_id}")
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    data = requests.get(url).json()
    
    print("\n=== TOP LEVEL KEYS ===")
    print(list(data.keys()))
    
    print("\n=== BOXSCORE KEYS ===")
    boxscore = data.get("boxscore", {})
    print(list(boxscore.keys()))
    
    print("\n=== FULL BOXSCORE STRUCTURE (FIRST 4000 CHARS) ===")
    print(json.dumps(boxscore, indent=2)[:4000])


if __name__ == "__main__":
    game_id = get_latest_game_id()
    if game_id:
        inspect_game(game_id)
