import requests
import datetime
import time
import json

DAYS_BACK = 30
REQUEST_DELAY = 0.25 # Slightly slower to prevent IP blocks
HEADERS = {"User-Agent": "Mozilla/5.0"}
TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def get_recent_game_ids():
    today = datetime.date.today()
    start = today - datetime.timedelta(days=DAYS_BACK)
    game_ids = set()

    for i in range(DAYS_BACK):
        date_str = (start + datetime.timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                for event in r.json().get("events", []):
                    if event.get("status", {}).get("type", {}).get("completed"):
                        game_ids.add(event["id"])
        except: continue
        time.sleep(0.1)
    return list(game_ids)

def get_players_from_game(game_id):
    url = f"https://cdn.espn.com/core/nba/boxscore?xhr=1&gameId={game_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        pkg = data.get("gamepackageJSON", {})
        game_date_str = pkg.get("header", {}).get("competitions", [{}])[0].get("date")
        game_date = datetime.datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
        
        boxscore = pkg.get("boxscore", {})
        teams = boxscore.get("players", [])
        all_players_in_game = []

        for team in teams:
            team_code = team.get("team", {}).get("abbreviation")
            for group in team.get("statistics", []):
                labels = group.get("labels", [])
                # ESPN sometimes uses '3PT' or '3PM'
                tpm_label = next((l for l in labels if l in ["3PT", "3PM", "3P"]), None)
                
                if not all(x in labels for x in ["PTS", "REB", "AST"]) or not tpm_label:
                    continue

                pts_i, reb_i, ast_i, tpm_i = labels.index("PTS"), labels.index("REB"), labels.index("AST"), labels.index(tpm_label)

                for athlete in group.get("athletes", []):
                    stats = athlete.get("stats", [])
                    if not stats or len(stats) <= max(pts_i, reb_i, ast_i, tpm_i): continue
                    
                    try:
                        # Handle "3-5" format or plain "3" format
                        tpm_val = str(stats[tpm_i]).split("-")[0]
                        all_players_in_game.append({
                            "name": athlete.get("athlete", {}).get("displayName"),
                            "team_code": team_code,
                            "date": game_date,
                            "PTS": int(stats[pts_i]),
                            "REB": int(stats[reb_i]),
                            "AST": int(stats[ast_i]),
                            "3PM": int(tpm_val)
                        })
                    except: continue
        return all_players_in_game
    except: return []

def main():
    print("🔎 Scanning NBA Schedule...")
    game_ids = get_recent_game_ids()
    all_players = {}

    print(f"🏀 Scraping {len(game_ids)} Boxscores...")
    for gid in game_ids:
        for p in get_players_from_game(gid):
            key = f"{p['name']}_{p['team_code']}"
            if key not in all_players:
                all_players[key] = {"name": p["name"], "team_code": p["team_code"], "games": []}
            all_players[key]["games"].append(p)
        print(f"✔️ Game {gid} processed", end="\r")
        time.sleep(REQUEST_DELAY)

    output_players = []
    for data in all_players.values():
        if len(data["games"]) < 3: continue # Filter out benchwarmers
        
        # Chronological sort
        sorted_games = sorted(data["games"], key=lambda x: x["date"])[-10:]
        count = len(sorted_games)
        
        output_players.append({
            "name": data["name"],
            "team_code": data["team_code"],
            "pts_heat": int((sum(g["PTS"] >= TARGETS['pts'] for g in sorted_games) / count) * 100),
            "reb_heat": int((sum(g["REB"] >= TARGETS['reb'] for g in sorted_games) / count) * 100),
            "ast_heat": int((sum(g["AST"] >= TARGETS['ast'] for g in sorted_games) / count) * 100),
            "tpm_heat": int((sum(g["3PM"] >= TARGETS['tpm'] for g in sorted_games) / count) * 100),
            "last_game": f"{sorted_games[-1]['PTS']} PTS, {sorted_games[-1]['REB']} REB, {sorted_games[-1]['AST']} AST"
        })

    output_players.sort(key=lambda x: x["pts_heat"], reverse=True)
    
    # Save to your specific site directory
    with open("nba-streaks/streak_data.json", "w") as f:
        json.dump({
            "last_updated": datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p"),
            "players": output_players
        }, f, indent=2)

    print(f"\n🚀 SUCCESS: {len(output_players)} players synced to Streak Lab.")

if __name__ == "__main__":
    main()
