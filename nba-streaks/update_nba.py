import requests
import json
from datetime import datetime
import time

# Thresholds for 'Heat Index' calculation
TARGETS = {'pts': 20, 'reb': 7, 'ast': 5, 'tpm': 3}

def safe_float(val):
    """Safely convert strings to floats, handling empty or null values."""
    try:
        return float(str(val).strip()) if val else 0.0
    except:
        return 0.0

def get_player_stats(player_name, team_code):
    try:
        # 1. Search for Player ID
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        res = requests.get(search_url, timeout=10).json()
        if 'items' not in res or not res['items']:
            return None
        p_id = res['items'][0]['id']
        
        # 2. Fetch Gamelog (using the stable common/v3 endpoint)
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{p_id}/gamelog"
        data = requests.get(url, timeout=10).json()

        # 3. Dynamic Index Matching
        # ESPN's stat column order changes frequently; we find the index by label name.
        labels = data.get('labels', [])
        
        # Find the correct list index for each category
        p_idx = labels.index('PTS') if 'PTS' in labels else None
        r_idx = labels.index('REB') if 'REB' in labels else None
        a_idx = labels.index('AST') if 'AST' in labels else None
        
        # 3PM can be listed as '3PM' or '3PT'
        m_idx = None
        for label in ['3PM', '3PT']:
            if label in labels:
                m_idx = labels.index(label)
                break

        # 4. Extract Game Entries
        entries = data.get('entries', [])
        if not entries:
            # Fallback for 2026 nested season groups
            if 'season' in data:
                entries = data['season'].get('entries', [])

        if not entries:
            return None

        # Filter for games that actually happened and sort by date
        valid_games = [e for e in entries if e.get('stats')]
        valid_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_games = valid_games[:10]
        
        if not recent_games:
            return None

        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        
        for game in recent_games:
            s = game.get('stats', [])
            
            # Match stats to targets using the dynamic indices
            if p_idx is not None and safe_float(s[p_idx]) >= TARGETS['pts']: hits['pts'] += 1
            if r_idx is not None and safe_float(s[r_idx]) >= TARGETS['reb']: hits['reb'] += 1
            if a_idx is not None and safe_float(s[a_idx]) >= TARGETS['ast']: hits['ast'] += 1
            if m_idx is not None and safe_float(s[m_idx]) >= TARGETS['tpm']: hits['tpm'] += 1

        # Calculate percentages
        count = len(recent_games)
        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / count) * 100),
            "reb_heat": int((hits['reb'] / count) * 100),
            "ast_heat": int((hits['ast'] / count) * 100),
            "tpm_heat": int((hits['tpm'] / count) * 100),
            "last_game": recent_games[0].get('gameDate', '')[:10]
        }
    except Exception as e:
        # Errors usually mean the player is inactive or missing data
        return None

def main():
    player_data = []
    
    # Load player list (Format: "Nikola Jokic DEN")
    try:
        with open('nba-streaks/players.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ Error: players.txt not found.")
        return

    print(f"🏀 Syncing {len(lines)} athletes for The Streak Lab...")
    
    for line in lines:
        parts = line.split()
        if len(parts) < 2: continue
        
        team = parts[-1]
        name = " ".join(parts[:-1])
        
        stats = get_player_stats(name, team)
        if stats:
            player_data.append(stats)
            print(f"✅ {name} ({stats['pts_heat']}% PTS Heat)")
        else:
            print(f"⚠️ Skipping {name} (No data found)")
            
        # Throttling to prevent API rate limiting
        time.sleep(0.5)

    # Save to JSON
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "players": player_data
    }

    with open('nba-streaks/streak_data.json', 'w') as f:
        json.dump(output, f, indent=4)
    
    print(f"🚀 SUCCESS: {len(player_data)} players processed and saved.")

if __name__ == "__main__":
    main()
