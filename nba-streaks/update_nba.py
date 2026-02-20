def get_player_stats(player_name, team_code):
    try:
        # 1. Search for Player ID
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={player_name.replace(' ', '%20')}&limit=1&type=player"
        res = requests.get(search_url, timeout=10).json()
        if 'items' not in res or not res['items']: return None
        p_id = res['items'][0]['id']
        
        # 2. Fetch Gamelog
        url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/athletes/{p_id}/gamelog"
        data = requests.get(url, timeout=10).json()

        # 3. UNIVERSAL PATH FINDER: Check all possible locations for game lists
        # ESPN 2026 uses 'regularSeason' -> 'groups' -> 'entries'
        entries = []
        if 'regularSeason' in data:
            # New 2026 nested structure
            groups = data['regularSeason'].get('groups', [])
            for group in groups:
                entries.extend(group.get('entries', []))
        
        # Fallback for older API versions or different season phases
        if not entries:
            entries = data.get('season', {}).get('entries', [])
        if not entries:
            entries = data.get('entries', [])

        if not entries:
            print(f"⚠️ Path Error for {player_name} (ID: {p_id})")
            return None

        # Sort entries by date (most recent first) and take 10
        entries.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        recent_games = entries[:10]
        
        hits = {'pts': 0, 'reb': 0, 'ast': 0, 'tpm': 0}
        for game in recent_games:
            s = game.get('stats', [])
            if len(s) > 14:
                # v2 Map: 3=PTS, 10=REB, 11=AST, 14=3PM
                if safe_float(s[3]) >= TARGETS['pts']: hits['pts'] += 1
                if safe_float(s[10]) >= TARGETS['reb']: hits['reb'] += 1
                if safe_float(s[11]) >= TARGETS['ast']: hits['ast'] += 1
                if safe_float(s[14]) >= TARGETS['tpm']: hits['tpm'] += 1

        return {
            "name": player_name,
            "team_code": team_code,
            "pts_heat": int((hits['pts'] / len(recent_games)) * 100),
            "reb_heat": int((hits['reb'] / len(recent_games)) * 100),
            "ast_heat": int((hits['ast'] / len(recent_games)) * 100),
            "tpm_heat": int((hits['tpm'] / len(recent_games)) * 100),
            "last_game": recent_games[0].get('gameDate', '')[:10]
        }
    except Exception as e:
        print(f"❌ Error with {player_name}: {e}")
        return None
