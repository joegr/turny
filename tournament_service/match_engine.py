import json
import random
from typing import List, Dict, Optional, Tuple


class MatchEngine:
    def __init__(self, redis_client, tournament_id: str):
        self.redis = redis_client
        self.tournament_id = tournament_id
        self.prefix = f"t:{tournament_id}:"
    
    def _key(self, name: str) -> str:
        return f"{self.prefix}{name}"
    
    def get_teams(self) -> Dict:
        data = self.redis.get(self._key("teams"))
        return json.loads(data) if data else {}
    
    def set_teams(self, teams: Dict):
        self.redis.set(self._key("teams"), json.dumps(teams))
    
    def get_matches(self) -> List[Dict]:
        data = self.redis.get(self._key("matches"))
        return json.loads(data) if data else []
    
    def set_matches(self, matches: List[Dict]):
        self.redis.set(self._key("matches"), json.dumps(matches))
    
    def get_current_round(self) -> int:
        data = self.redis.get(self._key("current_round"))
        return int(data) if data else 0
    
    def set_current_round(self, round_num: int):
        self.redis.set(self._key("current_round"), str(round_num))
    
    def register_team(self, team_id: str, name: str, captain: str) -> str:
        teams = self.get_teams()
        teams[team_id] = {
            'name': name,
            'captain': captain,
            'wins': 0,
            'losses': 0
        }
        self.set_teams(teams)
        return team_id
    
    def unregister_team(self, team_id: str) -> bool:
        teams = self.get_teams()
        if team_id in teams:
            del teams[team_id]
            self.set_teams(teams)
            return True
        return False
    
    def create_single_elimination_matches(self, round_num: int = 1) -> List[Dict]:
        teams = self.get_teams()
        team_ids = list(teams.keys())
        
        team_ids.sort(key=lambda tid: (
            teams[tid].get('wins', 0) * 100 - teams[tid].get('losses', 0) * 50
        ), reverse=True)
        
        matches = []
        for i in range(0, len(team_ids), 2):
            if i + 1 < len(team_ids):
                match_id = f"r{round_num}_m{len(matches) + 1}"
                matches.append({
                    'id': match_id,
                    'team1': team_ids[i],
                    'team2': team_ids[i + 1],
                    'winner': None,
                    'status': 'pending',
                    'round': round_num
                })
        
        self.set_matches(matches)
        self.set_current_round(round_num)
        return matches
    
    def create_round_robin_schedule(self) -> List[List[Dict]]:
        teams = self.get_teams()
        team_ids = list(teams.keys())
        n = len(team_ids)
        
        if n < 2:
            return []
        
        if n % 2 == 1:
            team_ids.append(None)
            n += 1
        
        all_rounds = []
        
        for round_num in range(n - 1):
            round_matches = []
            for i in range(n // 2):
                team1 = team_ids[i]
                team2 = team_ids[n - 1 - i]
                
                if team1 is not None and team2 is not None:
                    match_id = f"r{round_num + 1}_m{len(round_matches) + 1}"
                    round_matches.append({
                        'id': match_id,
                        'team1': team1,
                        'team2': team2,
                        'winner': None,
                        'status': 'pending',
                        'round': round_num + 1
                    })
            
            all_rounds.append(round_matches)
            team_ids = [team_ids[0]] + [team_ids[-1]] + team_ids[1:-1]
        
        self.redis.set(self._key("all_rounds"), json.dumps(all_rounds))
        
        if all_rounds:
            self.set_matches(all_rounds[0])
            self.set_current_round(1)
        
        return all_rounds
    
    def record_result(self, match_id: str, winner_id: str) -> Tuple[bool, str]:
        matches = self.get_matches()
        teams = self.get_teams()
        
        for match in matches:
            if match['id'] == match_id:
                if match['status'] != 'pending':
                    return False, f"Match {match_id} is not pending"
                
                if winner_id not in [match['team1'], match['team2']]:
                    return False, f"Winner {winner_id} is not in this match"
                
                match['winner'] = winner_id
                match['status'] = 'completed'
                
                teams[winner_id]['wins'] += 1
                loser_id = match['team2'] if match['team1'] == winner_id else match['team1']
                teams[loser_id]['losses'] += 1
                
                self.set_matches(matches)
                self.set_teams(teams)
                
                return True, f"Recorded {winner_id} as winner of {match_id}"
        
        return False, f"Match {match_id} not found"
    
    def all_matches_complete(self) -> bool:
        matches = self.get_matches()
        return all(m['status'] in ['completed', 'abandoned'] for m in matches)
    
    def get_winners(self) -> List[str]:
        matches = self.get_matches()
        return [m['winner'] for m in matches if m.get('winner')]
    
    def advance_single_elimination(self) -> Tuple[bool, Optional[List[Dict]]]:
        if not self.all_matches_complete():
            return False, None
        
        winners = self.get_winners()
        
        if len(winners) <= 1:
            return True, None
        
        next_round = self.get_current_round() + 1
        
        matches = []
        for i in range(0, len(winners), 2):
            if i + 1 < len(winners):
                match_id = f"r{next_round}_m{len(matches) + 1}"
                matches.append({
                    'id': match_id,
                    'team1': winners[i],
                    'team2': winners[i + 1],
                    'winner': None,
                    'status': 'pending',
                    'round': next_round
                })
        
        self.set_matches(matches)
        self.set_current_round(next_round)
        
        return False, matches
    
    def advance_round_robin(self) -> Tuple[bool, Optional[List[Dict]]]:
        if not self.all_matches_complete():
            return False, None
        
        all_rounds_data = self.redis.get(self._key("all_rounds"))
        if not all_rounds_data:
            return True, None
        
        all_rounds = json.loads(all_rounds_data)
        current_round = self.get_current_round()
        
        if current_round >= len(all_rounds):
            return True, None
        
        next_round_matches = all_rounds[current_round]
        self.set_matches(next_round_matches)
        self.set_current_round(current_round + 1)
        
        return False, next_round_matches
    
    def get_standings(self) -> List[Dict]:
        teams = self.get_teams()
        standings = []
        
        for team_id, team_data in teams.items():
            wins = team_data.get('wins', 0)
            losses = team_data.get('losses', 0)
            total = wins + losses
            win_rate = (wins / total * 100) if total > 0 else 0
            
            standings.append({
                'team_id': team_id,
                'name': team_data.get('name', 'Unknown'),
                'captain': team_data.get('captain', 'Unknown'),
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 1)
            })
        
        standings.sort(key=lambda x: (x['wins'], -x['losses']), reverse=True)
        
        for i, s in enumerate(standings):
            s['rank'] = i + 1
        
        return standings
    
    def get_tournament_winner(self) -> Optional[str]:
        standings = self.get_standings()
        return standings[0]['team_id'] if standings else None
    
    def cleanup(self):
        keys = [
            self._key("teams"),
            self._key("matches"),
            self._key("current_round"),
            self._key("all_rounds"),
            self._key("state"),
            self._key("config"),
        ]
        for key in keys:
            self.redis.delete(key)
