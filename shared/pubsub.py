import os
import json
import redis
from typing import Callable, Optional
from threading import Thread
from .events import Event


class PubSubClient:
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis = redis.from_url(
            self.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        self._pubsub = None
        self._listener_thread = None
        self._handlers = {}
    
    def publish(self, channel: str, event: Event):
        self.redis.publish(channel, event.to_json())
    
    def publish_tournament_event(self, tournament_id: str, event: Event):
        channel = f"tournament:{tournament_id}:events"
        self.publish(channel, event)
        
        self.redis.publish("global:announcements", event.to_json())
    
    def publish_user_notification(self, user_id: str, event: Event):
        channel = f"user:{user_id}:notifications"
        self.publish(channel, event)
    
    def subscribe(self, channel: str, handler: Callable[[Event], None]):
        if self._pubsub is None:
            self._pubsub = self.redis.pubsub()
        
        self._handlers[channel] = handler
        self._pubsub.subscribe(**{channel: self._message_handler})
    
    def subscribe_tournament(self, tournament_id: str, handler: Callable[[Event], None]):
        channel = f"tournament:{tournament_id}:events"
        self.subscribe(channel, handler)
    
    def subscribe_user(self, user_id: str, handler: Callable[[Event], None]):
        channel = f"user:{user_id}:notifications"
        self.subscribe(channel, handler)
    
    def subscribe_global(self, handler: Callable[[Event], None]):
        self.subscribe("global:announcements", handler)
    
    def _message_handler(self, message):
        if message['type'] == 'message':
            channel = message['channel']
            if channel in self._handlers:
                try:
                    event = Event.from_json(message['data'])
                    self._handlers[channel](event)
                except Exception as e:
                    print(f"Error handling message on {channel}: {e}")
    
    def start_listening(self, blocking: bool = False):
        if self._pubsub is None:
            return
        
        if blocking:
            self._pubsub.run_in_thread(sleep_time=0.1)
        else:
            self._listener_thread = Thread(target=self._listen_loop, daemon=True)
            self._listener_thread.start()
    
    def _listen_loop(self):
        if self._pubsub:
            for message in self._pubsub.listen():
                pass
    
    def stop_listening(self):
        if self._pubsub:
            self._pubsub.close()
            self._pubsub = None
    
    def get_recent_events(self, tournament_id: str, count: int = 50) -> list:
        key = f"tournament:{tournament_id}:event_log"
        events_json = self.redis.lrange(key, 0, count - 1)
        return [Event.from_json(e) for e in events_json]
    
    def log_event(self, tournament_id: str, event: Event):
        key = f"tournament:{tournament_id}:event_log"
        self.redis.lpush(key, event.to_json())
        self.redis.ltrim(key, 0, 999)
    
    def report_service_status(self, tournament_id: str, status: str, port: int = None, error: str = None):
        """Report tournament service deployment status back to orchestrator."""
        import json
        message = {
            "type": "service.status",
            "tournament_id": tournament_id,
            "status": status,  # "starting", "ready", "error", "stopped"
            "port": port,
            "error": error
        }
        self.redis.publish("orchestrator:service_status", json.dumps(message))
        # Also store in Redis for orchestrator to check
        self.redis.hset(f"service:{tournament_id}", mapping={
            "status": status,
            "port": str(port) if port else "",
            "error": error or ""
        })


class SubscriptionManager:
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
    
    def subscribe_user_to_tournament(self, user_id: str, tournament_id: str):
        self.redis.sadd(f"user:{user_id}:subscriptions", tournament_id)
        self.redis.sadd(f"tournament:{tournament_id}:subscribers", user_id)
    
    def unsubscribe_user_from_tournament(self, user_id: str, tournament_id: str):
        self.redis.srem(f"user:{user_id}:subscriptions", tournament_id)
        self.redis.srem(f"tournament:{tournament_id}:subscribers", user_id)
    
    def get_user_subscriptions(self, user_id: str) -> set:
        return self.redis.smembers(f"user:{user_id}:subscriptions")
    
    def get_tournament_subscribers(self, tournament_id: str) -> set:
        return self.redis.smembers(f"tournament:{tournament_id}:subscribers")
    
    def is_subscribed(self, user_id: str, tournament_id: str) -> bool:
        return self.redis.sismember(f"user:{user_id}:subscriptions", tournament_id)
