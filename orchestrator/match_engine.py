import json
import random
from typing import List, Dict, Optional, Tuple
from sqlalchemy import or_
from .models import db, Match, Team, Tournament, EloHistory
from .name_generator import generate_match_name
from .elo_calculator import EloCalculator
from .pubsub_manager import get_pubsub_manager

class MatchEngine:
    def __init__(self, tournament_id: str):
        self.tournament_id = tournament_id
        # We need the numeric ID for foreign keys, so we fetch it once or per query
        self.t_record = Tournament.query.filter_by(tournament_id=tournament_id).first()
        if not self.t_record:
            raise ValueError(f"Tournament {tournament_id} not found")
        self.db_id = self.t_record.id
        self.elo_calculator = EloCalculator()
        self.pubsub = get_pubsub_manager()
    
    def get_teams(self) -> Dict:
        teams = Team.query.filter_by(tournament_id=self.db_id).all()
        return {t.team_id: t.to_dict() for t in teams}
    
    def register_team(self, team_id: str, name: str, captain: str, group_name: str = None) -> str:
        team = Team(
            team_id=team_id,
            tournament_id=self.db_id,
            name=name,
            captain=captain,
            group_name=group_name
        )
        db.session.add(team)
        db.session.commit()
        
        # Publish event
        self.pubsub.publish_event(
            self.tournament_id,
            'team_registered',
            {'team_id': team_id, 'name': name, 'captain': captain}
        )
        
        return f"Team {name} registered"
    
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
                match_id = generate_match_name(round_num, len(matches_created) + 1)
                
                # Calculate win probabilities based on ELO
                prob_team1, prob_team2 = self.elo_calculator.calculate_win_probability(
                    teams[i].elo_rating, teams[i+1].elo_rating
                )
                
                match = Match(
                    match_id=match_id,
                    tournament_id=self.db_id,
                    round_num=round_num,
                    team1_id=teams[i].team_id,
                    team2_id=teams[i+1].team_id,
                    team1_win_probability=prob_team1,
                    team2_win_probability=prob_team2,
                    status='pending'
                )
                db.session.add(match)
                matches_created.append(match)
        
        self.t_record.current_round = round_num
        db.session.commit()
        
        # Publish event
        self.pubsub.publish_event(
            self.tournament_id,
            'matches_created',
            {
                'round': round_num,
                'match_count': len(matches_created),
                'matches': [m.to_dict() for m in matches_created]
            }
        )
        
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
                    match_id = generate_match_name(round_num, len(round_matches) + 1)
                    
                    # Get team objects for ELO calculation
                    team1_obj = Team.query.filter_by(tournament_id=self.db_id, team_id=t1).first()
                    team2_obj = Team.query.filter_by(tournament_id=self.db_id, team_id=t2).first()
                    
                    prob_team1, prob_team2 = 0.5, 0.5
                    if team1_obj and team2_obj:
                        prob_team1, prob_team2 = self.elo_calculator.calculate_win_probability(
                            team1_obj.elo_rating, team2_obj.elo_rating
                        )
                    
                    match = Match(
                        match_id=match_id,
                        tournament_id=self.db_id,
                        round_num=round_num,
                        team1_id=t1,
                        team2_id=t2,
                        team1_win_probability=prob_team1,
                        team2_win_probability=prob_team2,
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

    def assign_teams_to_groups(self) -> Dict[str, List]:
        """Automatically assign teams to groups for hybrid tournaments."""
        teams = list(Team.query.filter_by(tournament_id=self.db_id).all())
        num_groups = self.t_record.num_groups or 2
        
        if len(teams) < num_groups * 2:
            # Not enough teams for groups
            return {}
        
        # Shuffle teams for random group assignment
        random.shuffle(teams)
        
        # Create group names (A, B, C, D, etc.)
        group_names = [chr(65 + i) for i in range(num_groups)]  # A, B, C, D...
        
        # Distribute teams evenly across groups
        groups = {name: [] for name in group_names}
        for i, team in enumerate(teams):
            group_name = group_names[i % num_groups]
            team.group_name = group_name
            groups[group_name].append(team)
        
        db.session.commit()
        return groups

    def create_group_stage_matches(self) -> List[Dict]:
        """Create round robin matches within each group for hybrid tournaments."""
        teams = Team.query.filter_by(tournament_id=self.db_id).all()
        
        # Check if teams need to be assigned to groups first
        teams_with_groups = [t for t in teams if t.group_name]
        if not teams_with_groups:
            # Auto-assign teams to groups
            groups = self.assign_teams_to_groups()
        else:
            # Group teams by group_name
            groups = {}
            for t in teams:
                if t.group_name:
                    if t.group_name not in groups:
                        groups[t.group_name] = []
                    groups[t.group_name].append(t)
        
        if not groups:
            # Fall back to single elimination if no groups can be formed
            return self.create_single_elimination_matches()
        
        all_matches = []
        match_counter = 0
        
        # For each group, create round robin matches
        for group_name, group_teams in sorted(groups.items()):
            team_ids = [t.team_id for t in group_teams]
            n = len(team_ids)
            
            if n < 2:
                continue
            
            # Add bye if odd number
            if n % 2 == 1:
                team_ids.append(None)
                n += 1
            
            # Circle method for round robin within group
            for round_idx in range(n - 1):
                round_num = round_idx + 1
                for i in range(n // 2):
                    t1 = team_ids[i]
                    t2 = team_ids[n - 1 - i]
                    
                    if t1 is not None and t2 is not None:
                        match_counter += 1
                        match_id = f"g{group_name}-r{round_num}-m{match_counter}"
                        
                        team1_obj = Team.query.filter_by(tournament_id=self.db_id, team_id=t1).first()
                        team2_obj = Team.query.filter_by(tournament_id=self.db_id, team_id=t2).first()
                        
                        prob_team1, prob_team2 = 0.5, 0.5
                        if team1_obj and team2_obj:
                            prob_team1, prob_team2 = self.elo_calculator.calculate_win_probability(
                                team1_obj.elo_rating, team2_obj.elo_rating
                            )
                        
                        match = Match(
                            match_id=match_id,
                            tournament_id=self.db_id,
                            round_num=round_num,
                            team1_id=t1,
                            team2_id=t2,
                            team1_win_probability=prob_team1,
                            team2_win_probability=prob_team2,
                            group_name=group_name,
                            stage='group',
                            status='pending'
                        )
                        db.session.add(match)
                        all_matches.append(match)
                
                # Rotate for next round
                team_ids = [team_ids[0]] + [team_ids[-1]] + team_ids[1:-1]
        
        self.t_record.current_round = 1
        db.session.commit()
        
        self.pubsub.publish_event(
            self.tournament_id,
            'matches_created',
            {'stage': 'group', 'match_count': len(all_matches)}
        )
        
        return [m.to_dict() for m in all_matches]

    def create_knockout_from_groups(self) -> List[Dict]:
        """Create knockout stage matches from group stage qualifiers."""
        num_advance = self.t_record.teams_per_group_advance
        group_standings = self.get_group_standings()
        
        qualifiers = []
        for group_name in sorted(group_standings.keys()):
            standings = group_standings[group_name]
            qualifiers.extend(standings[:num_advance])
        
        if len(qualifiers) < 2:
            return []
        
        # Create bracket matches with qualifiers
        matches_created = []
        round_num = self.t_record.current_round + 1
        
        # Cross-group seeding: 1A vs 2B, 1B vs 2A, etc.
        # For simplicity, just pair in order for now
        for i in range(0, len(qualifiers), 2):
            if i + 1 < len(qualifiers):
                match_id = generate_match_name(round_num, len(matches_created) + 1)
                
                team1_obj = Team.query.filter_by(tournament_id=self.db_id, team_id=qualifiers[i]['team_id']).first()
                team2_obj = Team.query.filter_by(tournament_id=self.db_id, team_id=qualifiers[i+1]['team_id']).first()
                
                prob_team1, prob_team2 = 0.5, 0.5
                if team1_obj and team2_obj:
                    prob_team1, prob_team2 = self.elo_calculator.calculate_win_probability(
                        team1_obj.elo_rating, team2_obj.elo_rating
                    )
                
                match = Match(
                    match_id=match_id,
                    tournament_id=self.db_id,
                    round_num=round_num,
                    team1_id=qualifiers[i]['team_id'],
                    team2_id=qualifiers[i+1]['team_id'],
                    team1_win_probability=prob_team1,
                    team2_win_probability=prob_team2,
                    stage='knockout',
                    status='pending'
                )
                db.session.add(match)
                matches_created.append(match)
        
        self.t_record.current_round = round_num
        db.session.commit()
        
        self.pubsub.publish_event(
            self.tournament_id,
            'knockout_stage_started',
            {'round': round_num, 'match_count': len(matches_created)}
        )
        
        return [m.to_dict() for m in matches_created]

    def group_stage_complete(self) -> bool:
        """Check if all group stage matches are complete."""
        pending = Match.query.filter_by(
            tournament_id=self.db_id,
            stage='group',
            status='pending'
        ).count()
        return pending == 0

    def record_result(self, match_id: str, winner_id: str = None, is_draw: bool = False,
                       team1_score: int = None, team2_score: int = None) -> Tuple[bool, str]:
        """Record match result with support for draws and scores (football-style)."""
        match = Match.query.filter_by(tournament_id=self.db_id, match_id=match_id).first()
        if not match:
            return False, f"Match {match_id} not found"
        
        if match.status != 'pending':
            return False, f"Match {match_id} is not pending"
        
        # Validate input
        if not is_draw and winner_id not in [match.team1_id, match.team2_id]:
            return False, f"Winner {winner_id} is not in this match"
        
        # Get tournament settings
        allow_draws = self.t_record.allow_draws
        is_knockout = match.stage == 'knockout'
        
        # Draws not allowed in knockout stages
        if is_draw and is_knockout:
            return False, "Draws are not allowed in knockout stage matches"
        
        if is_draw and not allow_draws:
            return False, "Draws are not enabled for this tournament"
        
        # Update match
        match.status = 'completed'
        match.team1_score = team1_score
        match.team2_score = team2_score
        match.is_draw = is_draw
        
        team1 = Team.query.filter_by(tournament_id=self.db_id, team_id=match.team1_id).first()
        team2 = Team.query.filter_by(tournament_id=self.db_id, team_id=match.team2_id).first()
        
        old_team1_rating = team1.elo_rating if team1 else 1500
        old_team2_rating = team2.elo_rating if team2 else 1500
        
        if is_draw:
            # Draw: both teams get 1 point
            if team1:
                team1.draws += 1
                team1.points += 1
                if team1_score is not None:
                    team1.goals_for += team1_score
                if team2_score is not None:
                    team1.goals_against += team2_score
            if team2:
                team2.draws += 1
                team2.points += 1
                if team2_score is not None:
                    team2.goals_for += team2_score
                if team1_score is not None:
                    team2.goals_against += team1_score
            
            # ELO for draw (no change or small adjustment)
            # For simplicity, no ELO change on draw
            result_msg = f"Match {match_id} ended in a draw"
        else:
            # Win/Loss result
            match.winner_id = winner_id
            winner = team1 if winner_id == match.team1_id else team2
            loser = team2 if winner_id == match.team1_id else team1
            
            if winner:
                winner.wins += 1
                winner.points += 3  # Football: 3 points for win
                if winner_id == match.team1_id:
                    if team1_score is not None:
                        winner.goals_for += team1_score
                    if team2_score is not None:
                        winner.goals_against += team2_score
                else:
                    if team2_score is not None:
                        winner.goals_for += team2_score
                    if team1_score is not None:
                        winner.goals_against += team1_score
            
            if loser:
                loser.losses += 1
                # 0 points for loss
                if winner_id == match.team1_id:
                    if team2_score is not None:
                        loser.goals_for += team2_score
                    if team1_score is not None:
                        loser.goals_against += team1_score
                else:
                    if team1_score is not None:
                        loser.goals_for += team1_score
                    if team2_score is not None:
                        loser.goals_against += team2_score
            
            # Update ELO ratings
            if winner and loser:
                new_winner_rating, new_loser_rating = self.elo_calculator.calculate_rating_change(
                    winner.elo_rating, loser.elo_rating
                )
                winner.elo_rating = new_winner_rating
                loser.elo_rating = new_loser_rating
                
                # Record ELO history
                winner_history = EloHistory(
                    team_id=winner.id,
                    match_id=match_id,
                    old_rating=old_team1_rating if winner_id == match.team1_id else old_team2_rating,
                    new_rating=new_winner_rating,
                    rating_change=new_winner_rating - (old_team1_rating if winner_id == match.team1_id else old_team2_rating),
                    opponent_rating=old_team2_rating if winner_id == match.team1_id else old_team1_rating,
                    result='win'
                )
                loser_history = EloHistory(
                    team_id=loser.id,
                    match_id=match_id,
                    old_rating=old_team2_rating if winner_id == match.team1_id else old_team1_rating,
                    new_rating=new_loser_rating,
                    rating_change=new_loser_rating - (old_team2_rating if winner_id == match.team1_id else old_team1_rating),
                    opponent_rating=old_team1_rating if winner_id == match.team1_id else old_team2_rating,
                    result='loss'
                )
                db.session.add(winner_history)
                db.session.add(loser_history)
            
            result_msg = f"Recorded {winner_id} as winner of {match_id}"
        
        db.session.commit()
        
        # Publish event
        self.pubsub.publish_event(
            self.tournament_id,
            'match_completed',
            {
                'match_id': match_id,
                'winner_id': winner_id,
                'is_draw': is_draw,
                'team1_score': team1_score,
                'team2_score': team2_score
            }
        )
        
        return True, result_msg

    def all_matches_complete(self, stage: str = None) -> bool:
        """Check if all matches are complete, optionally filtered by stage."""
        query = Match.query.filter_by(
            tournament_id=self.db_id,
            status='pending'
        )
        
        if stage:
            # Check specific stage (e.g., 'knockout' for hybrid tournaments)
            query = query.filter_by(stage=stage)
        else:
            # Check current round only
            query = query.filter_by(round_num=self.t_record.current_round)
        
        return query.count() == 0
    
    def knockout_stage_complete(self) -> bool:
        """Check if all knockout stage matches are complete."""
        pending = Match.query.filter_by(
            tournament_id=self.db_id,
            stage='knockout',
            status='pending'
        ).count()
        completed = Match.query.filter_by(
            tournament_id=self.db_id,
            stage='knockout',
            status='completed'
        ).count()
        # Complete if no pending and at least one completed
        return pending == 0 and completed > 0

    def get_tournament_winner(self) -> Optional[str]:
        # Simple standing based winner
        standings = self.get_standings()
        return standings[0]['team_id'] if standings else None

    def get_standings(self, group_name: str = None) -> List[Dict]:
        """Get standings, optionally filtered by group. Uses football-style points."""
        query = Team.query.filter_by(tournament_id=self.db_id)
        if group_name:
            query = query.filter_by(group_name=group_name)
        teams = query.all()
        
        standings = []
        for t in teams:
            total = t.wins + t.losses + t.draws
            win_rate = (t.wins / total * 100) if total > 0 else 0
            goal_diff = t.goals_for - t.goals_against
            standings.append({
                'team_id': t.team_id,
                'name': t.name,
                'captain': t.captain,
                'group': t.group_name,
                'played': total,
                'wins': t.wins,
                'draws': t.draws,
                'losses': t.losses,
                'points': t.points,
                'goals_for': t.goals_for,
                'goals_against': t.goals_against,
                'goal_difference': goal_diff,
                'elo_rating': t.elo_rating,
                'win_rate': round(win_rate, 1)
            })
        
        # Football-style sort: Points desc, Goal Diff desc, Goals For desc
        standings.sort(key=lambda x: (x['points'], x['goal_difference'], x['goals_for']), reverse=True)
        
        for i, s in enumerate(standings):
            s['rank'] = i + 1
            
        return standings
    
    def get_group_standings(self) -> Dict[str, List[Dict]]:
        """Get standings grouped by group name."""
        teams = Team.query.filter_by(tournament_id=self.db_id).filter(Team.group_name.isnot(None)).all()
        groups = {}
        
        for t in teams:
            if t.group_name not in groups:
                groups[t.group_name] = []
        
        for group_name in groups.keys():
            groups[group_name] = self.get_standings(group_name=group_name)
        
        return groups

    def advance_single_elimination(self, is_hybrid: bool = False) -> Tuple[bool, Optional[List[Dict]]]:
        """Advance to next round of single elimination.
        
        For hybrid tournaments, this only handles knockout stage matches.
        """
        # For hybrid, only look at knockout stage matches
        if is_hybrid:
            # Get the latest knockout round with completed matches
            knockout_matches = Match.query.filter_by(
                tournament_id=self.db_id,
                stage='knockout',
                status='completed'
            ).order_by(Match.round_num.desc()).all()
            
            if not knockout_matches:
                return False, None
            
            current_round = knockout_matches[0].round_num
            
            # Check if current knockout round is complete
            pending = Match.query.filter_by(
                tournament_id=self.db_id,
                stage='knockout',
                round_num=current_round,
                status='pending'
            ).count()
            
            if pending > 0:
                return False, None
            
            current_matches = Match.query.filter_by(
                tournament_id=self.db_id,
                stage='knockout',
                round_num=current_round
            ).all()
        else:
            if not self.all_matches_complete():
                return False, None
            
            current_matches = Match.query.filter_by(
                tournament_id=self.db_id,
                round_num=self.t_record.current_round
            ).all()
            current_round = self.t_record.current_round
        
        winners_ids = [m.winner_id for m in current_matches if m.winner_id]
        
        if len(winners_ids) <= 1:
            # Tournament complete - we have a winner
            return True, None
            
        next_round = current_round + 1
        matches_created = []
        
        # Determine stage for new matches
        stage = 'knockout' if is_hybrid else None
        
        for i in range(0, len(winners_ids), 2):
            if i + 1 < len(winners_ids):
                match_id = generate_match_name(next_round, len(matches_created) + 1)
                
                team1_obj = Team.query.filter_by(tournament_id=self.db_id, team_id=winners_ids[i]).first()
                team2_obj = Team.query.filter_by(tournament_id=self.db_id, team_id=winners_ids[i+1]).first()
                
                prob_team1, prob_team2 = 0.5, 0.5
                if team1_obj and team2_obj:
                    prob_team1, prob_team2 = self.elo_calculator.calculate_win_probability(
                        team1_obj.elo_rating, team2_obj.elo_rating
                    )
                
                match = Match(
                    match_id=match_id,
                    tournament_id=self.db_id,
                    round_num=next_round,
                    team1_id=winners_ids[i],
                    team2_id=winners_ids[i+1],
                    team1_win_probability=prob_team1,
                    team2_win_probability=prob_team2,
                    stage=stage,
                    status='pending'
                )
                db.session.add(match)
                matches_created.append(match)
        
        self.t_record.current_round = next_round
        db.session.commit()
        
        self.pubsub.publish_event(
            self.tournament_id,
            'round_advanced',
            {
                'new_round': next_round,
                'match_count': len(matches_created),
                'matches': [m.to_dict() for m in matches_created]
            }
        )
        
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
