from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Tournament(db.Model):
    __tablename__ = 'tournaments'
    
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    tournament_type = db.Column(db.String(50), nullable=False, default='single_elimination')
    status = db.Column(db.String(20), nullable=False, default='draft')
    current_round = db.Column(db.Integer, default=0)
    max_teams = db.Column(db.Integer, default=16)
    min_teams = db.Column(db.Integer, default=4)
    
    # Group/Hybrid tournament settings
    num_groups = db.Column(db.Integer, default=0)  # 0 = no groups
    group_stage_rounds = db.Column(db.Integer, default=3)  # Rounds per group (round robin)
    knockout_type = db.Column(db.String(50), default='single_elimination')  # For hybrid: knockout stage type
    teams_per_group_advance = db.Column(db.Integer, default=2)  # How many teams advance from each group
    allow_draws = db.Column(db.Boolean, default=False)  # Football-style draws allowed
    
    # Service instance info (Monolith: deprecated but kept for compatibility or future scaling)
    service_port = db.Column(db.Integer, nullable=True)
    service_host = db.Column(db.String(100), nullable=True)
    container_id = db.Column(db.String(100), nullable=True)
    service_url = db.Column(db.String(200), nullable=True) # Used for internal routing now
    
    # Results
    winner_team_id = db.Column(db.String(50), nullable=True)
    
    # Timestamps
    scheduled_start = db.Column(db.DateTime, nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    teams = db.relationship('Team', back_populates='tournament', cascade='all, delete-orphan')
    matches = db.relationship('Match', back_populates='tournament', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'tournament_id': self.tournament_id,
            'name': self.name,
            'tournament_type': self.tournament_type,
            'status': self.status,
            'current_round': self.current_round,
            'max_teams': self.max_teams,
            'min_teams': self.min_teams,
            'num_groups': self.num_groups,
            'group_stage_rounds': self.group_stage_rounds,
            'knockout_type': self.knockout_type,
            'teams_per_group_advance': self.teams_per_group_advance,
            'allow_draws': self.allow_draws,
            'team_count': len(self.teams),
            'winner_team_id': self.winner_team_id,
            'service_url': self.service_url_prop,
            'scheduled_start': self.scheduled_start.isoformat() if self.scheduled_start else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    @property
    def service_url_prop(self):
        # Return internal URL if set, otherwise construct from host/port (legacy)
        if self.service_url:
            return self.service_url
        if self.service_host and self.service_port:
            return f"http://{self.service_host}:{self.service_port}"
        return None


class Team(db.Model):
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.String(50), nullable=False, index=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    captain = db.Column(db.String(100), nullable=False)
    group_name = db.Column(db.String(50), nullable=True)  # e.g., 'A', 'B', 'C', 'D'
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)  # Football: 3 for win, 1 for draw, 0 for loss
    goals_for = db.Column(db.Integer, default=0)  # Optional: for goal difference tiebreaker
    goals_against = db.Column(db.Integer, default=0)
    elo_rating = db.Column(db.Integer, default=1500)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tournament = db.relationship('Tournament', back_populates='teams')
    elo_history = db.relationship('EloHistory', back_populates='team', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('team_id', 'tournament_id', name='unique_team_per_tournament'),
    )
    
    def to_dict(self):
        return {
            'team_id': self.team_id,
            'name': self.name,
            'captain': self.captain,
            'wins': self.wins,
            'losses': self.losses,
            'draws': self.draws,
            'points': self.points,
            'goals_for': self.goals_for,
            'goals_against': self.goals_against,
            'goal_difference': self.goals_for - self.goals_against,
            'group': self.group_name,
            'elo_rating': self.elo_rating,
        }


class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.String(50), nullable=False, index=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    round_num = db.Column(db.Integer, nullable=False)
    
    team1_id = db.Column(db.String(50), nullable=True)
    team2_id = db.Column(db.String(50), nullable=True)
    winner_id = db.Column(db.String(50), nullable=True)
    is_draw = db.Column(db.Boolean, default=False)  # Football-style draw
    
    # Scores (for football-style)
    team1_score = db.Column(db.Integer, nullable=True)
    team2_score = db.Column(db.Integer, nullable=True)
    
    # Group/Stage info
    group_name = db.Column(db.String(50), nullable=True)  # Which group this match belongs to
    stage = db.Column(db.String(50), default='knockout')  # 'group' or 'knockout'
    
    # ELO-based win probabilities
    team1_win_probability = db.Column(db.Float, nullable=True)
    team2_win_probability = db.Column(db.Float, nullable=True)
    
    status = db.Column(db.String(20), default='pending') # pending, completed, abandoned
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tournament = db.relationship('Tournament', back_populates='matches')
    
    __table_args__ = (
        db.UniqueConstraint('match_id', 'tournament_id', name='unique_match_per_tournament'),
    )

    def to_dict(self):
        return {
            'id': self.match_id,
            'team1': self.team1_id,
            'team2': self.team2_id,
            'winner': self.winner_id,
            'status': self.status,
            'round': self.round_num,
            'is_draw': self.is_draw,
            'team1_score': self.team1_score,
            'team2_score': self.team2_score,
            'group': self.group_name,
            'stage': self.stage,
            'team1_win_probability': self.team1_win_probability,
            'team2_win_probability': self.team2_win_probability,
        }



class EloHistory(db.Model):
    __tablename__ = 'elo_history'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    match_id = db.Column(db.String(50), nullable=True)
    old_rating = db.Column(db.Integer, nullable=False)
    new_rating = db.Column(db.Integer, nullable=False)
    rating_change = db.Column(db.Integer, nullable=False)
    opponent_rating = db.Column(db.Integer, nullable=True)
    result = db.Column(db.String(10), nullable=False)  # 'win', 'loss', 'draw'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    team = db.relationship('Team', back_populates='elo_history')


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False, index=True)
    tournament_id = db.Column(db.String(50), nullable=False, index=True)
    notify_on_start = db.Column(db.Boolean, default=True)
    notify_on_match = db.Column(db.Boolean, default=True)
    notify_on_complete = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'tournament_id', name='unique_subscription'),
    )
