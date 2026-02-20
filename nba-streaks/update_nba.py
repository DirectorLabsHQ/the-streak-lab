import requests
import json
from datetime import datetime
import time

# Benchmarks for Heat Index
TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

# YOUR HARDCODED PLAYER LIST (Extracted from players.txt)
PLAYER_LIST = [
    "Stephen Curry GSW", "Jonathan Kuminga ATL", "Buddy Hield ATL", "Brandin Podziemski GSW",
    "Trayce Jackson-Davis GSW", "Moses Moody GSW", "De'Anthony Melton GSW", "Kyle Anderson MIA",
    "Nikola Jokic DEN", "Luka Doncic DAL", "Giannis Antetokounmpo MIL", "Shai Gilgeous-Alexander OKC",
    "Kevin Durant PHX", "LeBron James LAL", "Anthony Davis WAS", "Joel Embiid PHI", "Tyrese Maxey PHI",
    "Devin Booker PHX", "Anthony Edwards MIN", "Jalen Brunson NYK", "Donovan Mitchell CLE",
    "Tyrese Haliburton IND", "De'Aaron Fox SAS", "Domantas Sabonis SAC", "Ja Morant MEM",
    "Victor Wembanyama SAS", "Chet Holmgren OKC", "Jalen Williams OKC", "Jalen Johnson ATL",
    "Trae Young WAS", "Zion Williamson NOP", "Brandon Ingram NOP", "CJ McCollum NOP",
    "Alperen Sengun HOU", "Fred VanVleet HOU", "Jalen Green HOU", "Paolo Banchero ORL",
    "Franz Wagner ORL", "Jalen Suggs ORL", "Cade Cunningham DET", "Jaden Ivey DET",
    "Lauri Markkanen UTA", "Mikal Bridges NYK", "OG Anunoby NYK", "Josh Hart NYK",
    "Jaylen Brown BOS", "Derrick White BOS", "Kristaps Porzingis GSW", "Bam Adebayo MIA",
    "Jimmy Butler GSW", "Tyler Herro MIA", "Karl-Anthony Towns NYK", "Rudy Gobert MIN",
    "Julius Randle MIN", "Naz Reid MIN", "Donte DiVincenzo MIN", "Jarrett Allen CLE",
    "Evan Mobley CLE", "Darius Garland LAC", "Myles Turner IND", "Pascal Siakam IND",
    "Coby White CHA", "Zach LaVine SAC", "Josh Giddey CHI", "Anfernee Simons POR",
    "Jerami Grant POR", "Scottie Barnes TOR", "Immanuel Quickley TOR", "RJ Barrett TOR",
    "Cam Thomas MIL", "Nic Claxton BKN", "Cameron Johnson BKN", "Jordan Poole NOP",
    "Kyle Kuzma MIL", "Bilal Coulibaly WAS", "Terry Rozier MIA", "Dejounte Murray NOP",
    "Clint Capela ATL", "Bogdan Bogdanovic ATL", "Dyson Daniels ATL", "Jalen Duren DET",
    "Ausar Thompson DET", "Keyonte George UTA", "Walker Kessler UTA", "John Collins UTA",
    "Scoot Henderson POR", "Shaedon Sharpe POR", "Amen Thompson HOU", "Jabari Smith Jr HOU",
    "Benedict Mathurin IND", "Aaron Nesmith IND", "Jaden McDaniels MIN", "Austin Reaves LAL",
    "D'Angelo Russell LAL", "Malik Monk SAC", "Herb Jones NOP", "Trey Murphy III NOP",
    "Jabari Smith Jr. HOU", "Miles Bridges CHA", "LaMelo Ball CHA", "Brandon Miller CHA",
    "Ivica Zubac LAC", "James Harden CLE", "Kawhi Leonard LAC", "Norman Powell LAC",
    "Aaron Gordon DEN", "Michael Porter Jr. BKN", "Brook Lopez LAC", "Quinten Post GSW"
]

def get_player_stats(player_name, team_code):
    try:
        # Step 1: Search for Player ID
        search_url = f"https://site.web.api.espn.com/apis/search/v2?query={player_name}&limit=1"
        res = requests.get(search_url, timeout=10).json()
        if not res.get('results'): return None
        player_id = res['results'][0]['id']

        # Step 2: Get L10 Game Logs
        log_url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/gamelog"
        logs = requests.get(log_url, timeout=10).json()
        events = logs.get('events', [])[:10]
        if not events: return None

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for event in events:
            stats = event['stats']
            if float(stats[3]) >= TARGETS['pts']: hits['pts'] += 1
            if float(stats[10]) >= TARGETS['reb']: hits['reb'] += 1
            if float(stats[11]) >= TARGETS['ast']: hits['ast'] += 1
            if float(stats[14]) >= TARGETS['tpm']: hits['tpm'] += 1

        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(events)) * 100),
            "reb_heat": int((hits['reb'] / len(events)) * 100),
            "ast_heat": int((hits['ast'] / len(events)) * 100),
            "tpm_heat": int((hits['tpm'] / len(events)) * 100),
            "last_game": f"{events[0]['gameDate'][:10]}"
        }
    except:
        return None

def main():
    player_data = []
    print(f"🏀 Starting sync for {len(PLAYER_LIST)} players...")

    for entry in PLAYER_LIST:
        parts = entry.split()
        team = parts[-1]
        name = " ".join(parts[:-1])
        
        stats = get_player_stats(name, team)
        if stats:
            player_data.append(stats)
            print(f"✅ {name} synced.")
        
        time.sleep(0.2) # Prevent ESPN rate limiting

    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    # Saves to the same folder for your GitHub Action
    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print(f"🚀 SUCCESS: {len(player_data)} players processed.")

if __name__ == "__main__":
    main()
