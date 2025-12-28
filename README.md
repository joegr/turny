# Tournament Manager

A Flask-based tournament management system with Redis backend and vanilla JavaScript frontend. Features time-based deterministic automation for sequential rounds with automatic handling of abandoned matches.

## Features

- **Team Registration**: Captains register teams with minimal data (username + team name)
- **Tournament Automation**: Time-based deterministic round progression
- **Abandoned Match Handling**: Timed-out matches result in losses for both teams (neither advances)
- **Real-time Updates**: Frontend polls for state changes every 5 seconds
- **Redis Persistence**: All tournament data stored in Redis
- **Docker Wrapped**: Complete containerized deployment

## Architecture

- **Backend**: Flask + Redis
- **Frontend**: Vanilla JavaScript (no frameworks)
- **Deployment**: Docker + Docker Compose
- **Round Duration**: 5 minutes per round (configurable in code)

## Quick Start

### Prerequisites
- Docker
- Docker Compose

### Running the Application

1. Build and start the containers:
```bash
docker-compose up --build
```

2. Access the application at `http://localhost:5000`

### Development Mode

For local development without Docker:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start Redis:
```bash
docker run -p 6379:6379 redis:7-alpine
```

3. Run the Flask app:
```bash
python app.py
```

## API Endpoints

### Tournament State
- `GET /api/tournament/state` - Get current tournament status
- `POST /api/tournament/start` - Start the tournament

### Teams
- `GET /api/teams` - List all registered teams
- `POST /api/teams/register` - Register a new team
  ```json
  {
    "captain_name": "string",
    "team_name": "string"
  }
  ```

### Matches
- `GET /api/matches` - Get current round matches
- `POST /api/matches/<match_id>/result` - Record match result
  ```json
  {
    "winner": "team_id"
  }
  ```

### Automation
- `POST /api/tournament/auto-advance` - Check and advance tournament if time expired

## Tournament Flow

1. **Registration Phase**: Teams register via the web interface
2. **Tournament Start**: Admin starts tournament (minimum 2 teams required)
3. **Round Execution**: 
   - Matches are created deterministically
   - Each round has a 5-minute time limit
   - Results can be manually recorded
4. **Auto-Advancement**:
   - System checks every 10 seconds if round time expired
   - Abandoned matches mark both teams with losses
   - Neither team advances to next round
   - Tournament continues with only winning teams
5. **Completion**: Tournament ends when one team remains or all matches abandoned

## Configuration

Edit `app.py` to modify:
- `round_duration = 300` (line 122) - Time per round in seconds
- Redis connection settings via environment variables:
  - `REDIS_HOST` (default: localhost)
  - `REDIS_PORT` (default: 6379)

## Data Model

### Tournament State
```json
{
  "status": "registration|active|completed",
  "round": 0,
  "winner": "team_id|null"
}
```

### Team
```json
{
  "captain": "string",
  "name": "string",
  "wins": 0,
  "losses": 0
}
```

### Match
```json
{
  "id": "match_1",
  "team1": "team_id",
  "team2": "team_id",
  "winner": "team_id|null",
  "status": "pending|completed|abandoned"
}
```

## Abandoned Match Logic

When a round times out:
1. All pending matches are marked as "abandoned"
2. Both teams in abandoned matches receive a loss
3. Neither team advances to the next round
4. Only teams with completed match wins advance
5. If all matches are abandoned, tournament ends with no winner

## Frontend Features

- Real-time tournament state display
- Team registration form
- Live match results
- Auto-refresh every 5 seconds
- Manual result recording buttons
- Winner announcement

## License

MIT
