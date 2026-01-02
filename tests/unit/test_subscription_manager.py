"""
Unit tests for SubscriptionManager class.
Tests: subscribe, unsubscribe, get_user_subscriptions, get_tournament_subscribers,
       is_subscribed, get_subscribers_for_event
"""
import pytest
from orchestrator.subscription_manager import SubscriptionManager
from orchestrator.models import db, Subscription


class TestSubscriptionManagerInit:
    """Tests for SubscriptionManager initialization."""
    
    def test_init(self):
        """Should initialize without errors."""
        manager = SubscriptionManager()
        assert manager is not None


class TestSubscribe:
    """Tests for subscribe method."""
    
    def test_subscribe_new_user(self, app, db_session):
        """Should create new subscription."""
        with app.app_context():
            manager = SubscriptionManager()
            result = manager.subscribe("user-1", "tournament-1")
            
            assert result is True
            
            sub = Subscription.query.filter_by(
                user_id="user-1",
                tournament_id="tournament-1"
            ).first()
            assert sub is not None
    
    def test_subscribe_default_preferences(self, app, db_session):
        """Default preferences should all be True."""
        with app.app_context():
            manager = SubscriptionManager()
            manager.subscribe("user-1", "tournament-1")
            
            sub = Subscription.query.filter_by(
                user_id="user-1",
                tournament_id="tournament-1"
            ).first()
            
            assert sub.notify_on_start is True
            assert sub.notify_on_match is True
            assert sub.notify_on_complete is True
    
    def test_subscribe_custom_preferences(self, app, db_session):
        """Custom preferences should be set correctly."""
        with app.app_context():
            manager = SubscriptionManager()
            manager.subscribe(
                "user-1", 
                "tournament-1",
                notify_on_start=True,
                notify_on_match=False,
                notify_on_complete=True
            )
            
            sub = Subscription.query.filter_by(
                user_id="user-1",
                tournament_id="tournament-1"
            ).first()
            
            assert sub.notify_on_start is True
            assert sub.notify_on_match is False
            assert sub.notify_on_complete is True
    
    def test_subscribe_update_existing(self, app, db_session):
        """Subscribing again should update preferences."""
        with app.app_context():
            manager = SubscriptionManager()
            
            # First subscription
            manager.subscribe("user-1", "tournament-1", notify_on_match=True)
            
            # Update subscription
            manager.subscribe("user-1", "tournament-1", notify_on_match=False)
            
            sub = Subscription.query.filter_by(
                user_id="user-1",
                tournament_id="tournament-1"
            ).first()
            
            # Should be updated, not duplicated
            assert sub.notify_on_match is False
            
            count = Subscription.query.filter_by(
                user_id="user-1",
                tournament_id="tournament-1"
            ).count()
            assert count == 1
    
    def test_subscribe_multiple_tournaments(self, app, db_session):
        """User can subscribe to multiple tournaments."""
        with app.app_context():
            manager = SubscriptionManager()
            
            manager.subscribe("user-1", "tournament-1")
            manager.subscribe("user-1", "tournament-2")
            manager.subscribe("user-1", "tournament-3")
            
            subs = Subscription.query.filter_by(user_id="user-1").all()
            assert len(subs) == 3


class TestUnsubscribe:
    """Tests for unsubscribe method."""
    
    def test_unsubscribe_existing(self, app, db_session):
        """Should remove existing subscription."""
        with app.app_context():
            manager = SubscriptionManager()
            
            manager.subscribe("user-1", "tournament-1")
            result = manager.unsubscribe("user-1", "tournament-1")
            
            assert result is True
            
            sub = Subscription.query.filter_by(
                user_id="user-1",
                tournament_id="tournament-1"
            ).first()
            assert sub is None
    
    def test_unsubscribe_nonexistent(self, app, db_session):
        """Should succeed gracefully for non-existent subscription."""
        with app.app_context():
            manager = SubscriptionManager()
            result = manager.unsubscribe("user-1", "tournament-1")
            
            assert result is True  # Should not fail


class TestGetUserSubscriptions:
    """Tests for get_user_subscriptions method."""
    
    def test_get_subscriptions(self, app, db_session):
        """Should return list of tournament IDs."""
        with app.app_context():
            manager = SubscriptionManager()
            
            manager.subscribe("user-1", "tournament-1")
            manager.subscribe("user-1", "tournament-2")
            manager.subscribe("user-1", "tournament-3")
            
            subs = manager.get_user_subscriptions("user-1")
            
            assert len(subs) == 3
            assert "tournament-1" in subs
            assert "tournament-2" in subs
            assert "tournament-3" in subs
    
    def test_get_subscriptions_empty(self, app, db_session):
        """Should return empty list for user with no subscriptions."""
        with app.app_context():
            manager = SubscriptionManager()
            subs = manager.get_user_subscriptions("user-no-subs")
            
            assert subs == []
    
    def test_get_subscriptions_different_users(self, app, db_session):
        """Should only return subscriptions for specified user."""
        with app.app_context():
            manager = SubscriptionManager()
            
            manager.subscribe("user-1", "tournament-1")
            manager.subscribe("user-2", "tournament-2")
            
            subs = manager.get_user_subscriptions("user-1")
            
            assert len(subs) == 1
            assert "tournament-1" in subs


class TestGetTournamentSubscribers:
    """Tests for get_tournament_subscribers method."""
    
    def test_get_subscribers(self, app, db_session):
        """Should return list of user IDs."""
        with app.app_context():
            manager = SubscriptionManager()
            
            manager.subscribe("user-1", "tournament-1")
            manager.subscribe("user-2", "tournament-1")
            manager.subscribe("user-3", "tournament-1")
            
            subscribers = manager.get_tournament_subscribers("tournament-1")
            
            assert len(subscribers) == 3
            assert "user-1" in subscribers
            assert "user-2" in subscribers
            assert "user-3" in subscribers
    
    def test_get_subscribers_empty(self, app, db_session):
        """Should return empty list for tournament with no subscribers."""
        with app.app_context():
            manager = SubscriptionManager()
            subscribers = manager.get_tournament_subscribers("no-subscribers")
            
            assert subscribers == []


class TestIsSubscribed:
    """Tests for is_subscribed method."""
    
    def test_is_subscribed_true(self, app, db_session):
        """Should return True when subscribed."""
        with app.app_context():
            manager = SubscriptionManager()
            manager.subscribe("user-1", "tournament-1")
            
            assert manager.is_subscribed("user-1", "tournament-1") is True
    
    def test_is_subscribed_false(self, app, db_session):
        """Should return False when not subscribed."""
        with app.app_context():
            manager = SubscriptionManager()
            
            assert manager.is_subscribed("user-1", "tournament-1") is False
    
    def test_is_subscribed_after_unsubscribe(self, app, db_session):
        """Should return False after unsubscribing."""
        with app.app_context():
            manager = SubscriptionManager()
            manager.subscribe("user-1", "tournament-1")
            manager.unsubscribe("user-1", "tournament-1")
            
            assert manager.is_subscribed("user-1", "tournament-1") is False


class TestGetSubscribersForEvent:
    """Tests for get_subscribers_for_event method."""
    
    def test_tournament_started_event(self, app, db_session):
        """Should return subscribers with notify_on_start enabled."""
        with app.app_context():
            manager = SubscriptionManager()
            
            manager.subscribe("user-1", "tournament-1", notify_on_start=True)
            manager.subscribe("user-2", "tournament-1", notify_on_start=False)
            manager.subscribe("user-3", "tournament-1", notify_on_start=True)
            
            subscribers = manager.get_subscribers_for_event(
                "tournament-1",
                "tournament.started"
            )
            
            assert len(subscribers) == 2
            assert "user-1" in subscribers
            assert "user-3" in subscribers
            assert "user-2" not in subscribers
    
    def test_match_result_event(self, app, db_session):
        """Should return subscribers with notify_on_match enabled."""
        with app.app_context():
            manager = SubscriptionManager()
            
            manager.subscribe("user-1", "tournament-1", notify_on_match=True)
            manager.subscribe("user-2", "tournament-1", notify_on_match=False)
            
            subscribers = manager.get_subscribers_for_event(
                "tournament-1",
                "match.result"
            )
            
            assert len(subscribers) == 1
            assert "user-1" in subscribers
    
    def test_tournament_completed_event(self, app, db_session):
        """Should return subscribers with notify_on_complete enabled."""
        with app.app_context():
            manager = SubscriptionManager()
            
            manager.subscribe("user-1", "tournament-1", notify_on_complete=True)
            manager.subscribe("user-2", "tournament-1", notify_on_complete=False)
            
            subscribers = manager.get_subscribers_for_event(
                "tournament-1",
                "tournament.completed"
            )
            
            assert len(subscribers) == 1
            assert "user-1" in subscribers
    
    def test_unknown_event_returns_all(self, app, db_session):
        """Unknown event type should return all subscribers."""
        with app.app_context():
            manager = SubscriptionManager()
            
            manager.subscribe("user-1", "tournament-1")
            manager.subscribe("user-2", "tournament-1")
            manager.subscribe("user-3", "tournament-1")
            
            subscribers = manager.get_subscribers_for_event(
                "tournament-1",
                "unknown.event"
            )
            
            assert len(subscribers) == 3
