import uuid
import subprocess
import socket
import time
import requests
from typing import Optional, Tuple, List
from flask import current_app
import redis

from .models import db, Tournament, Team
from shared.state_machine import TournamentStateMachine, TournamentState, TransitionError
from shared.events import state_changed_event


class TournamentRegistry:
    """
    Manages tournament lifecycle:
    - Create/update/delete tournament records
    - Track running instances (Monolith: internal routing)
    """
    
    def __init__(self):
        self._port_pool = set()
    
    def _get_available_port(self) -> int:
        """Deprecated: No longer needed in Monolith mode."""
        return 0
    
    def _is_port_free(self, port: int) -> bool:
        """Deprecated: No longer needed in Monolith mode."""
        return True
    
    def create_tournament(
        self,
        name: str,
        tournament_type: str = 'single_elimination',
        max_teams: int = 16,
        min_teams: int = 4,
        scheduled_start: str = None
    ) -> Tournament:
        """Create a new tournament in draft state."""
        tournament_id = f"t_{uuid.uuid4().hex[:12]}"
        
        tournament = Tournament(
            tournament_id=tournament_id,
            name=name,
            tournament_type=tournament_type,
            status='draft',
            max_teams=max_teams,
            min_teams=min_teams
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
            
            # Monolith Mode: No external service spawning.
            # We simply mark it as published. The internal 'play' blueprint handles the rest.
            
            # Update tournament status from state machine
            tournament.status = new_state.value
            
            # Set service URL to internal route for consistency in UI logic
            tournament.service_url = f"/tournaments/{tournament_id}/play"
            
            db.session.commit()
            
            return True, f"Tournament published"
            
        except TransitionError as e:
            return False, str(e)
    
    def spawn_service(self, tournament: Tournament) -> Tuple[bool, str]:
        """Deprecated in Monolith mode."""
        return True, "Internal service active"
    
    def stop_service(self, tournament: Tournament) -> Tuple[bool, str]:
        """Deprecated in Monolith mode."""
        return True, "Internal service stopped"
    
    def get_service_url(self, tournament_id: str) -> Optional[str]:
        """Get the service URL for a tournament."""
        return f"/tournaments/{tournament_id}/play"
    
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
