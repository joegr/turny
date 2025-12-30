"""
Cloud Run Manager for spawning tournament service instances.

Uses Google Cloud Run Admin API to dynamically deploy tournament services.
"""
import os
import time
from typing import Optional, Tuple
from flask import current_app


class CloudRunManager:
    """Manages Cloud Run service deployments for tournaments."""
    
    def __init__(self):
        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.region = os.getenv('GCP_REGION', 'us-central1')
        self.tournament_image = os.getenv(
            'TOURNAMENT_SERVICE_IMAGE',
            f'us-central1-docker.pkg.dev/{self.project_id}/tournament-repo/tournament-service:latest'
        )
        self._client = None
    
    @property
    def client(self):
        """Lazy-load Cloud Run client."""
        if self._client is None:
            try:
                from google.cloud import run_v2
                self._client = run_v2.ServicesClient()
            except ImportError:
                raise RuntimeError("google-cloud-run package not installed")
        return self._client
    
    def spawn_tournament_service(
        self,
        tournament_id: str,
        tournament_type: str,
        redis_url: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Deploy a new Cloud Run service for a tournament.
        
        Returns:
            Tuple of (success, message, service_url)
        """
        from google.cloud import run_v2
        from google.api_core.exceptions import AlreadyExists, GoogleAPIError
        
        service_name = f"tournament-{tournament_id.replace('_', '-')}"
        parent = f"projects/{self.project_id}/locations/{self.region}"
        
        service = run_v2.Service(
            template=run_v2.RevisionTemplate(
                containers=[
                    run_v2.Container(
                        image=self.tournament_image,
                        ports=[run_v2.ContainerPort(container_port=8080)],
                        env=[
                            run_v2.EnvVar(name="TOURNAMENT_ID", value=tournament_id),
                            run_v2.EnvVar(name="TOURNAMENT_TYPE", value=tournament_type),
                            run_v2.EnvVar(name="REDIS_URL", value=redis_url),
                            run_v2.EnvVar(name="PORT", value="8080"),
                        ],
                        resources=run_v2.ResourceRequirements(
                            limits={"memory": "512Mi", "cpu": "1"}
                        ),
                    )
                ],
                scaling=run_v2.RevisionScaling(
                    min_instance_count=0,
                    max_instance_count=2
                ),
            ),
            ingress=run_v2.IngressTraffic.INGRESS_TRAFFIC_ALL,
        )
        
        try:
            operation = self.client.create_service(
                parent=parent,
                service=service,
                service_id=service_name
            )
            
            # Wait for deployment (with timeout)
            result = operation.result(timeout=120)
            service_url = result.uri
            
            return True, f"Service deployed: {service_name}", service_url
            
        except AlreadyExists:
            # Service exists, get its URL
            service_path = f"{parent}/services/{service_name}"
            try:
                existing = self.client.get_service(name=service_path)
                return True, f"Service already exists: {service_name}", existing.uri
            except GoogleAPIError as e:
                return False, f"Failed to get existing service: {e}", None
                
        except GoogleAPIError as e:
            return False, f"Failed to deploy service: {e}", None
    
    def delete_tournament_service(self, tournament_id: str) -> Tuple[bool, str]:
        """Delete a tournament's Cloud Run service."""
        from google.api_core.exceptions import NotFound, GoogleAPIError
        
        service_name = f"tournament-{tournament_id.replace('_', '-')}"
        name = f"projects/{self.project_id}/locations/{self.region}/services/{service_name}"
        
        try:
            operation = self.client.delete_service(name=name)
            operation.result(timeout=60)
            return True, f"Service deleted: {service_name}"
        except NotFound:
            return True, f"Service not found (already deleted): {service_name}"
        except GoogleAPIError as e:
            return False, f"Failed to delete service: {e}"
    
    def get_service_status(self, tournament_id: str) -> Optional[dict]:
        """Get the status of a tournament service."""
        from google.api_core.exceptions import NotFound, GoogleAPIError
        
        service_name = f"tournament-{tournament_id.replace('_', '-')}"
        name = f"projects/{self.project_id}/locations/{self.region}/services/{service_name}"
        
        try:
            service = self.client.get_service(name=name)
            return {
                "name": service_name,
                "url": service.uri,
                "ready": service.terminal_condition.state.name == "CONDITION_SUCCEEDED",
                "generation": service.generation,
            }
        except NotFound:
            return None
        except GoogleAPIError:
            return None
    
    def wait_for_service_ready(
        self,
        tournament_id: str,
        timeout: int = 120,
        poll_interval: int = 5
    ) -> Tuple[bool, Optional[str]]:
        """Wait for a service to become ready."""
        import requests
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_service_status(tournament_id)
            
            if status and status.get("ready") and status.get("url"):
                # Verify the service is actually responding
                try:
                    resp = requests.get(f"{status['url']}/api/state", timeout=5)
                    if resp.status_code == 200:
                        return True, status["url"]
                except requests.exceptions.RequestException:
                    pass
            
            time.sleep(poll_interval)
        
        return False, None
