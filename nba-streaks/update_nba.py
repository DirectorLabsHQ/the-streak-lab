import requests
import datetime
import time

DAYS_BACK = 21


# --------------------------------------------------
# GET RECENT COMPLETED REGULAR SEASON GAME IDS
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
            status = event.get("status", {}).get("type", {})
            season = event.get("season", {})

            # ✅ Only completed regular season games
            if (
                status.get("completed") and
                season.get("type") == 2  # 2 = Regular season
            ):
                game_ids.append(event["id"])

    return game_ids


# --------------------------------------------------
# GET PLAYER STATS FROM A SINGLE GAME
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

            labels = group.get("labels", [])
            athletes = group.get("athletes", [])

            # Dynamically find stat columns
            try:
                pts_index = labels.index("PTS")
                reb_index = labels.index("REB")
                ast_index = labels.index("AST")
            except ValueError:
                continue

            for athlete in athletes:
                name = athlete.get("athlete", {}).get("displayName")
                stats = athlete.get("stats", [])

                if not name or len(stats) <= max(pts_index, reb_index, ast_index):
                    continue

                try:
                    player_data = {
                        "name": name,
                        "PTS": int(stats[pts_index]),
                        "REB": int(stats[reb_index]),
                        "AST": int(stats[ast_index]),
                    }
                except ValueError:
                    continue  # Skip DNP or malformed rows

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

        time.sleep(0.25)  # Prevent rate limiting

    print(f"🔥 Calculating Heat for {len(all_players)} players...\n")

    sorted_players = sorted(
        all_players.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    for name, games in sorted_players[:20]:

        if not games:
            print(f"⚠️ {name} (No games found)")
            continue

        avg_pts = sum(g["PTS"] for g in games) / len(games)
        avg_reb = sum(g["REB"] for g in games) / len(games)
        avg_ast = sum(g["AST"] for g in games) / len(games)

        print(
            f"✅ {name} — "
            f"{len(games)} games — "
            f"{avg_pts:.1f} PPG / "
            f"{avg_reb:.1f} RPG / "
            f"{avg_ast:.1f} APG"
        )


if __name__ == "__main__":
    main()
