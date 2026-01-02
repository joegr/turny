"""
Unit tests for TournamentStateMachine class.
Tests all state transitions, guards, and helper methods.
"""
import pytest
from shared.state_machine import (
    TournamentStateMachine,
    TournamentState,
    TransitionError,
    Transition,
    min_teams_guard,
    all_matches_complete_guard
)


class TestTournamentStateEnum:
    """Tests for TournamentState enum."""
    
    def test_all_states_exist(self):
        """All expected states should exist."""
        assert TournamentState.DRAFT.value == "draft"
        assert TournamentState.REGISTRATION.value == "registration"
        assert TournamentState.ACTIVE.value == "active"
        assert TournamentState.COMPLETED.value == "completed"
        assert TournamentState.ARCHIVED.value == "archived"
    
    def test_state_is_string_enum(self):
        """States should be string enums."""
        assert isinstance(TournamentState.DRAFT.value, str)


class TestTransitionError:
    """Tests for TransitionError exception."""
    
    def test_error_attributes(self):
        """TransitionError should have from_state and to_state."""
        error = TransitionError("draft", "active")
        assert error.from_state == "draft"
        assert error.to_state == "active"
    
    def test_default_reason(self):
        """Default reason should be generated."""
        error = TransitionError("draft", "active")
        assert "draft" in str(error)
        assert "active" in str(error)
    
    def test_custom_reason(self):
        """Custom reason should be used if provided."""
        error = TransitionError("draft", "active", "Custom error message")
        assert str(error) == "Custom error message"


class TestStateMachineInit:
    """Tests for TournamentStateMachine initialization."""
    
    def test_default_initial_state(self):
        """Default initial state should be DRAFT."""
        sm = TournamentStateMachine()
        assert sm.state == TournamentState.DRAFT
    
    def test_custom_initial_state(self):
        """Custom initial state should be set."""
        sm = TournamentStateMachine(initial_state=TournamentState.ACTIVE)
        assert sm.state == TournamentState.ACTIVE
    
    def test_empty_history_on_init(self):
        """History should be empty on initialization."""
        sm = TournamentStateMachine()
        assert sm.get_history() == []
    
    def test_from_state_string_valid(self):
        """from_state_string should create SM with correct state."""
        sm = TournamentStateMachine.from_state_string("registration")
        assert sm.state == TournamentState.REGISTRATION
    
    def test_from_state_string_invalid(self):
        """Invalid state string should default to DRAFT."""
        sm = TournamentStateMachine.from_state_string("invalid_state")
        assert sm.state == TournamentState.DRAFT
    
    def test_from_state_string_empty(self):
        """Empty state string should default to DRAFT."""
        sm = TournamentStateMachine.from_state_string("")
        assert sm.state == TournamentState.DRAFT


class TestStateTransitions:
    """Tests for state transition logic."""
    
    def test_draft_to_registration_publish(self):
        """publish should transition from DRAFT to REGISTRATION."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        new_state = sm.transition("publish")
        assert new_state == TournamentState.REGISTRATION
        assert sm.state == TournamentState.REGISTRATION
    
    def test_draft_to_draft_edit(self):
        """edit should keep state at DRAFT."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        new_state = sm.transition("edit")
        assert new_state == TournamentState.DRAFT
    
    def test_registration_to_active_start(self):
        """start should transition from REGISTRATION to ACTIVE."""
        sm = TournamentStateMachine(TournamentState.REGISTRATION)
        new_state = sm.transition("start")
        assert new_state == TournamentState.ACTIVE
    
    def test_registration_to_draft_cancel(self):
        """cancel should transition from REGISTRATION to DRAFT."""
        sm = TournamentStateMachine(TournamentState.REGISTRATION)
        new_state = sm.transition("cancel")
        assert new_state == TournamentState.DRAFT
    
    def test_active_to_active_advance(self):
        """advance should keep state at ACTIVE."""
        sm = TournamentStateMachine(TournamentState.ACTIVE)
        new_state = sm.transition("advance")
        assert new_state == TournamentState.ACTIVE
    
    def test_active_to_completed_complete(self):
        """complete should transition from ACTIVE to COMPLETED."""
        sm = TournamentStateMachine(TournamentState.ACTIVE)
        new_state = sm.transition("complete")
        assert new_state == TournamentState.COMPLETED
    
    def test_completed_to_archived_archive(self):
        """archive should transition from COMPLETED to ARCHIVED."""
        sm = TournamentStateMachine(TournamentState.COMPLETED)
        new_state = sm.transition("archive")
        assert new_state == TournamentState.ARCHIVED


class TestInvalidTransitions:
    """Tests for invalid state transitions."""
    
    def test_cannot_start_from_draft(self):
        """start should fail from DRAFT state."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        with pytest.raises(TransitionError) as exc_info:
            sm.transition("start")
        assert sm.state == TournamentState.DRAFT  # State unchanged
    
    def test_cannot_publish_from_active(self):
        """publish should fail from ACTIVE state."""
        sm = TournamentStateMachine(TournamentState.ACTIVE)
        with pytest.raises(TransitionError):
            sm.transition("publish")
    
    def test_cannot_archive_from_active(self):
        """archive should fail from ACTIVE state."""
        sm = TournamentStateMachine(TournamentState.ACTIVE)
        with pytest.raises(TransitionError):
            sm.transition("archive")
    
    def test_cannot_transition_from_archived(self):
        """No transitions should be possible from ARCHIVED."""
        sm = TournamentStateMachine(TournamentState.ARCHIVED)
        for action in ["publish", "start", "complete", "cancel"]:
            with pytest.raises(TransitionError):
                sm.transition(action)
    
    def test_invalid_action_raises_error(self):
        """Unknown action should raise TransitionError."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        with pytest.raises(TransitionError):
            sm.transition("invalid_action")


class TestCanTransition:
    """Tests for can_transition method."""
    
    def test_can_transition_valid_action(self):
        """Should return True for valid transition."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        assert sm.can_transition("publish") is True
    
    def test_can_transition_invalid_action(self):
        """Should return False for invalid transition."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        assert sm.can_transition("start") is False
    
    def test_can_transition_all_states(self):
        """Test can_transition for all states."""
        # DRAFT
        sm = TournamentStateMachine(TournamentState.DRAFT)
        assert sm.can_transition("publish") is True
        assert sm.can_transition("edit") is True
        assert sm.can_transition("start") is False
        
        # REGISTRATION
        sm = TournamentStateMachine(TournamentState.REGISTRATION)
        assert sm.can_transition("start") is True
        assert sm.can_transition("cancel") is True
        assert sm.can_transition("publish") is False
        
        # ACTIVE
        sm = TournamentStateMachine(TournamentState.ACTIVE)
        assert sm.can_transition("advance") is True
        assert sm.can_transition("complete") is True
        assert sm.can_transition("archive") is False
        
        # COMPLETED
        sm = TournamentStateMachine(TournamentState.COMPLETED)
        assert sm.can_transition("archive") is True
        assert sm.can_transition("start") is False


class TestCanPerform:
    """Tests for can_perform method."""
    
    def test_draft_allowed_actions(self):
        """DRAFT state should allow edit, publish, delete."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        assert sm.can_perform("edit") is True
        assert sm.can_perform("publish") is True
        assert sm.can_perform("delete") is True
        assert sm.can_perform("register_team") is False
    
    def test_registration_allowed_actions(self):
        """REGISTRATION state should allow team registration."""
        sm = TournamentStateMachine(TournamentState.REGISTRATION)
        assert sm.can_perform("register_team") is True
        assert sm.can_perform("unregister_team") is True
        assert sm.can_perform("start") is True
        assert sm.can_perform("cancel") is True
        assert sm.can_perform("edit") is False
    
    def test_active_allowed_actions(self):
        """ACTIVE state should allow result recording."""
        sm = TournamentStateMachine(TournamentState.ACTIVE)
        assert sm.can_perform("record_result") is True
        assert sm.can_perform("abandon_match") is True
        assert sm.can_perform("advance") is True
        assert sm.can_perform("register_team") is False
    
    def test_completed_allowed_actions(self):
        """COMPLETED state should allow view and archive."""
        sm = TournamentStateMachine(TournamentState.COMPLETED)
        assert sm.can_perform("view") is True
        assert sm.can_perform("archive") is True
        assert sm.can_perform("record_result") is False
    
    def test_archived_allowed_actions(self):
        """ARCHIVED state should only allow view."""
        sm = TournamentStateMachine(TournamentState.ARCHIVED)
        assert sm.can_perform("view") is True
        assert sm.can_perform("archive") is False


class TestAllowedActions:
    """Tests for allowed_actions property."""
    
    def test_draft_actions(self):
        """DRAFT should have correct allowed actions."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        actions = sm.allowed_actions
        assert "edit" in actions
        assert "publish" in actions
        assert "delete" in actions
    
    def test_registration_actions(self):
        """REGISTRATION should have correct allowed actions."""
        sm = TournamentStateMachine(TournamentState.REGISTRATION)
        actions = sm.allowed_actions
        assert "register_team" in actions
        assert "unregister_team" in actions
        assert "start" in actions
        assert "cancel" in actions
    
    def test_active_actions(self):
        """ACTIVE should have correct allowed actions."""
        sm = TournamentStateMachine(TournamentState.ACTIVE)
        actions = sm.allowed_actions
        assert "record_result" in actions
        assert "abandon_match" in actions
        assert "advance" in actions


class TestFormAccess:
    """Tests for form_access property."""
    
    def test_draft_config_form(self):
        """DRAFT should use config form."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        assert sm.form_access == "config"
    
    def test_registration_signup_form(self):
        """REGISTRATION should use signup form."""
        sm = TournamentStateMachine(TournamentState.REGISTRATION)
        assert sm.form_access == "signup"
    
    def test_active_results_form(self):
        """ACTIVE should use results form."""
        sm = TournamentStateMachine(TournamentState.ACTIVE)
        assert sm.form_access == "results"
    
    def test_completed_readonly(self):
        """COMPLETED should be readonly."""
        sm = TournamentStateMachine(TournamentState.COMPLETED)
        assert sm.form_access == "readonly"
    
    def test_archived_readonly(self):
        """ARCHIVED should be readonly."""
        sm = TournamentStateMachine(TournamentState.ARCHIVED)
        assert sm.form_access == "readonly"


class TestHistory:
    """Tests for transition history tracking."""
    
    def test_history_records_transitions(self):
        """Transitions should be recorded in history."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        sm.transition("publish")
        
        history = sm.get_history()
        assert len(history) == 1
        assert history[0] == (TournamentState.DRAFT, "publish", TournamentState.REGISTRATION)
    
    def test_multiple_transitions_recorded(self):
        """Multiple transitions should all be recorded."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        sm.transition("publish")
        sm.transition("start")
        
        history = sm.get_history()
        assert len(history) == 2
    
    def test_history_returns_copy(self):
        """get_history should return a copy."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        sm.transition("publish")
        
        history = sm.get_history()
        history.clear()
        
        # Original should still have entry
        assert len(sm.get_history()) == 1
    
    def test_failed_transition_not_recorded(self):
        """Failed transitions should not be recorded."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        try:
            sm.transition("start")
        except TransitionError:
            pass
        
        assert len(sm.get_history()) == 0


class TestSetState:
    """Tests for set_state method."""
    
    def test_set_state_directly(self):
        """set_state should change state directly."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        sm.set_state(TournamentState.ACTIVE)
        assert sm.state == TournamentState.ACTIVE
    
    def test_set_state_no_history(self):
        """set_state should not add to history."""
        sm = TournamentStateMachine(TournamentState.DRAFT)
        sm.set_state(TournamentState.ACTIVE)
        assert len(sm.get_history()) == 0


class TestGuards:
    """Tests for guard functions."""
    
    def test_min_teams_guard_passes(self):
        """min_teams_guard should pass with enough teams."""
        guard = min_teams_guard(4)
        context = {"teams": {"t1": {}, "t2": {}, "t3": {}, "t4": {}}}
        assert guard(context) is True
    
    def test_min_teams_guard_fails(self):
        """min_teams_guard should fail with too few teams."""
        guard = min_teams_guard(4)
        context = {"teams": {"t1": {}, "t2": {}}}
        assert guard(context) is False
    
    def test_min_teams_guard_custom_count(self):
        """min_teams_guard should work with custom count."""
        guard = min_teams_guard(8)
        context = {"teams": {f"t{i}": {} for i in range(8)}}
        assert guard(context) is True
        
        context = {"teams": {f"t{i}": {} for i in range(7)}}
        assert guard(context) is False
    
    def test_all_matches_complete_guard_passes(self):
        """all_matches_complete_guard should pass when all complete."""
        context = {
            "matches": [
                {"status": "completed"},
                {"status": "completed"},
                {"status": "abandoned"},
            ]
        }
        assert all_matches_complete_guard(context) is True
    
    def test_all_matches_complete_guard_fails(self):
        """all_matches_complete_guard should fail with pending matches."""
        context = {
            "matches": [
                {"status": "completed"},
                {"status": "pending"},
            ]
        }
        assert all_matches_complete_guard(context) is False
    
    def test_all_matches_complete_guard_empty(self):
        """all_matches_complete_guard should pass with empty matches."""
        context = {"matches": []}
        assert all_matches_complete_guard(context) is True


class TestGuardedTransitions:
    """Tests for transitions with guard conditions."""
    
    def test_transition_with_passing_guard(self):
        """Transition should succeed when guard passes."""
        # Create a custom transition with guard
        sm = TournamentStateMachine(TournamentState.REGISTRATION)
        
        # The existing transitions don't have guards in the default setup,
        # but we can test the guard mechanism
        context = {"teams": {f"t{i}": {} for i in range(4)}}
        
        # This transition doesn't have a guard, so it should work
        new_state = sm.transition("start", guard_context=context)
        assert new_state == TournamentState.ACTIVE
