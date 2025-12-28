from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Tournament(Base):
    __tablename__ = 'tournaments'
    
    id = Column(Integer, primary_key=True)
    tournament_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default='registration')
    current_round = Column(Integer, default=0)
    winner_team_id = Column(String(50), nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    bracket_structure = Column(Text, nullable=True)
    round_robin_rounds = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    teams = relationship('Team', back_populates='tournament', cascade='all, delete-orphan')
    matches = relationship('Match', back_populates='tournament', cascade='all, delete-orphan')

class Team(Base):
    __tablename__ = 'teams'
    
    id = Column(Integer, primary_key=True)
    team_id = Column(String(50), unique=True, nullable=False, index=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'), nullable=False)
    name = Column(String(100), nullable=False)
    captain = Column(String(100), nullable=False)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tournament = relationship('Tournament', back_populates='teams')

class Match(Base):
    __tablename__ = 'matches'
    
    id = Column(Integer, primary_key=True)
    match_id = Column(String(50), nullable=False, index=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'), nullable=False)
    round_number = Column(Integer, nullable=False)
    team1_id = Column(String(50), nullable=False)
    team2_id = Column(String(50), nullable=False)
    winner_id = Column(String(50), nullable=True)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tournament = relationship('Tournament', back_populates='matches')
