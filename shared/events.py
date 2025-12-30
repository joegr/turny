from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Any
import json


class EventType(str, Enum):
    # Tournament lifecycle
    TOURNAMENT_CREATED = "tournament.created"
    TOURNAMENT_PUBLISHED = "tournament.published"
    TOURNAMENT_STARTED = "tournament.started"
    TOURNAMENT_COMPLETED = "tournament.completed"
    TOURNAMENT_ARCHIVED = "tournament.archived"
    
    # State changes
    STATE_CHANGED = "state.changed"
    
    # Team events
    TEAM_REGISTERED = "team.registered"
    TEAM_UNREGISTERED = "team.unregistered"
    
    # Match events
    MATCH_CREATED = "match.created"
    MATCH_RESULT = "match.result"
    MATCH_ABANDONED = "match.abandoned"
    
    # Round events
    ROUND_STARTED = "round.started"
    ROUND_COMPLETED = "round.completed"
    
    # User notifications
    MATCH_READY = "notification.match_ready"
    TOURNAMENT_STARTING = "notification.tournament_starting"
    TOURNAMENT_REMINDER = "notification.tournament_reminder"


@dataclass
class Event:
    type: EventType
    tournament_id: str
    timestamp: str = None
    data: dict = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
        if self.data is None:
            self.data = {}
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value if isinstance(self.type, EventType) else self.type,
            "tournament_id": self.tournament_id,
            "timestamp": self.timestamp,
            "data": self.data
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        return cls(
            type=EventType(data["type"]) if data["type"] in [e.value for e in EventType] else data["type"],
            tournament_id=data["tournament_id"],
            timestamp=data.get("timestamp"),
            data=data.get("data", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        return cls.from_dict(json.loads(json_str))


def state_changed_event(tournament_id: str, from_state: str, to_state: str) -> Event:
    return Event(
        type=EventType.STATE_CHANGED,
        tournament_id=tournament_id,
        data={
            "from_state": from_state,
            "to_state": to_state
        }
    )


def match_result_event(tournament_id: str, match_id: str, winner: str, round_num: int) -> Event:
    return Event(
        type=EventType.MATCH_RESULT,
        tournament_id=tournament_id,
        data={
            "match_id": match_id,
            "winner": winner,
            "round": round_num
        }
    )


def round_started_event(tournament_id: str, round_num: int, matches_count: int) -> Event:
    return Event(
        type=EventType.ROUND_STARTED,
        tournament_id=tournament_id,
        data={
            "round": round_num,
            "matches_count": matches_count
        }
    )


def tournament_completed_event(tournament_id: str, winner: str, tournament_type: str) -> Event:
    return Event(
        type=EventType.TOURNAMENT_COMPLETED,
        tournament_id=tournament_id,
        data={
            "winner": winner,
            "tournament_type": tournament_type
        }
    )
