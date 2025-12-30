import json
import random
from typing import List, Dict, Optional, Tuple
from sqlalchemy import or_
from .models import db, Match, Team, Tournament

class MatchEngine:
    def __init__(self, tournament_id: str):
        self.tournament_id = tournament_id
        # We need the numeric ID for foreign keys, so we fetch it once or per query
        self.t_record = Tournament.query.filter_by(tournament_id=tournament_id).first()
        if not self.t_record:
            raise ValueError(f"Tournament {tournament_id} not found")
        self.db_id = self.t_record.id
    
    def get_teams(self) -> Dict:
        teams = Team.query.filter_by(tournament_id=self.db_id).all()
        return {t.team_id: t.to_dict() for t in teams}
    
    def register_team(self, team_id: str, name: str, captain: str) -> str:
        team = Team(
            team_id=team_id,
            tournament_id=self.db_id,
            name=name,
            captain=captain
        )
        db.session.add(team)
        db.session.commit()
        return team_id
    
    def unregister_team(self, team_id: str) -> bool:
        team = Team.query.filter_by(tournament_id=self.db_id, team_id=team_id).first()
        if team:
            db.session.delete(team)
            db.session.commit()
            return True
        return False
    
    def get_matches(self) -> List[Dict]:
        matches = Match.query.filter_by(tournament_id=self.db_id).order_by(Match.id).all()
        return [m.to_dict() for m in matches]
    
    def get_current_round(self) -> int:
        return self.t_record.current_round
    
    def set_current_round(self, round_num: int):
        self.t_record.current_round = round_num
        db.session.commit()
    
    def create_single_elimination_matches(self, round_num: int = 1) -> List[Dict]:
        teams = Team.query.filter_by(tournament_id=self.db_id).all()
        
        # Sort by seeding (wins/loss or random/insertion order if new)
        # For new tournament, simple random or insertion order
        teams.sort(key=lambda t: (t.wins * 100 - t.losses * 50), reverse=True)
        
        matches_created = []
        for i in range(0, len(teams), 2):
            if i + 1 < len(teams):
                match_id = f"r{round_num}_m{len(matches_created) + 1}"
                match = Match(
                    match_id=match_id,
                    tournament_id=self.db_id,
                    round_num=round_num,
                    team1_id=teams[i].team_id,
                    team2_id=teams[i+1].team_id,
                    status='pending'
                )
                db.session.add(match)
                matches_created.append(match)
        
        self.t_record.current_round = round_num
        db.session.commit()
        
        return [m.to_dict() for m in matches_created]
    
    def create_round_robin_schedule(self) -> List[List[Dict]]:
        # Simplified: just create round 1 for now, or all rounds?
        # For MVP, let's just do single round robin logic generation but only save current round matches?
        # Or generate all and store them with different round numbers.
        
        teams = Team.query.filter_by(tournament_id=self.db_id).all()
        team_ids = [t.team_id for t in teams]
        n = len(team_ids)
        
        if n < 2:
            return []
        
        if n % 2 == 1:
            team_ids.append(None)
            n += 1
        
        all_rounds_matches = []
        
        # Circle method
        for round_idx in range(n - 1):
            round_num = round_idx + 1
            round_matches = []
            for i in range(n // 2):
                t1 = team_ids[i]
                t2 = team_ids[n - 1 - i]
                
                if t1 is not None and t2 is not None:
                    match_id = f"r{round_num}_m{len(round_matches) + 1}"
                    match = Match(
                        match_id=match_id,
                        tournament_id=self.db_id,
                        round_num=round_num,
                        team1_id=t1,
                        team2_id=t2,
                        status='pending'
                    )
                    db.session.add(match)
                    round_matches.append(match)
            
            all_rounds_matches.append(round_matches)
            team_ids = [team_ids[0]] + [team_ids[-1]] + team_ids[1:-1]
        
        # For MVP simple flow, we assume round 1 starts now
        self.t_record.current_round = 1
        db.session.commit()
        
        # Return nested structure for compatibility
        return [[m.to_dict() for m in rnd] for rnd in all_rounds_matches]

    def record_result(self, match_id: str, winner_id: str) -> Tuple[bool, str]:
        match = Match.query.filter_by(tournament_id=self.db_id, match_id=match_id).first()
        if not match:
            return False, f"Match {match_id} not found"
        
        if match.status != 'pending':
            return False, f"Match {match_id} is not pending"
        
        if winner_id not in [match.team1_id, match.team2_id]:
            return False, f"Winner {winner_id} is not in this match"
        
        match.winner_id = winner_id
        match.status = 'completed'
        
        # Update team stats
        winner = Team.query.filter_by(tournament_id=self.db_id, team_id=winner_id).first()
        if winner:
            winner.wins += 1
            
        loser_id = match.team2_id if match.team1_id == winner_id else match.team1_id
        loser = Team.query.filter_by(tournament_id=self.db_id, team_id=loser_id).first()
        if loser:
            loser.losses += 1
            
        db.session.commit()
        return True, f"Recorded {winner_id} as winner of {match_id}"

    def all_matches_complete(self) -> bool:
        # Check if there are any pending matches for the current round
        pending = Match.query.filter_by(
            tournament_id=self.db_id, 
            round_num=self.t_record.current_round,
            status='pending'
        ).count()
        return pending == 0

    def get_tournament_winner(self) -> Optional[str]:
        # Simple standing based winner
        standings = self.get_standings()
        return standings[0]['team_id'] if standings else None

    def get_standings(self) -> List[Dict]:
        teams = Team.query.filter_by(tournament_id=self.db_id).all()
        standings = []
        for t in teams:
            total = t.wins + t.losses
            win_rate = (t.wins / total * 100) if total > 0 else 0
            standings.append({
                'team_id': t.team_id,
                'name': t.name,
                'captain': t.captain,
                'wins': t.wins,
                'losses': t.losses,
                'win_rate': round(win_rate, 1)
            })
        
        # Sort by wins desc, then losses asc
        standings.sort(key=lambda x: (x['wins'], -x['losses']), reverse=True)
        
        for i, s in enumerate(standings):
            s['rank'] = i + 1
            
        return standings

    def advance_single_elimination(self) -> Tuple[bool, Optional[List[Dict]]]:
        if not self.all_matches_complete():
            return False, None
            
        # Get winners from current round matches
        current_matches = Match.query.filter_by(
            tournament_id=self.db_id,
            round_num=self.t_record.current_round
        ).all()
        
        winners_ids = [m.winner_id for m in current_matches if m.winner_id]
        
        if len(winners_ids) <= 1:
            return True, None
            
        next_round = self.t_record.current_round + 1
        matches_created = []
        
        for i in range(0, len(winners_ids), 2):
            if i + 1 < len(winners_ids):
                match_id = f"r{next_round}_m{len(matches_created) + 1}"
                match = Match(
                    match_id=match_id,
                    tournament_id=self.db_id,
                    round_num=next_round,
                    team1_id=winners_ids[i],
                    team2_id=winners_ids[i+1],
                    status='pending'
                )
                db.session.add(match)
                matches_created.append(match)
        
        self.t_record.current_round = next_round
        db.session.commit()
        
        return False, [m.to_dict() for m in matches_created]

    def advance_round_robin(self) -> Tuple[bool, Optional[List[Dict]]]:
        if not self.all_matches_complete():
            return False, None
        
        # In round robin, matches are pre-generated or we just increment round.
        # Since we generated all rounds at start (or we should have), we just check if next round exists
        next_round = self.t_record.current_round + 1
        
        next_matches = Match.query.filter_by(
            tournament_id=self.db_id,
            round_num=next_round
        ).all()
        
        if not next_matches:
            # No more matches, we are done
            return True, None
            
        self.t_record.current_round = next_round
        db.session.commit()
        
        return False, [m.to_dict() for m in next_matches]
