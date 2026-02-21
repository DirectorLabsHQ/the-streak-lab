import requests
import datetime
import time

DAYS_BACK = 21


# --------------------------------------------------
# GET RECENT GAME IDS
# --------------------------------------------------
def get_recent_game_ids():
    today = datetime.date.today()
    start = today - datetime.timedelta(days=DAYS_BACK)

    game_ids = []

    print("📡 Gathering game IDs for last 21 days...")

    for i in range(DAYS_BACK):
        date = start + datetime.timedelta(days=i)
        date_str = date.strftime("%Y%m%d")

        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
        r = requests.get(url)

        if r.status_code != 200:
            continue

        data = r.json()

        for event in data.get("events", []):
            # Only completed games
            if event.get("status", {}).get("type", {}).get("completed"):
                game_ids.append(event["id"])

    return game_ids


# --------------------------------------------------
# GET PLAYER STATS FROM A GAME
# --------------------------------------------------
def get_players_from_game(game_id):
    url = f"https://cdn.espn.com/core/nba/boxscore?xhr=1&gameId={game_id}"
    r = requests.get(url)

    if r.status_code != 200:
        return []

    data = r.json()
    pkg = data.get("gamepackageJSON", {})

    boxscore = pkg.get("boxscore", {})
    players = boxscore.get("players", [])

    all_players = []

    for team in players:
        for group in team.get("statistics", []):
            for athlete in group.get("athletes", []):
                name = athlete.get("athlete", {}).get("displayName")

                stats = athlete.get("stats", [])

                # ESPN stat order:
                # 0 MIN
                # 1 FG
                # 2 3PT
                # 3 FT
                # 4 OREB
                # 5 DREB
                # 6 REB
                # 7 AST
                # 8 STL
                # 9 BLK
                # 10 TO
                # 11 PF
                # 12 PTS

                if len(stats) >= 13:
                    player_data = {
                        "name": name,
                        "PTS": int(stats[12]) if stats[12].isdigit() else 0,
                        "REB": int(stats[6]) if stats[6].isdigit() else 0,
                        "AST": int(stats[7]) if stats[7].isdigit() else 0,
                    }

                    all_players.append(player_data)

    return all_players


# --------------------------------------------------
# MAIN HEAT ENGINE
# --------------------------------------------------
def main():
    game_ids = get_recent_game_ids()

    print(f"📦 Downloading {len(game_ids)} boxscores...\n")

    all_players = {}

    for gid in game_ids:
        players = get_players_from_game(gid)

        for p in players:
            name = p["name"]

            if name not in all_players:
                all_players[name] = []

            all_players[name].append(p)

        time.sleep(0.3)  # prevent rate limiting

    print(f"🔥 Calculating Heat for {len(all_players)} players...\n")

    for name, games in list(all_players.items())[:12]:  # limit output
        if not games:
            print(f"⚠️ {name} (No games found)")
            continue

        avg_pts = sum(g["PTS"] for g in games) / len(games)

        print(f"✅ {name} — {len(games)} games — {avg_pts:.1f} PPG")


if __name__ == "__main__":
    main()
