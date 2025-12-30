from typing import List, Set
from .models import db, Subscription


class SubscriptionManager:
    """
    Manages user subscriptions to tournaments.
    Uses PostgreSQL for persistence.
    """
    
    def __init__(self):
        pass
    
    def subscribe(
        self,
        user_id: str,
        tournament_id: str,
        notify_on_start: bool = True,
        notify_on_match: bool = True,
        notify_on_complete: bool = True
    ) -> bool:
        """Subscribe a user to a tournament."""
        # Check if already subscribed
        existing = Subscription.query.filter_by(
            user_id=user_id,
            tournament_id=tournament_id
        ).first()
        
        if existing:
            # Update preferences
            existing.notify_on_start = notify_on_start
            existing.notify_on_match = notify_on_match
            existing.notify_on_complete = notify_on_complete
        else:
            # Create new subscription
            sub = Subscription(
                user_id=user_id,
                tournament_id=tournament_id,
                notify_on_start=notify_on_start,
                notify_on_match=notify_on_match,
                notify_on_complete=notify_on_complete
            )
            db.session.add(sub)
        
        db.session.commit()
        return True
    
    def unsubscribe(self, user_id: str, tournament_id: str) -> bool:
        """Unsubscribe a user from a tournament."""
        sub = Subscription.query.filter_by(
            user_id=user_id,
            tournament_id=tournament_id
        ).first()
        
        if sub:
            db.session.delete(sub)
            db.session.commit()
        
        return True
    
    def get_user_subscriptions(self, user_id: str) -> List[str]:
        """Get all tournament IDs a user is subscribed to."""
        subs = Subscription.query.filter_by(user_id=user_id).all()
        return [s.tournament_id for s in subs]
    
    def get_tournament_subscribers(self, tournament_id: str) -> List[str]:
        """Get all user IDs subscribed to a tournament."""
        subs = Subscription.query.filter_by(tournament_id=tournament_id).all()
        return [s.user_id for s in subs]
    
    def is_subscribed(self, user_id: str, tournament_id: str) -> bool:
        """Check if a user is subscribed to a tournament."""
        return Subscription.query.filter_by(
            user_id=user_id,
            tournament_id=tournament_id
        ).first() is not None
    
    def get_subscribers_for_event(
        self,
        tournament_id: str,
        event_type: str
    ) -> List[str]:
        """Get subscribers who want notifications for a specific event type."""
        # Map event types to notification preferences
        pref_map = {
            'tournament.started': 'notify_on_start',
            'match.result': 'notify_on_match',
            'tournament.completed': 'notify_on_complete',
        }
        
        pref_field = pref_map.get(event_type)
        if not pref_field:
            # Default to all subscribers
            return self.get_tournament_subscribers(tournament_id)
        
        # Query database for subscribers with this preference enabled
        subs = Subscription.query.filter(
            Subscription.tournament_id == tournament_id,
            getattr(Subscription, pref_field) == True
        ).all()
        
        return [s.user_id for s in subs]
