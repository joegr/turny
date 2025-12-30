# Tournament Platform Architecture

## Overview

The platform follows a microservices architecture where each tournament runs on its own isolated server instance. A central orchestrator manages tournament lifecycle, and Redis pub/sub enables real-time event broadcasting to subscribed users.

**Status: ✅ IMPLEMENTED**

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GATEWAY / ORCHESTRATOR                       │
│                              (Port 5000)                             │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │ Tournament      │  │ User Service     │  │ Subscription      │  │
│  │ Registry        │  │ (auth, profiles) │  │ Manager           │  │
│  └─────────────────┘  └──────────────────┘  └───────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  Tournament   │       │  Tournament   │       │  Tournament   │
│  Server 1     │       │  Server 2     │       │  Server N     │
│  (Port 6001)  │       │  (Port 6002)  │       │  (Port 600N)  │
│               │       │               │       │               │
│ State Machine │       │ State Machine │       │ State Machine │
│ Match Engine  │       │ Match Engine  │       │ Match Engine  │
└───────┬───────┘       └───────┬───────┘       └───────┬───────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          REDIS PUB/SUB                               │
│  Channels:                                                           │
│  ├── tournament:{id}:events    (state changes, match results)       │
│  ├── tournament:{id}:chat      (tournament chat)                    │
│  ├── user:{id}:notifications   (personal alerts)                    │
│  └── global:announcements      (new tournaments, results)           │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           POSTGRESQL                                 │
│  Tables: tournaments, teams, subscriptions                          │
└─────────────────────────────────────────────────────────────────────┘
```

## Tournament State Machine

```
    ┌──────────────┐
    │  DRAFT       │  (Tournament created, configuring)
    └──────┬───────┘
           │ publish()
           ▼
    ┌──────────────┐
    │ REGISTRATION │  (Accepting team signups)
    └──────┬───────┘
           │ start() [min teams met]
           ▼
    ┌──────────────┐
    │   ACTIVE     │  (Matches in progress)
    │              │◄─────────────────┐
    └──────┬───────┘                  │
           │ advance() [round complete]
           │                          │
           ├──────────────────────────┘
           │ [final round complete]
           ▼
    ┌──────────────┐
    │  COMPLETED   │  (Tournament finished, winner declared)
    └──────┬───────┘
           │ archive()
           ▼
    ┌──────────────┐
    │  ARCHIVED    │  (Read-only historical record)
    └──────────────┘
```

### State Transitions & Form Access

| Current State | Allowed Actions | Form Access |
|---------------|-----------------|-------------|
| DRAFT | edit, publish, delete | Config form only |
| REGISTRATION | register_team, unregister, start, cancel | Team signup form |
| ACTIVE | record_result, abandon_match | **Results form (primary)** |
| COMPLETED | view, archive | Read-only |
| ARCHIVED | view | Read-only |

## Pub/Sub Event Types

### Tournament Events (`tournament:{id}:events`)
```json
{
  "type": "state_changed",
  "tournament_id": "t_123",
  "from_state": "REGISTRATION",
  "to_state": "ACTIVE",
  "timestamp": "2025-12-29T19:00:00Z"
}

{
  "type": "match_result",
  "tournament_id": "t_123",
  "match_id": "r1_match_1",
  "winner": "team_5",
  "round": 1,
  "timestamp": "2025-12-29T19:15:00Z"
}

{
  "type": "round_advanced",
  "tournament_id": "t_123",
  "new_round": 2,
  "matches_count": 2,
  "timestamp": "2025-12-29T19:30:00Z"
}
```

### User Notifications (`user:{id}:notifications`)
```json
{
  "type": "tournament_starting",
  "tournament_id": "t_123",
  "tournament_name": "Summer Championship",
  "starts_in_minutes": 5
}

{
  "type": "match_ready",
  "tournament_id": "t_123",
  "match_id": "r1_match_3",
  "opponent": "Fierce Dragons",
  "team_id": "team_7"
}
```

## Service Responsibilities

### Orchestrator (Gateway)
- Tournament registry (CRUD)
- Spin up/down tournament server containers
- Route requests to appropriate tournament server
- User authentication
- Subscription management
- Aggregate views (all tournaments, leaderboards)

### Tournament Server
- Owns single tournament's state
- Enforces state machine transitions
- Manages matches and results
- Publishes events to Redis
- Namespaced Redis keys: `t:{id}:*`

### Results Form (Primary Engagement)
- **Only enabled when tournament state is ACTIVE**
- **Only shows pending matches for current round**
- Real-time updates via WebSocket/SSE
- Optimistic UI with rollback on failure
- Clear visual feedback for state changes

## Directory Structure

```
windsurf-project-4/
├── orchestrator/                    # ✅ Gateway Service
│   ├── __init__.py
│   ├── app.py                       # Flask app factory + routes
│   ├── config.py                    # Configuration classes
│   ├── models.py                    # SQLAlchemy models (Tournament, Team, Subscription)
│   ├── tournament_registry.py       # Tournament lifecycle + service spawning
│   ├── subscription_manager.py      # User subscription management
│   └── templates/
│       ├── base.html                # Base template with nav + SSE
│       ├── home.html                # Dashboard with stats
│       ├── tournaments.html         # Tournament list with filters
│       ├── tournament_detail.html   # Single tournament management
│       ├── tournament_form.html     # Create tournament form
│       ├── dashboard.html           # User subscriptions
│       ├── 404.html
│       └── tournament_not_started.html
│
├── tournament_service/              # ✅ Per-Tournament Service
│   ├── __init__.py
│   ├── app.py                       # Tournament server (spawned per tournament)
│   ├── match_engine.py              # Match creation, results, advancement
│   └── templates/
│       └── results_form.html        # Live match results UI
│
├── shared/                          # ✅ Shared Components
│   ├── __init__.py
│   ├── events.py                    # Event type definitions
│   ├── pubsub.py                    # Redis pub/sub client
│   └── state_machine.py             # Tournament state machine
│
├── run.py                           # Entry point (orchestrator | tournament)
├── docker-compose.yml               # Multi-service orchestration
├── Dockerfile.orchestrator
├── Dockerfile.tournament
├── requirements.txt
└── ARCHITECTURE.md
```

## Implementation Phases

### Phase 1: State Machine & Events ✅
- [x] Implement tournament state machine (`shared/state_machine.py`)
- [x] Define event types and schemas (`shared/events.py`)
- [x] Set up Redis pub/sub infrastructure (`shared/pubsub.py`)

### Phase 2: Orchestrator Service ✅
- [x] Tournament CRUD API (`/api/v1/tournaments`)
- [x] User subscription management (`/api/v1/subscriptions`)
- [x] Service registry (`orchestrator/tournament_registry.py`)

### Phase 3: Tournament Service ✅
- [x] Per-tournament server template (`tournament_service/app.py`)
- [x] Dynamic subprocess spawning (Docker support ready)
- [x] Match engine with state validation (`tournament_service/match_engine.py`)

### Phase 4: Results Form (Primary UI) ✅
- [x] State-aware form rendering (signup/results/readonly modes)
- [x] Real-time updates via SSE
- [x] Interactive match result recording

### Phase 5: Notifications & Alerts ✅
- [x] SSE connections (`/api/v1/events/global`, `/api/v1/events/user/:id`)
- [ ] Push notification integration (future)
- [ ] Email alerts (future)

## Quick Start

```bash
# Start infrastructure
docker-compose up -d postgres redis

# Install dependencies
pip install -r requirements.txt

# Run orchestrator
python run.py orchestrator

# Access at http://localhost:5000
```

## API Endpoints

### Orchestrator (Port 5000)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tournaments` | List tournaments |
| POST | `/api/v1/tournaments` | Create tournament |
| GET | `/api/v1/tournaments/:id` | Get tournament |
| POST | `/api/v1/tournaments/:id/publish` | Publish & spawn service |
| POST | `/api/v1/tournaments/:id/archive` | Archive tournament |
| GET | `/api/v1/tournaments/:id/teams` | List teams |
| POST | `/api/v1/tournaments/:id/teams` | Register team |
| POST | `/api/v1/subscriptions` | Subscribe to tournament |
| GET | `/api/v1/events/global` | SSE global events |
| GET | `/api/v1/events/user/:id` | SSE user events |

### Tournament Service (Port 600X)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/state` | Get tournament state |
| GET | `/api/teams` | List teams |
| POST | `/api/teams` | Register team |
| GET | `/api/matches` | Get current matches |
| POST | `/api/matches/:id/result` | Record match result |
| GET | `/api/standings` | Get standings |
| POST | `/api/start` | Start tournament |
| GET | `/api/events` | SSE tournament events |
