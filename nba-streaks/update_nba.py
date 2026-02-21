import requests
import datetime
import time
import json

DAYS_BACK = 30
REQUEST_DELAY = 0.2

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# --------------------------------------------------
# GET RECENT COMPLETED GAME IDS (DEDUPED)
# --------------------------------------------------
def get_recent_game_ids():
    today = datetime.date.today()
    start = today - datetime.timedelta(days=DAYS_BACK)

    game_ids = set()

    for i in range(DAYS_BACK):
        date = start + datetime.timedelta(days=i)
        date_str = date.strftime("%Y%m%d")

        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue

            data = r.json()

            for event in data.get("events", []):
                status = event.get("status", {}).get("type", {})
                if status.get("completed") is True:
                    game_ids.add(event["id"])

        except:
            continue

        time.sleep(0.05)

    return list(game_ids)


# --------------------------------------------------
# GET PLAYER STATS FROM GAME
# --------------------------------------------------
def get_players_from_game(game_id):
    url = f"https://cdn.espn.com/core/nba/boxscore?xhr=1&gameId={game_id}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return []

        data = r.json()
    except:
        return []

    pkg = data.get("gamepackageJSON", {})

    game_date_str = (
        pkg.get("header", {})
        .get("competitions", [{}])[0]
        .get("date")
    )

    if not game_date_str:
        return []

    game_date = datetime.datetime.fromisoformat(
        game_date_str.replace("Z", "+00:00")
    )

    boxscore = pkg.get("boxscore", {})
    teams = boxscore.get("players", [])

    all_players = []

    for team in teams:
        team_code = team.get("team", {}).get("abbreviation")
        stat_groups = team.get("statistics", [])

        for group in stat_groups:
            labels = group.get("labels", [])
            athletes = group.get("athletes", [])

            # Ensure required stats exist
            required_stats = ["PTS", "REB", "AST", "3PT"]
            if not all(stat in labels for stat in required_stats):
                continue

            pts_i = labels.index("PTS")
            reb_i = labels.index("REB")
            ast_i = labels.index("AST")
            tpm_i = labels.index("3PT")

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
    print("🔎 Pulling recent completed games...")
    game_ids = get_recent_game_ids()
    print(f"✅ Found {len(game_ids)} completed games")

    all_players = {}

    for gid in game_ids:
        players = get_players_from_game(gid)

        for p in players:
            key = f"{p['name']}_{p['team_code']}"  # avoids name collision

            if key not in all_players:
                all_players[key] = {
                    "name": p["name"],
                    "team_code": p["team_code"],
                    "games": []
                }

            all_players[key]["games"].append(p)

        time.sleep(REQUEST_DELAY)

    output_players = []

    for data in all_players.values():
        games = data["games"]

        if len(games) < 5:
            continue

        # True chronological sort
        games_sorted = sorted(games, key=lambda x: x["date"])
        last10 = games_sorted[-10:]

        total_games = len(last10)

        pts_hits = sum(g["PTS"] >= 20 for g in last10)
        reb_hits = sum(g["REB"] >= 7 for g in last10)
        ast_hits = sum(g["AST"] >= 5 for g in last10)
        tpm_hits = sum(g["3PM"] >= 3 for g in last10)

        last_game = last10[-1]

        output_players.append({
            "name": data["name"],
            "team_code": data["team_code"],
            "games_used": total_games,
            "pts_heat": int((pts_hits / total_games) * 100),
            "reb_heat": int((reb_hits / total_games) * 100),
            "ast_heat": int((ast_hits / total_games) * 100),
            "tpm_heat": int((tpm_hits / total_games) * 100),
            "last_game": f"{last_game['PTS']} PTS, {last_game['REB']} REB, {last_game['AST']} AST"
        })

    # Sort by scoring heat descending
    output_players.sort(key=lambda x: x["pts_heat"], reverse=True)

    final_data = {
        "last_updated": datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p EST"),
        "players": output_players
    }

    with open("streak_data.json", "w") as f:
        json.dump(final_data, f, indent=2)

    print(f"🔥 streak_data.json updated successfully ({len(output_players)} players)")


if __name__ == "__main__":
    main()
