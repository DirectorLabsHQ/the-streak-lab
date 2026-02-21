import requests
import json
from datetime import datetime, timedelta

BASE_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
BASE_BOXSCORE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/boxscore"

OUTPUT_FILE = "nba-streaks/nba_games.json"


def get_recent_game_ids(days_back=3):
    game_ids = []

    for i in range(days_back):
        date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y%m%d")
        url = f"{BASE_SCOREBOARD_URL}?dates={date}"

        try:
            r = requests.get(url, timeout=10)
            data = r.json()

            for event in data.get("events", []):
                game_ids.append(event["id"])

        except Exception as e:
            print(f"Error fetching scoreboard for {date}: {e}")

    return game_ids


def fetch_boxscore(game_id):
    url = f"{BASE_BOXSCORE_URL}?event={game_id}"

    try:
        r = requests.get(url, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Error fetching boxscore {game_id}: {e}")
        return None


def parse_players_from_boxscore(boxscore_json):
    players = []

    if not boxscore_json:
        return players

    teams = boxscore_json.get("players", [])

    for team in teams:
        team_name = team.get("team", {}).get("displayName", "Unknown")

        for stat_group in team.get("statistics", []):
            for athlete in stat_group.get("athletes", []):
                player_name = athlete.get("athlete", {}).get("displayName")

                stats = athlete.get("stats", [])

                players.append({
                    "player": player_name,
                    "team": team_name,
                    "stats": stats
                })

    return players


def load_existing_data():
    try:
        with open(OUTPUT_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_data(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main():
    print("Fetching recent NBA games...")

    existing_data = load_existing_data()
    game_ids = get_recent_game_ids(days_back=3)

    for gid in game_ids:
        print(f"Processing game {gid}")

        boxscore = fetch_boxscore(gid)
        players = parse_players_from_boxscore(boxscore)

        if players:
            existing_data[gid] = players
            print(f"  Found {len(players)} players")
        else:
            print("  No players found")

    save_data(existing_data)
    print("Update complete.")


if __name__ == "__main__":
    main()
