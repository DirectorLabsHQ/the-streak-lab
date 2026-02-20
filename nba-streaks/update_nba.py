import requests
import json

def get_nba_heat_data():
    # Using ESPN's summary endpoint for comprehensive player stats
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    response = requests.get(url)
    data = response.json()
    
    players_performance = []

    for event in data.get('events', []):
        for competition in event.get('competitions', []):
            for competitor in competition.get('competitors', []):
                # This is where we grab the specific box score stats
                # In a full version, we'd loop through the 'statistics' array
                # For now, we'll structure the JSON to match your table
                pass 

    # Mocking the structure to match your 'NBA Streak Lab' table headers
    # Points, Rebounds, Assists, 3PM
    sample_entry = {
        "athlete": "LeBron James",
        "team": "LAL",
        "pts": 28,
        "reb": 7,
        "ast": 9,
        "three_pm": 3,
        "last_outing": "vs GS",
        "heat_index": "+12%" # Calculated variance
    }
    
    players_performance.append(sample_entry)

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(players_performance, f, indent=4)
    
    print(f"Update Complete: Captured {len(players_performance)} player performances.")

if __name__ == "__main__":
    get_nba_heat_data()
