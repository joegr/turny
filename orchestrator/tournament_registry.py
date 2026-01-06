from typing import Optional, Tuple, List

from .models import db, Tournament, Team
from .name_generator import generate_tournament_name, generate_short_id
from shared.state_machine import TournamentStateMachine, TournamentState, TransitionError


class TournamentRegistry:
    """
    Manages tournament lifecycle:
    - Create/update/delete tournament records
    - State transitions (draft -> registration -> active -> completed -> archived)
    """
    
    def __init__(self):
        pass
    
    def create_tournament(
        self,
        name: str,
        tournament_type: str = 'single_elimination',
        max_teams: int = 16,
        min_teams: int = 4,
        scheduled_start: str = None,
        num_groups: int = 0,
        group_stage_rounds: int = 3,
        knockout_type: str = 'single_elimination',
        teams_per_group_advance: int = 2,
        allow_draws: bool = False
    ) -> Tournament:
        """Create a new tournament in draft state."""
        # Generate friendly tournament ID
        tournament_id = generate_tournament_name()
        
        # Check for uniqueness (unlikely collision but handle it)
        existing = Tournament.query.filter_by(tournament_id=tournament_id).first()
        if existing:
            # Fallback to short ID if collision
            tournament_id = f"{tournament_id}-{generate_short_id()[:4]}"
        
        # For hybrid/round_robin with groups, enable draws by default
        if tournament_type in ['hybrid', 'round_robin'] and num_groups > 0:
            allow_draws = True
        
        tournament = Tournament(
            tournament_id=tournament_id,
            name=name,
            tournament_type=tournament_type,
            status='draft',
            max_teams=max_teams,
            min_teams=min_teams,
            num_groups=num_groups,
            group_stage_rounds=group_stage_rounds,
            knockout_type=knockout_type,
            teams_per_group_advance=teams_per_group_advance,
            allow_draws=allow_draws
        )
        
        db.session.add(tournament)
        db.session.commit()
        
        return tournament
    
    def get_tournament(self, tournament_id: str) -> Optional[Tournament]:
        """Get tournament by its public ID."""
        return Tournament.query.filter_by(tournament_id=tournament_id).first()
    
    def list_tournaments(
        self,
        status: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Tournament]:
        """List tournaments with optional filtering."""
        query = Tournament.query
        
        if status:
            query = query.filter_by(status=status)
        
        query = query.order_by(Tournament.created_at.desc())
        return query.offset(offset).limit(limit).all()
    
    def publish_tournament(self, tournament_id: str) -> Tuple[bool, str]:
        """Move tournament from draft to registration and initialize state."""
        tournament = self.get_tournament(tournament_id)
        
        if not tournament:
            return False, "Tournament not found"
        
        # Use state machine to validate and execute transition
        sm = TournamentStateMachine.from_state_string(tournament.status)
        
        if not sm.can_perform('publish'):
            return False, f"Cannot publish tournament in {tournament.status} state"
        
        try:
            old_state = sm.state.value
            new_state = sm.transition('publish')
            
            # Update tournament status from state machine
            tournament.status = new_state.value
            
            db.session.commit()
            
            return True, f"Tournament published"
            
        except TransitionError as e:
            return False, str(e)
    
    def get_tournament_url(self, tournament_id: str) -> str:
        """Get the URL for a tournament's bracket view."""
        return f"/{tournament_id}/bracket"
    
    def archive_tournament(self, tournament_id: str) -> Tuple[bool, str]:
        """Archive a completed tournament."""
        tournament = self.get_tournament(tournament_id)
        
        if not tournament:
            return False, "Tournament not found"
        
        # Use state machine to validate transition
        sm = TournamentStateMachine.from_state_string(tournament.status)
        
        if not sm.can_perform('archive'):
            return False, f"Cannot archive tournament in {tournament.status} state"
        
        try:
            old_state = sm.state.value
            new_state = sm.transition('archive')
            
            tournament.status = new_state.value
            db.session.commit()
            
            return True, "Tournament archived"
            
        except TransitionError as e:
            return False, str(e)
    
    def delete_tournament(self, tournament_id: str) -> Tuple[bool, str]:
        """Delete a tournament (only allowed in draft state)."""
        tournament = self.get_tournament(tournament_id)
        
        if not tournament:
            return False, "Tournament not found"
        
        if tournament.status != 'draft':
            return False, "Can only delete tournaments in draft state"
        
        db.session.delete(tournament)
        db.session.commit()
        
        return True, "Tournament deleted"
