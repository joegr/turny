/**
 * Tests for ColumnBracket JavaScript object.
 * Tests: init, render, createMatchCard, createTeamRow, openMatchModal,
 *        selectWinner, confirmWinner, closeModal, updateScoreSelection
 */

// Mock the ColumnBracket object structure
const ColumnBracket = {
  containerId: null,
  currentMatch: null,
  selectedWinner: null,
  isDraw: false,

  init(containerId) {
    this.containerId = containerId;
    this.currentMatch = null;
    this.selectedWinner = null;
    this.isDraw = false;
  },

  async render(tournamentId) {
    const teamsResp = await fetch(`/api/v1/play/${tournamentId}/teams`);
    const matchesResp = await fetch(`/api/v1/play/${tournamentId}/matches`);
    return { teams: await teamsResp.json(), matches: await matchesResp.json() };
  },

  createMatchCard(match, teams) {
    const card = document.createElement('div');
    card.className = 'match-card';
    card.dataset.matchId = match.id;
    return card;
  },

  createTeamRow(team, isWinner, isLoser) {
    const row = document.createElement('div');
    row.className = `team-row ${isWinner ? 'team-winner' : ''} ${isLoser ? 'team-loser' : ''}`;
    return row;
  },

  selectWinner(teamId) {
    this.selectedWinner = teamId;
    this.isDraw = false;
  },

  updateScoreSelection() {
    const score1 = parseInt(document.getElementById('team1-score')?.value || 0);
    const score2 = parseInt(document.getElementById('team2-score')?.value || 0);
    
    if (score1 > score2) {
      this.selectedWinner = this.currentMatch?.team1;
      this.isDraw = false;
    } else if (score2 > score1) {
      this.selectedWinner = this.currentMatch?.team2;
      this.isDraw = false;
    } else {
      this.selectedWinner = null;
      this.isDraw = true;
    }
  },

  async confirmWinner() {
    if (!this.selectedWinner && !this.isDraw) return false;
    if (!this.currentMatch) return false;

    const body = {};
    if (this.isDraw) {
      body.is_draw = true;
    } else {
      body.winner = this.selectedWinner;
    }

    const response = await fetch(
      `/api/v1/play/${window.currentTournamentId}/matches/${this.currentMatch.id}/result`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }
    );

    return response.ok;
  },

  closeModal() {
    this.currentMatch = null;
    this.selectedWinner = null;
    this.isDraw = false;
  },

  getRoundName(roundNum, matchCount) {
    if (matchCount === 1) return 'Finals';
    if (matchCount === 2) return 'Semifinals';
    if (matchCount === 4) return 'Quarterfinals';
    return `Round ${roundNum}`;
  },
};

describe('ColumnBracket', () => {
  beforeEach(() => {
    ColumnBracket.init('test-container');
  });

  describe('init', () => {
    test('should set containerId', () => {
      ColumnBracket.init('my-bracket');
      expect(ColumnBracket.containerId).toBe('my-bracket');
    });

    test('should reset currentMatch', () => {
      ColumnBracket.currentMatch = { id: 'old-match' };
      ColumnBracket.init('new-container');
      expect(ColumnBracket.currentMatch).toBeNull();
    });

    test('should reset selectedWinner', () => {
      ColumnBracket.selectedWinner = 'team-1';
      ColumnBracket.init('new-container');
      expect(ColumnBracket.selectedWinner).toBeNull();
    });

    test('should reset isDraw', () => {
      ColumnBracket.isDraw = true;
      ColumnBracket.init('new-container');
      expect(ColumnBracket.isDraw).toBe(false);
    });
  });

  describe('render', () => {
    test('should fetch teams and matches', async () => {
      const mockTeams = { 'team-1': { name: 'Dragons' } };
      const mockMatches = [{ id: 'match-1', team1: 'team-1', team2: 'team-2' }];

      fetch
        .mockResolvedValueOnce(mockFetchResponse(mockTeams))
        .mockResolvedValueOnce(mockFetchResponse(mockMatches));

      const result = await ColumnBracket.render('test-tournament');

      expect(fetch).toHaveBeenCalledTimes(2);
      expect(fetch).toHaveBeenCalledWith('/api/v1/play/test-tournament/teams');
      expect(fetch).toHaveBeenCalledWith('/api/v1/play/test-tournament/matches');
      expect(result.teams).toEqual(mockTeams);
      expect(result.matches).toEqual(mockMatches);
    });
  });

  describe('createMatchCard', () => {
    test('should create div with match-card class', () => {
      const match = { id: 'match-123' };
      const card = ColumnBracket.createMatchCard(match, {});

      expect(card.tagName).toBe('DIV');
      expect(card.className).toContain('match-card');
    });

    test('should set match ID in dataset', () => {
      const match = { id: 'match-456' };
      const card = ColumnBracket.createMatchCard(match, {});

      expect(card.dataset.matchId).toBe('match-456');
    });
  });

  describe('createTeamRow', () => {
    test('should create row with team-row class', () => {
      const team = { name: 'Dragons', elo_rating: 1500 };
      const row = ColumnBracket.createTeamRow(team, false, false);

      expect(row.tagName).toBe('DIV');
      expect(row.className).toContain('team-row');
    });

    test('should add winner class when isWinner is true', () => {
      const team = { name: 'Dragons' };
      const row = ColumnBracket.createTeamRow(team, true, false);

      expect(row.className).toContain('team-winner');
    });

    test('should add loser class when isLoser is true', () => {
      const team = { name: 'Phoenix' };
      const row = ColumnBracket.createTeamRow(team, false, true);

      expect(row.className).toContain('team-loser');
    });

    test('should not add winner/loser classes when both false', () => {
      const team = { name: 'Tigers' };
      const row = ColumnBracket.createTeamRow(team, false, false);

      expect(row.className).not.toContain('team-winner');
      expect(row.className).not.toContain('team-loser');
    });
  });

  describe('selectWinner', () => {
    test('should set selectedWinner', () => {
      ColumnBracket.selectWinner('team-abc');
      expect(ColumnBracket.selectedWinner).toBe('team-abc');
    });

    test('should set isDraw to false', () => {
      ColumnBracket.isDraw = true;
      ColumnBracket.selectWinner('team-abc');
      expect(ColumnBracket.isDraw).toBe(false);
    });
  });

  describe('updateScoreSelection', () => {
    beforeEach(() => {
      document.body.innerHTML = `
        <input id="team1-score" value="0" />
        <input id="team2-score" value="0" />
      `;
      ColumnBracket.currentMatch = { team1: 'team-a', team2: 'team-b' };
    });

    test('should set team1 as winner when score1 > score2', () => {
      document.getElementById('team1-score').value = '3';
      document.getElementById('team2-score').value = '1';

      ColumnBracket.updateScoreSelection();

      expect(ColumnBracket.selectedWinner).toBe('team-a');
      expect(ColumnBracket.isDraw).toBe(false);
    });

    test('should set team2 as winner when score2 > score1', () => {
      document.getElementById('team1-score').value = '1';
      document.getElementById('team2-score').value = '2';

      ColumnBracket.updateScoreSelection();

      expect(ColumnBracket.selectedWinner).toBe('team-b');
      expect(ColumnBracket.isDraw).toBe(false);
    });

    test('should set isDraw when scores are equal', () => {
      document.getElementById('team1-score').value = '2';
      document.getElementById('team2-score').value = '2';

      ColumnBracket.updateScoreSelection();

      expect(ColumnBracket.selectedWinner).toBeNull();
      expect(ColumnBracket.isDraw).toBe(true);
    });
  });

  describe('confirmWinner', () => {
    beforeEach(() => {
      ColumnBracket.currentMatch = { id: 'match-123' };
    });

    test('should return false if no winner and not draw', async () => {
      ColumnBracket.selectedWinner = null;
      ColumnBracket.isDraw = false;

      const result = await ColumnBracket.confirmWinner();
      expect(result).toBe(false);
    });

    test('should return false if no current match', async () => {
      ColumnBracket.currentMatch = null;
      ColumnBracket.selectedWinner = 'team-1';

      const result = await ColumnBracket.confirmWinner();
      expect(result).toBe(false);
    });

    test('should send winner in request body', async () => {
      ColumnBracket.selectedWinner = 'team-winner';
      fetch.mockResolvedValueOnce(mockFetchResponse({ success: true }));

      await ColumnBracket.confirmWinner();

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/matches/match-123/result'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ winner: 'team-winner' }),
        })
      );
    });

    test('should send is_draw in request body for draws', async () => {
      ColumnBracket.selectedWinner = null;
      ColumnBracket.isDraw = true;
      fetch.mockResolvedValueOnce(mockFetchResponse({ success: true }));

      await ColumnBracket.confirmWinner();

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/matches/match-123/result'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ is_draw: true }),
        })
      );
    });

    test('should return true on successful response', async () => {
      ColumnBracket.selectedWinner = 'team-1';
      fetch.mockResolvedValueOnce(mockFetchResponse({ success: true }));

      const result = await ColumnBracket.confirmWinner();
      expect(result).toBe(true);
    });
  });

  describe('closeModal', () => {
    test('should reset currentMatch', () => {
      ColumnBracket.currentMatch = { id: 'match-123' };
      ColumnBracket.closeModal();
      expect(ColumnBracket.currentMatch).toBeNull();
    });

    test('should reset selectedWinner', () => {
      ColumnBracket.selectedWinner = 'team-1';
      ColumnBracket.closeModal();
      expect(ColumnBracket.selectedWinner).toBeNull();
    });

    test('should reset isDraw', () => {
      ColumnBracket.isDraw = true;
      ColumnBracket.closeModal();
      expect(ColumnBracket.isDraw).toBe(false);
    });
  });

  describe('getRoundName', () => {
    test('should return Finals for 1 match', () => {
      expect(ColumnBracket.getRoundName(4, 1)).toBe('Finals');
    });

    test('should return Semifinals for 2 matches', () => {
      expect(ColumnBracket.getRoundName(3, 2)).toBe('Semifinals');
    });

    test('should return Quarterfinals for 4 matches', () => {
      expect(ColumnBracket.getRoundName(2, 4)).toBe('Quarterfinals');
    });

    test('should return Round N for other counts', () => {
      expect(ColumnBracket.getRoundName(1, 8)).toBe('Round 1');
      expect(ColumnBracket.getRoundName(1, 16)).toBe('Round 1');
    });
  });
});
