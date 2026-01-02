import os
import json
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from google.cloud import pubsub_v1
from google.api_core import retry
import logging

logger = logging.getLogger(__name__)

class PubSubManager:
    """
    Manages Google Cloud Pub/Sub for real-time tournament events.
    Handles topic creation, message publishing, and subscription management.
    """
    
    def __init__(self):
        self.project_id = os.getenv('GCP_PROJECT_ID', 'local-dev')
        self.is_local = os.getenv('FLASK_ENV') == 'development'
        
        if not self.is_local:
            self.publisher = pubsub_v1.PublisherClient()
            self.subscriber = pubsub_v1.SubscriberClient()
        else:
            # Local development mode - no actual Pub/Sub
            self.publisher = None
            self.subscriber = None
            logger.info("PubSubManager running in local development mode (no actual Pub/Sub)")
    
    def get_topic_path(self, tournament_id: str) -> str:
        """Get the full topic path for a tournament."""
        if self.is_local:
            return f"local-topic-{tournament_id}"
        return self.publisher.topic_path(self.project_id, f'tournament-{tournament_id}')
    
    def get_subscription_path(self, tournament_id: str, subscriber_id: str = 'default') -> str:
        """Get the full subscription path for a tournament."""
        if self.is_local:
            return f"local-sub-{tournament_id}-{subscriber_id}"
        return self.subscriber.subscription_path(
            self.project_id, 
            f'tournament-{tournament_id}-{subscriber_id}'
        )
    
    def ensure_topic_exists(self, tournament_id: str) -> bool:
        """
        Ensure a Pub/Sub topic exists for the tournament.
        Creates it if it doesn't exist.
        """
        if self.is_local:
            logger.debug(f"Local mode: Topic for {tournament_id} (simulated)")
            return True
        
        try:
            topic_path = self.get_topic_path(tournament_id)
            self.publisher.get_topic(request={"topic": topic_path})
            logger.info(f"Topic exists: {topic_path}")
            return True
        except Exception:
            # Topic doesn't exist, create it
            try:
                topic_path = self.get_topic_path(tournament_id)
                self.publisher.create_topic(request={"name": topic_path})
                logger.info(f"Created topic: {topic_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to create topic for {tournament_id}: {e}")
                return False
    
    def ensure_subscription_exists(self, tournament_id: str, subscriber_id: str = 'default') -> bool:
        """
        Ensure a subscription exists for the tournament topic.
        Creates it if it doesn't exist.
        """
        if self.is_local:
            logger.debug(f"Local mode: Subscription for {tournament_id} (simulated)")
            return True
        
        try:
            subscription_path = self.get_subscription_path(tournament_id, subscriber_id)
            self.subscriber.get_subscription(request={"subscription": subscription_path})
            logger.info(f"Subscription exists: {subscription_path}")
            return True
        except Exception:
            # Subscription doesn't exist, create it
            try:
                topic_path = self.get_topic_path(tournament_id)
                subscription_path = self.get_subscription_path(tournament_id, subscriber_id)
                
                self.subscriber.create_subscription(
                    request={
                        "name": subscription_path,
                        "topic": topic_path,
                        "ack_deadline_seconds": 60,
                        "message_retention_duration": {"seconds": 86400}  # 24 hours
                    }
                )
                logger.info(f"Created subscription: {subscription_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to create subscription for {tournament_id}: {e}")
                return False
    
    def publish_event(
        self, 
        tournament_id: str, 
        event_type: str, 
        data: Dict[str, Any],
        ensure_topic: bool = True
    ) -> Optional[str]:
        """
        Publish an event to the tournament's Pub/Sub topic.
        
        Args:
            tournament_id: Tournament identifier
            event_type: Type of event (e.g., 'match_completed', 'team_registered')
            data: Event data payload
            ensure_topic: Whether to ensure topic exists before publishing
            
        Returns:
            Message ID if successful, None otherwise
        """
        if self.is_local:
            logger.info(f"Local mode: Published {event_type} for {tournament_id}: {data}")
            return "local-message-id"
        
        try:
            if ensure_topic:
                self.ensure_topic_exists(tournament_id)
            
            topic_path = self.get_topic_path(tournament_id)
            
            message_data = {
                'event_type': event_type,
                'tournament_id': tournament_id,
                'data': data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            message_bytes = json.dumps(message_data).encode('utf-8')
            
            # Publish with retry
            future = self.publisher.publish(
                topic_path, 
                message_bytes,
                event_type=event_type  # Add as attribute for filtering
            )
            
            message_id = future.result(timeout=5.0)
            logger.info(f"Published {event_type} to {tournament_id}: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type} for {tournament_id}: {e}")
            return None
    
    def pull_messages(
        self, 
        tournament_id: str, 
        max_messages: int = 10,
        subscriber_id: str = 'default'
    ) -> list:
        """
        Pull messages from a tournament subscription (for SSE streaming).
        
        Args:
            tournament_id: Tournament identifier
            max_messages: Maximum number of messages to pull
            subscriber_id: Subscriber identifier
            
        Returns:
            List of message dictionaries
        """
        if self.is_local:
            return []
        
        try:
            subscription_path = self.get_subscription_path(tournament_id, subscriber_id)
            
            response = self.subscriber.pull(
                request={
                    "subscription": subscription_path,
                    "max_messages": max_messages,
                },
                retry=retry.Retry(deadline=5.0),
            )
            
            messages = []
            ack_ids = []
            
            for received_message in response.received_messages:
                try:
                    data = json.loads(received_message.message.data.decode('utf-8'))
                    messages.append(data)
                    ack_ids.append(received_message.ack_id)
                except Exception as e:
                    logger.error(f"Failed to parse message: {e}")
            
            # Acknowledge messages
            if ack_ids:
                self.subscriber.acknowledge(
                    request={
                        "subscription": subscription_path,
                        "ack_ids": ack_ids,
                    }
                )
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to pull messages for {tournament_id}: {e}")
            return []
    
    def delete_topic(self, tournament_id: str) -> bool:
        """Delete a tournament's Pub/Sub topic (cleanup)."""
        if self.is_local:
            return True
        
        try:
            topic_path = self.get_topic_path(tournament_id)
            self.publisher.delete_topic(request={"topic": topic_path})
            logger.info(f"Deleted topic: {topic_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete topic for {tournament_id}: {e}")
            return False
    
    def delete_subscription(self, tournament_id: str, subscriber_id: str = 'default') -> bool:
        """Delete a tournament subscription (cleanup)."""
        if self.is_local:
            return True
        
        try:
            subscription_path = self.get_subscription_path(tournament_id, subscriber_id)
            self.subscriber.delete_subscription(request={"subscription": subscription_path})
            logger.info(f"Deleted subscription: {subscription_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete subscription for {tournament_id}: {e}")
            return False


# Global instance
_pubsub_manager = None

def get_pubsub_manager() -> PubSubManager:
    """Get or create the global PubSubManager instance."""
    global _pubsub_manager
    if _pubsub_manager is None:
        _pubsub_manager = PubSubManager()
    return _pubsub_manager
