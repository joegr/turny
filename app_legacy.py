import os
import json
import time
import random
import math
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, Tournament, Team, Match

app = Flask(__name__)

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_client = redis.from_url(
    redis_url, 
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30
)

database_url = os.getenv('DATABASE_URL', 'postgresql://tournament:tournament123@localhost:5432/tournament_db')
engine = create_engine(database_url, pool_pre_ping=True)
Base.metadata.create_all(engine)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

TOURNAMENT_STATE = 'tournament_state'
TEAMS = 'teams'
MATCHES = 'matches'
CURRENT_ROUND = 'current_round'
TOURNAMENT_START_TIME = 'tournament_start_time'
TOURNAMENT_TYPE = 'tournament_type'
ROUND_ROBIN_ROUNDS = 'round_robin_rounds'

TEAM_ADJECTIVES = [
    'Mighty', 'Fierce', 'Swift', 'Thunder', 'Lightning', 'Shadow', 'Golden',
    'Silver', 'Iron', 'Steel', 'Crimson', 'Azure', 'Emerald', 'Blazing',
    'Frozen', 'Savage', 'Noble', 'Royal', 'Elite', 'Supreme', 'Legendary',
    'Mystic', 'Cosmic', 'Phantom', 'Vicious', 'Ruthless', 'Fearless'
]

TEAM_NOUNS = [
    'Warriors', 'Dragons', 'Tigers', 'Eagles', 'Wolves', 'Lions', 'Bears',
    'Hawks', 'Falcons', 'Panthers', 'Cobras', 'Vipers', 'Sharks', 'Titans',
    'Giants', 'Knights', 'Spartans', 'Gladiators', 'Samurai', 'Vikings',
    'Crusaders', 'Ninjas', 'Assassins', 'Reapers', 'Phoenixes', 'Griffins'
]

class TournamentManager:
    def __init__(self):
        self.redis = redis_client
        self.db = SessionLocal
        self.current_tournament_id = None
        self._ensure_tournament_exists()
    
    def _ensure_tournament_exists(self):
        try:
            if not self.current_tournament_id:
                tournament = self.db.query(Tournament).filter_by(status='registration').first()
                if not tournament:
                    tournament = Tournament(
                        tournament_type='single_elimination',
                        status='registration',
                        current_round=0
                    )
                    self.db.add(tournament)
                    self.db.commit()
                self.current_tournament_id = tournament.id
        except Exception as e:
            print(f"Error ensuring tournament exists: {e}")
            self.db.rollback()
    
    def _sync_tournament_to_db(self, state):
        try:
            if not self.current_tournament_id:
                self._ensure_tournament_exists()
            
            tournament = self.db.query(Tournament).get(self.current_tournament_id)
            if tournament:
                tournament.status = state.get('status', 'registration')
                tournament.current_round = state.get('round', 0)
                tournament.tournament_type = state.get('type', 'single_elimination')
                tournament.winner_team_id = state.get('winner')
                tournament.updated_at = datetime.now()
                
                if state.get('status') == 'active' and not tournament.start_time:
                    tournament.start_time = datetime.now()
                elif state.get('status') == 'completed' and not tournament.end_time:
                    tournament.end_time = datetime.now()
                
                self.db.commit()
        except Exception as e:
            print(f"Error syncing tournament to DB: {e}")
            self.db.rollback()
    
    def _sync_team_to_db(self, team_id, team_data):
        try:
            if not self.current_tournament_id:
                self._ensure_tournament_exists()
            
            team = self.db.query(Team).filter_by(team_id=team_id).first()
            if team:
                team.name = team_data['name']
                team.captain = team_data['captain']
                team.wins = team_data.get('wins', 0)
                team.losses = team_data.get('losses', 0)
                team.updated_at = datetime.now()
            else:
                team = Team(
                    team_id=team_id,
                    tournament_id=self.current_tournament_id,
                    name=team_data['name'],
                    captain=team_data['captain'],
                    wins=team_data.get('wins', 0),
                    losses=team_data.get('losses', 0)
                )
                self.db.add(team)
            
            self.db.commit()
        except Exception as e:
            print(f"Error syncing team to DB: {e}")
            self.db.rollback()
    
    def _sync_match_to_db(self, match_data):
        try:
            if not self.current_tournament_id:
                self._ensure_tournament_exists()
            
            match = self.db.query(Match).filter_by(match_id=match_data['id']).first()
            if match:
                match.status = match_data.get('status', 'pending')
                match.winner_id = match_data.get('winner')
                match.updated_at = datetime.now()
            else:
                match = Match(
                    match_id=match_data['id'],
                    tournament_id=self.current_tournament_id,
                    round_number=match_data.get('round', 1),
                    team1_id=match_data['team1'],
                    team2_id=match_data['team2'],
                    winner_id=match_data.get('winner'),
                    status=match_data.get('status', 'pending')
                )
                self.db.add(match)
            
            self.db.commit()
        except Exception as e:
            print(f"Error syncing match to DB: {e}")
            self.db.rollback()
    
    def get_tournament_state(self):
        state = self.redis.get(TOURNAMENT_STATE)
        tournament_type = self.redis.get(TOURNAMENT_TYPE) or 'single_elimination'
        default_state = {'status': 'registration', 'round': 0, 'type': tournament_type}
        return json.loads(state) if state else default_state
    
    def set_tournament_state(self, state):
        self.redis.set(TOURNAMENT_STATE, json.dumps(state))
        self._sync_tournament_to_db(state)
    
    def register_team(self, captain_name, team_name):
        teams = self.get_teams()
        team_id = f"team_{len(teams) + 1}"
        teams[team_id] = {
            'captain': captain_name,
            'name': team_name,
            'wins': 0,
            'losses': 0
        }
        self.redis.set(TEAMS, json.dumps(teams))
        self._sync_team_to_db(team_id, teams[team_id])
        return team_id
    
    def get_teams(self):
        teams = self.redis.get(TEAMS)
        if teams:
            return json.loads(teams)
        else:
            self.initialize_teams(8)
            teams = self.redis.get(TEAMS)
            return json.loads(teams) if teams else {}
    
    def start_tournament(self, tournament_type='single_elimination'):
        teams = self.get_teams()
        if tournament_type == 'single_elimination' and len(teams) < 4:
            return False, 'Need at least 4 teams for single elimination'
        if tournament_type == 'round_robin' and len(teams) < 2:
            return False, 'Need at least 2 teams for round robin'
        
        self.redis.set(TOURNAMENT_TYPE, tournament_type)
        
        competitors = []
        for team_id, team_data in teams.items():
            competitors.append({
                'team': team_id,
                'name': team_data['name'],
                'rating': 1500 + (team_data.get('wins', 0) * 100) - (team_data.get('losses', 0) * 50)
            })
        
        competitors.sort(key=lambda x: x['rating'], reverse=True)
        
        if tournament_type == 'round_robin':
            return self._start_round_robin(competitors, teams)
        else:
            return self._start_single_elimination(competitors, teams)
    
    def _start_single_elimination(self, competitors, teams):
        team_ids = [comp['team'] for comp in competitors]
        
        matches = self._create_single_elim_matches(team_ids, round_num=1)
        
        for match in matches:
            self._sync_match_to_db(match)
        
        self.redis.set(MATCHES, json.dumps(matches))
        self.redis.set(CURRENT_ROUND, '1')
        self.redis.set(TOURNAMENT_START_TIME, str(time.time()))
        
        self.set_tournament_state({'status': 'active', 'round': 1, 'type': 'single_elimination'})
        return True, 'Single elimination tournament started'
    
    def _create_single_elim_matches(self, team_ids, round_num):
        matches = []
        for i in range(0, len(team_ids), 2):
            if i + 1 < len(team_ids):
                match_id = f"r{round_num}_match_{len(matches) + 1}"
                matches.append({
                    'id': match_id,
                    'team1': team_ids[i],
                    'team2': team_ids[i + 1],
                    'winner': None,
                    'status': 'pending',
                    'round': round_num
                })
        return matches
    
    def _start_round_robin(self, competitors, teams):
        all_rounds = self._generate_round_robin_rounds(competitors)
        
        self.redis.set(ROUND_ROBIN_ROUNDS, json.dumps(all_rounds))
        
        if all_rounds:
            first_round_matches = all_rounds[0]
            
            for match in first_round_matches:
                self._sync_match_to_db(match)
            
            self.redis.set(MATCHES, json.dumps(first_round_matches))
            self.redis.set(CURRENT_ROUND, '1')
            self.redis.set(TOURNAMENT_START_TIME, str(time.time()))
            
            self.set_tournament_state({'status': 'active', 'round': 1, 'type': 'round_robin', 'total_rounds': len(all_rounds)})
            return True, f'Round robin tournament started with {len(all_rounds)} rounds'
        
        return False, 'Failed to generate round robin schedule'
    
    def _generate_round_robin_rounds(self, competitors):
        n = len(competitors)
        if n < 2:
            return []
        
        rounds = []
        team_ids = [comp['team'] for comp in competitors]
        
        if n % 2 == 1:
            team_ids.append(None)
            n += 1
        
        for round_num in range(n - 1):
            round_matches = []
            for i in range(n // 2):
                team1 = team_ids[i]
                team2 = team_ids[n - 1 - i]
                
                if team1 is not None and team2 is not None:
                    match_id = f"r{round_num + 1}_match_{len(round_matches) + 1}"
                    round_matches.append({
                        'id': match_id,
                        'team1': team1,
                        'team2': team2,
                        'winner': None,
                        'status': 'pending',
                        'round': round_num + 1
                    })
            
            rounds.append(round_matches)
            team_ids = [team_ids[0]] + [team_ids[-1]] + team_ids[1:-1]
        
        return rounds
    
    
    def get_matches(self):
        matches = self.redis.get(MATCHES)
        return json.loads(matches) if matches else []
    
    def record_match_result(self, match_id, winner):
        matches = self.get_matches()
        teams = self.get_teams()
        
        for match in matches:
            if match['id'] == match_id:
                match['winner'] = winner
                match['status'] = 'completed'
                teams[winner]['wins'] += 1
                loser = match['team2'] if match['team1'] == winner else match['team1']
                teams[loser]['losses'] += 1
                
                self._sync_match_to_db(match)
                self._sync_team_to_db(winner, teams[winner])
                self._sync_team_to_db(loser, teams[loser])
                break
        
        self.redis.set(MATCHES, json.dumps(matches))
        self.redis.set(TEAMS, json.dumps(teams))
        
        if all(m['status'] == 'completed' for m in matches):
            self.advance_tournament()
    
    def advance_tournament(self):
        tournament_type = self.redis.get(TOURNAMENT_TYPE) or 'single_elimination'
        
        if tournament_type == 'round_robin':
            self._advance_round_robin()
        else:
            self._advance_single_elimination()
    
    def _advance_round_robin(self):
        current_round = int(self.redis.get(CURRENT_ROUND) or '1')
        rounds_str = self.redis.get(ROUND_ROBIN_ROUNDS)
        
        if not rounds_str:
            return
        
        all_rounds = json.loads(rounds_str)
        
        if current_round < len(all_rounds):
            next_round_matches = all_rounds[current_round]
            self.redis.set(MATCHES, json.dumps(next_round_matches))
            self.redis.set(CURRENT_ROUND, str(current_round + 1))
            self.set_tournament_state({'status': 'active', 'round': current_round + 1, 'type': 'round_robin', 'total_rounds': len(all_rounds)})
        else:
            teams = self.get_teams()
            standings = sorted(
                teams.items(),
                key=lambda x: (x[1].get('wins', 0), -x[1].get('losses', 0)),
                reverse=True
            )
            winner = standings[0][0] if standings else None
            self.set_tournament_state({'status': 'completed', 'winner': winner, 'type': 'round_robin', 'standings': [{'team_id': t[0], 'wins': t[1].get('wins', 0), 'losses': t[1].get('losses', 0)} for t in standings]})
    
    def _advance_single_elimination(self):
        matches = self.get_matches()
        teams = self.get_teams()
        current_round = int(self.redis.get(CURRENT_ROUND) or '1')
        
        winners = [match['winner'] for match in matches if match['winner']]
        
        if len(winners) == 1:
            self.set_tournament_state({'status': 'completed', 'winner': winners[0], 'type': 'single_elimination'})
            return
        
        if len(winners) == 0:
            self.set_tournament_state({'status': 'completed', 'winner': None, 'type': 'single_elimination'})
            return
        
        next_round = current_round + 1
        next_matches = self._create_single_elim_matches(winners, next_round)
        
        for match in next_matches:
            self._sync_match_to_db(match)
        
        self.redis.set(MATCHES, json.dumps(next_matches))
        self.redis.set(CURRENT_ROUND, str(next_round))
        self.set_tournament_state({'status': 'active', 'round': next_round, 'type': 'single_elimination'})
    
    def should_auto_advance(self):
        if self.redis.get(TOURNAMENT_START_TIME):
            start_time = float(self.redis.get(TOURNAMENT_START_TIME))
            current_round = int(self.redis.get(CURRENT_ROUND) or '1')
            
            round_duration = 300  # 5 minutes per round
            expected_end_time = start_time + (current_round * round_duration)
            
            return time.time() > expected_end_time
        return False
    
    def handle_abandoned_match(self, match_id):
        matches = self.get_matches()
        teams = self.get_teams()
        
        for match in matches:
            if match['id'] == match_id:
                match['status'] = 'abandoned'
                match['winner'] = None
                teams[match['team1']]['losses'] += 1
                teams[match['team2']]['losses'] += 1
                break
        
        self.redis.set(MATCHES, json.dumps(matches))
        self.redis.set(TEAMS, json.dumps(teams))
        
        if all(m['status'] in ['completed', 'abandoned'] for m in matches):
            self.advance_tournament()
    
    def reset_tournament(self):
        try:
            self.redis.delete(
                TOURNAMENT_STATE,
                TEAMS,
                MATCHES,
                CURRENT_ROUND,
                TOURNAMENT_START_TIME,
                TOURNAMENT_TYPE,
                ROUND_ROBIN_ROUNDS,
                'bracket_structure'
            )
            
            self.initialize_teams(8, force=True)
            return True, 'Tournament reset successfully'
        except Exception as e:
            return False, f'Failed to reset tournament: {e}'
    
    def initialize_teams(self, count=8, force=False):
        try:
            self.redis.ping()
            
            if not force:
                existing_teams = self.get_teams()
                if existing_teams:
                    return
            
            teams = {}
            used_names = set()
            
            for i in range(count):
                while True:
                    team_name = f"{random.choice(TEAM_ADJECTIVES)} {random.choice(TEAM_NOUNS)}"
                    if team_name not in used_names:
                        used_names.add(team_name)
                        break
                
                team_id = f"team_{i + 1}"
                teams[team_id] = {
                    'captain': f"Captain {i + 1}",
                    'name': team_name,
                    'wins': 0,
                    'losses': 0
                }
                self._sync_team_to_db(team_id, teams[team_id])
            
            self.redis.set(TEAMS, json.dumps(teams))
            self.set_tournament_state({'status': 'registration', 'round': 0})
        except Exception as e:
            print(f"Warning: Could not initialize teams - {e}")
            pass

tournament_manager = TournamentManager()

@app.route('/')
def index():
    return render_template('index.html', active_page='home')

@app.route('/teams')
def teams_page():
    return render_template('teams.html', active_page='teams')

@app.route('/teams/<team_id>')
def team_detail_page(team_id):
    return render_template('team_detail.html', active_page='teams', team_id=team_id)

@app.route('/tournaments')
def tournaments_page():
    return render_template('tournaments.html', active_page='tournaments')

@app.route('/tournaments/current')
def tournament_detail_page():
    return render_template('tournament_detail.html', active_page='tournaments')

@app.route('/api/tournament/state')
def get_tournament_state():
    return jsonify(tournament_manager.get_tournament_state())

@app.route('/api/teams', methods=['GET'])
def get_teams():
    return jsonify(tournament_manager.get_teams())

@app.route('/api/teams/register', methods=['POST'])
def register_team():
    data = request.json
    captain_name = data.get('captain_name')
    team_name = data.get('team_name')
    
    if not captain_name or not team_name:
        return jsonify({'error': 'Captain name and team name required'}), 400
    
    team_id = tournament_manager.register_team(captain_name, team_name)
    return jsonify({'team_id': team_id, 'message': 'Team registered successfully'})

@app.route('/api/tournament/start', methods=['POST'])
def start_tournament():
    data = request.json or {}
    tournament_type = data.get('type', 'single_elimination')
    
    if tournament_type not in ['single_elimination', 'round_robin']:
        return jsonify({'error': 'Invalid tournament type. Must be "single_elimination" or "round_robin"'}), 400
    
    success, message = tournament_manager.start_tournament(tournament_type)
    if success:
        return jsonify({'message': message, 'type': tournament_type})
    return jsonify({'error': message}), 400

@app.route('/api/tournament/reset', methods=['POST'])
def reset_tournament():
    success, message = tournament_manager.reset_tournament()
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 500

@app.route('/api/matches')
def get_matches():
    return jsonify(tournament_manager.get_matches())

@app.route('/api/bracket')
def get_bracket():
    bracket_str = tournament_manager.redis.get('bracket_structure')
    if bracket_str:
        return jsonify(json.loads(bracket_str))
    return jsonify({'error': 'No bracket structure available'}), 404

@app.route('/api/matches/<match_id>/result', methods=['POST'])
def record_match_result(match_id):
    try:
        data = request.json
        winner = data.get('winner')
        
        if not winner:
            return jsonify({'error': 'Winner is required'}), 400
        
        app.logger.info(f"Recording match result: match_id={match_id}, winner={winner}")
        tournament_manager.record_match_result(match_id, winner)
        
        return jsonify({
            'message': 'Match result recorded',
            'match_id': match_id,
            'winner': winner
        })
    except Exception as e:
        app.logger.error(f"Error recording match result: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tournament/auto-advance', methods=['POST'])
def auto_advance_tournament():
    if tournament_manager.should_auto_advance():
        matches = tournament_manager.get_matches()
        pending_matches = [m for m in matches if m['status'] == 'pending']
        
        if pending_matches:
            for match in pending_matches:
                tournament_manager.handle_abandoned_match(match['id'])
        
        return jsonify({'message': 'Tournament auto-advanced, abandoned matches marked as losses'})
    
    return jsonify({'message': 'No auto-advance needed at this time'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
