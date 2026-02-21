import requests
import datetime
import time
import json

DAYS_BACK = 30


# --------------------------------------------------
# GET RECENT COMPLETED GAME IDS
# --------------------------------------------------
def get_recent_game_ids():
    today = datetime.date.today()
    start = today - datetime.timedelta(days=DAYS_BACK)

    game_ids = []

    for i in range(DAYS_BACK):
        date = start + datetime.timedelta(days=i)
        date_str = date.strftime("%Y%m%d")

        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
        r = requests.get(url)

        if r.status_code != 200:
            continue

        data = r.json()

        for event in data.get("events", []):
            if event.get("status", {}).get("type", {}).get("completed"):
                game_ids.append(event["id"])

    return game_ids


# --------------------------------------------------
# GET PLAYER STATS FROM GAME
# --------------------------------------------------
def get_players_from_game(game_id):
    url = f"https://cdn.espn.com/core/nba/boxscore?xhr=1&gameId={game_id}"
    r = requests.get(url)

    if r.status_code != 200:
        return []

    data = r.json()
    pkg = data.get("gamepackageJSON", {})

    # 🔥 Extract true game date
    game_date_str = pkg.get("header", {}).get("competitions", [{}])[0].get("date")
    if not game_date_str:
        return []

    game_date = datetime.datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))

    boxscore = pkg.get("boxscore", {})
    players = boxscore.get("players", [])

    all_players = []

    for team in players:
        team_code = team.get("team", {}).get("abbreviation")

        for group in team.get("statistics", []):
            labels = group.get("labels", [])
            athletes = group.get("athletes", [])

            try:
                pts_i = labels.index("PTS")
                reb_i = labels.index("REB")
                ast_i = labels.index("AST")
                tpm_i = labels.index("3PT")
            except ValueError:
                continue

            for athlete in athletes:
                name = athlete.get("athlete", {}).get("displayName")
                stats = athlete.get("stats", [])

                if not name or len(stats) <= max(pts_i, reb_i, ast_i, tpm_i):
                    continue

                try:
                    pts = int(stats[pts_i])
                    reb = int(stats[reb_i])
                    ast = int(stats[ast_i])
                    tpm = int(stats[tpm_i].split("-")[0])
                except:
                    continue

                all_players.append({
                    "name": name,
                    "team_code": team_code,
                    "date": game_date,
                    "PTS": pts,
                    "REB": reb,
                    "AST": ast,
                    "3PM": tpm
                })

    return all_players


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    game_ids = get_recent_game_ids()
    all_players = {}

    for gid in game_ids:
        players = get_players_from_game(gid)

        for p in players:
            name = p["name"]

            if name not in all_players:
                all_players[name] = {
                    "team_code": p["team_code"],
                    "games": []
                }

            all_players[name]["games"].append(p)

        time.sleep(0.25)

    output_players = []

    for name, data in all_players.items():
        games = data["games"]

        if len(games) < 5:
            continue

        # 🔥 True chronological sort
        games_sorted = sorted(games, key=lambda x: x["date"])

        last10 = games_sorted[-10:]

        pts_hits = sum(1 for g in last10 if g["PTS"] >= 20)
        reb_hits = sum(1 for g in last10 if g["REB"] >= 7)
        ast_hits = sum(1 for g in last10 if g["AST"] >= 5)
        tpm_hits = sum(1 for g in last10 if g["3PM"] >= 3)

        last_game = last10[-1]

        output_players.append({
            "name": name,
            "team_code": data["team_code"],
            "pts_heat": int((pts_hits / len(last10)) * 100),
            "reb_heat": int((reb_hits / len(last10)) * 100),
            "ast_heat": int((ast_hits / len(last10)) * 100),
            "tpm_heat": int((tpm_hits / len(last10)) * 100),
            "last_game": f"{last_game['PTS']} PTS, {last_game['REB']} REB, {last_game['AST']} AST"
        })

    final_data = {
        "last_updated": datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p EST"),
        "players": output_players
    }

    with open("streak_data.json", "w") as f:
        json.dump(final_data, f, indent=2)

    print("🔥 streak_data.json updated successfully")


if __name__ == "__main__":
    main()
