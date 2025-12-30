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
    - Spawn tournament service instances
    - Track running instances
    - Route requests to correct instance
    """
    
    def __init__(self, redis_client: redis.Redis = None):
        self.redis = redis_client
        self._port_pool = set()
    
    def _get_available_port(self) -> int:
        """Find an available port for a new tournament service."""
        base_port = current_app.config.get('TOURNAMENT_SERVICE_BASE_PORT', 6001)
        max_instances = current_app.config.get('MAX_TOURNAMENT_INSTANCES', 100)
        
        # Get all used ports from active tournaments
        active = Tournament.query.filter(
            Tournament.status.in_(['registration', 'active']),
            Tournament.service_port.isnot(None)
        ).all()
        used_ports = {t.service_port for t in active}
        
        # Find first available port
        for port in range(base_port, base_port + max_instances):
            if port not in used_ports:
                # Verify port is actually free
                if self._is_port_free(port):
                    return port
        
        raise RuntimeError("No available ports for tournament service")
    
    def _is_port_free(self, port: int) -> bool:
        """Check if a port is available."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', port))
                s.close()
                time.sleep(0.1)  # Give OS time to release the port
                return True
            except OSError:
                return False
    
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
        """Move tournament from draft to registration and spawn service."""
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
            
            # Spawn the tournament service
            success, message = self.spawn_service(tournament)
            if not success:
                return False, message
            
            # Update tournament status from state machine
            tournament.status = new_state.value
            db.session.commit()
            
            # Publish state change event
            if self.redis:
                event = state_changed_event(tournament_id, old_state, new_state.value)
                self.redis.publish('global:announcements', event.to_json())
            
            return True, f"Tournament published and service started on port {tournament.service_port}"
            
        except TransitionError as e:
            return False, str(e)
    
    def spawn_service(self, tournament: Tournament) -> Tuple[bool, str]:
        """Spawn a tournament service instance."""
        use_cloud_run = current_app.config.get('USE_CLOUD_RUN', False)
        use_docker = current_app.config.get('USE_DOCKER', False)
        
        if use_cloud_run:
            return self._spawn_cloud_run_service(tournament)
        elif use_docker:
            return self._spawn_docker_service(tournament)
        else:
            return self._spawn_process_service(tournament)
    
    def _spawn_cloud_run_service(self, tournament: Tournament) -> Tuple[bool, str]:
        """Spawn tournament service as a Cloud Run service."""
        from .cloud_run_manager import CloudRunManager
        
        manager = CloudRunManager()
        redis_url = current_app.config.get('REDIS_URL', '')
        
        success, message, service_url = manager.spawn_tournament_service(
            tournament_id=tournament.tournament_id,
            tournament_type=tournament.tournament_type,
            redis_url=redis_url
        )
        
        if success and service_url:
            tournament.service_url = service_url
            tournament.service_host = service_url
            db.session.commit()
            
            # Notify via pub/sub
            if self.redis:
                import json
                self.redis.publish('orchestrator:service_status', json.dumps({
                    'type': 'service.deployed',
                    'tournament_id': tournament.tournament_id,
                    'url': service_url
                }))
        
        return success, message
    
    def _spawn_process_service(self, tournament: Tournament) -> Tuple[bool, str]:
        """Spawn tournament service as a subprocess."""
        import os
        log_path = f'/tmp/tournament_{tournament.tournament_id}.log'
        
        try:
            port = self._get_available_port()
            host = current_app.config.get('TOURNAMENT_SERVICE_HOST', 'localhost')
            
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            service_path = os.path.join(project_root, 'tournament_service', 'app.py')
            
            env = os.environ.copy()
            env['TOURNAMENT_ID'] = tournament.tournament_id
            env['TOURNAMENT_TYPE'] = tournament.tournament_type
            env['PORT'] = str(port)
            env['REDIS_URL'] = current_app.config.get('REDIS_URL', 'redis://localhost:6379')
            
            log_file = open(log_path, 'w')
            process = subprocess.Popen(
                ['python', '-u', service_path],
                env=env,
                stdout=log_file,
                stderr=log_file,
                start_new_session=True
            )
            
            tournament.service_port = port
            tournament.service_host = host
            db.session.commit()
            
            # Wait for service to be ready
            for attempt in range(15):
                if process.poll() is not None:
                    log_file.close()
                    with open(log_path, 'r') as f:
                        error_log = f.read()
                    return False, f"Service exited with code {process.returncode}: {error_log[:500]}"
                
                try:
                    resp = requests.get(f"http://{host}:{port}/api/state", timeout=1)
                    if resp.status_code == 200:
                        return True, f"Service started on port {port}"
                except requests.exceptions.RequestException:
                    time.sleep(0.5)
            
            return True, f"Service starting on port {port}"
            
        except Exception as e:
            import traceback
            return False, f"Failed to spawn service: {str(e)}\n{traceback.format_exc()}"
    
    def _spawn_docker_service(self, tournament: Tournament) -> Tuple[bool, str]:
        """Spawn tournament service as a Docker container (production mode)."""
        try:
            port = self._get_available_port()
            container_name = f"tournament-{tournament.tournament_id}"
            network = current_app.config.get('DOCKER_NETWORK', 'tournament-network')
            redis_url = current_app.config.get('REDIS_URL', 'redis://redis:6379')
            
            cmd = [
                'docker', 'run', '-d',
                '--name', container_name,
                '--network', network,
                '-p', f'{port}:5000',
                '-e', f'TOURNAMENT_ID={tournament.tournament_id}',
                '-e', f'TOURNAMENT_TYPE={tournament.tournament_type}',
                '-e', f'REDIS_URL={redis_url}',
                'tournament-service:latest'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"Docker error: {result.stderr}"
            
            container_id = result.stdout.strip()
            
            tournament.service_port = port
            tournament.service_host = 'localhost'
            tournament.container_id = container_id
            db.session.commit()
            
            return True, f"Container {container_id[:12]} started on port {port}"
            
        except Exception as e:
            return False, f"Failed to spawn container: {str(e)}"
    
    def stop_service(self, tournament: Tournament) -> Tuple[bool, str]:
        """Stop a tournament service instance."""
        if tournament.container_id:
            # Docker mode
            try:
                subprocess.run(
                    ['docker', 'stop', tournament.container_id],
                    capture_output=True,
                    timeout=30
                )
                subprocess.run(
                    ['docker', 'rm', tournament.container_id],
                    capture_output=True,
                    timeout=10
                )
            except Exception as e:
                return False, f"Failed to stop container: {str(e)}"
        
        tournament.service_port = None
        tournament.service_host = None
        tournament.container_id = None
        db.session.commit()
        
        return True, "Service stopped"
    
    def get_service_url(self, tournament_id: str) -> Optional[str]:
        """Get the service URL for a tournament."""
        tournament = self.get_tournament(tournament_id)
        if tournament:
            return tournament.service_url
        return None
    
    def archive_tournament(self, tournament_id: str) -> Tuple[bool, str]:
        """Archive a completed tournament and stop its service."""
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
            
            # Stop the service if running
            if tournament.service_url:
                self.stop_service(tournament)
            
            tournament.status = new_state.value
            db.session.commit()
            
            # Publish state change event
            if self.redis:
                event = state_changed_event(tournament_id, old_state, new_state.value)
                self.redis.publish('global:announcements', event.to_json())
            
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
