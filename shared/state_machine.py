from enum import Enum
from typing import Optional, Callable, List
from dataclasses import dataclass


class TournamentState(str, Enum):
    DRAFT = "draft"
    REGISTRATION = "registration"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TransitionError(Exception):
    def __init__(self, from_state: str, to_state: str, reason: str = None):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason or f"Cannot transition from {from_state} to {to_state}"
        super().__init__(self.reason)


@dataclass
class Transition:
    from_state: TournamentState
    to_state: TournamentState
    action: str
    guard: Optional[Callable] = None


class TournamentStateMachine:
    TRANSITIONS = [
        Transition(TournamentState.DRAFT, TournamentState.REGISTRATION, "publish"),
        Transition(TournamentState.DRAFT, TournamentState.DRAFT, "edit"),
        Transition(TournamentState.REGISTRATION, TournamentState.ACTIVE, "start"),
        Transition(TournamentState.REGISTRATION, TournamentState.DRAFT, "cancel"),
        Transition(TournamentState.ACTIVE, TournamentState.ACTIVE, "advance"),
        Transition(TournamentState.ACTIVE, TournamentState.COMPLETED, "complete"),
        Transition(TournamentState.COMPLETED, TournamentState.ARCHIVED, "archive"),
    ]
    
    ALLOWED_ACTIONS = {
        TournamentState.DRAFT: ["edit", "publish", "delete"],
        TournamentState.REGISTRATION: ["register_team", "unregister_team", "start", "cancel"],
        TournamentState.ACTIVE: ["record_result", "abandon_match", "advance"],
        TournamentState.COMPLETED: ["view", "archive"],
        TournamentState.ARCHIVED: ["view"],
    }
    
    FORM_ACCESS = {
        TournamentState.DRAFT: "config",
        TournamentState.REGISTRATION: "signup",
        TournamentState.ACTIVE: "results",
        TournamentState.COMPLETED: "readonly",
        TournamentState.ARCHIVED: "readonly",
    }
    
    def __init__(self, initial_state: TournamentState = TournamentState.DRAFT):
        self._state = initial_state
        self._history: List[tuple] = []
    
    @property
    def state(self) -> TournamentState:
        return self._state
    
    @property
    def form_access(self) -> str:
        return self.FORM_ACCESS.get(self._state, "readonly")
    
    @property
    def allowed_actions(self) -> List[str]:
        return self.ALLOWED_ACTIONS.get(self._state, [])
    
    def can_transition(self, action: str) -> bool:
        for t in self.TRANSITIONS:
            if t.from_state == self._state and t.action == action:
                return True
        return False
    
    def can_perform(self, action: str) -> bool:
        return action in self.allowed_actions
    
    def transition(self, action: str, guard_context: dict = None) -> TournamentState:
        for t in self.TRANSITIONS:
            if t.from_state == self._state and t.action == action:
                if t.guard and guard_context:
                    if not t.guard(guard_context):
                        raise TransitionError(
                            self._state.value, 
                            t.to_state.value,
                            f"Guard condition failed for action '{action}'"
                        )
                
                old_state = self._state
                self._state = t.to_state
                self._history.append((old_state, action, self._state))
                return self._state
        
        raise TransitionError(
            self._state.value,
            "unknown",
            f"No valid transition for action '{action}' from state '{self._state.value}'"
        )
    
    def set_state(self, state: TournamentState):
        self._state = state
    
    def get_history(self) -> List[tuple]:
        return self._history.copy()
    
    @classmethod
    def from_state_string(cls, state_str: str) -> "TournamentStateMachine":
        try:
            state = TournamentState(state_str)
        except ValueError:
            state = TournamentState.DRAFT
        return cls(initial_state=state)


def min_teams_guard(min_count: int = 4):
    def guard(context: dict) -> bool:
        teams = context.get("teams", {})
        return len(teams) >= min_count
    return guard


def all_matches_complete_guard(context: dict) -> bool:
    matches = context.get("matches", [])
    return all(m.get("status") in ["completed", "abandoned"] for m in matches)
