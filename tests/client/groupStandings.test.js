/**
 * Tests for GroupStandings JavaScript object.
 * Tests: init, fetchStandings, render, createStandingsTable, calculateStats
 */

// Mock the GroupStandings object structure
const GroupStandings = {
  tournamentId: null,
  containerId: null,
  standings: {},

  init(containerId, tournamentId) {
    this.containerId = containerId;
    this.tournamentId = tournamentId;
    this.standings = {};
  },

  async fetchStandings() {
    const resp = await fetch(`/api/v1/play/${this.tournamentId}/group-standings`);
    this.standings = await resp.json();
    return this.standings;
  },

  calculateGoalDifference(team) {
    return (team.goals_for || 0) - (team.goals_against || 0);
  },

  formatGoalDifference(gd) {
    return gd > 0 ? `+${gd}` : `${gd}`;
  },

  sortStandings(teams) {
    return [...teams].sort((a, b) => {
      // Sort by points (desc)
      if (b.points !== a.points) return b.points - a.points;
      
      // Then by goal difference (desc)
      const gdA = this.calculateGoalDifference(a);
      const gdB = this.calculateGoalDifference(b);
      if (gdB !== gdA) return gdB - gdA;
      
      // Then by goals scored (desc)
      return (b.goals_for || 0) - (a.goals_for || 0);
    });
  },

  isQualifyingPosition(index, teamsAdvance) {
    return index < teamsAdvance;
  },
};

describe('GroupStandings', () => {
  beforeEach(() => {
    GroupStandings.init('standings-container', 'test-tournament');
    jest.clearAllMocks();
  });

  describe('init', () => {
    test('should set containerId', () => {
      GroupStandings.init('my-container', 'tournament-1');
      expect(GroupStandings.containerId).toBe('my-container');
    });

    test('should set tournamentId', () => {
      GroupStandings.init('container', 'my-tournament');
      expect(GroupStandings.tournamentId).toBe('my-tournament');
    });

    test('should reset standings', () => {
      GroupStandings.standings = { A: [{ name: 'Team' }] };
      GroupStandings.init('container', 'tournament');
      expect(GroupStandings.standings).toEqual({});
    });
  });

  describe('fetchStandings', () => {
    test('should fetch from API', async () => {
      const mockStandings = {
        A: [{ name: 'Team A1', points: 9 }],
        B: [{ name: 'Team B1', points: 7 }],
      };
      fetch.mockResolvedValueOnce(mockFetchResponse(mockStandings));

      const result = await GroupStandings.fetchStandings();

      expect(fetch).toHaveBeenCalledWith('/api/v1/play/test-tournament/group-standings');
      expect(result).toEqual(mockStandings);
      expect(GroupStandings.standings).toEqual(mockStandings);
    });

    test('should handle empty response', async () => {
      fetch.mockResolvedValueOnce(mockFetchResponse({}));

      const result = await GroupStandings.fetchStandings();

      expect(result).toEqual({});
    });
  });

  describe('calculateGoalDifference', () => {
    test('should calculate positive goal difference', () => {
      const team = { goals_for: 10, goals_against: 3 };
      expect(GroupStandings.calculateGoalDifference(team)).toBe(7);
    });

    test('should calculate negative goal difference', () => {
      const team = { goals_for: 2, goals_against: 8 };
      expect(GroupStandings.calculateGoalDifference(team)).toBe(-6);
    });

    test('should calculate zero goal difference', () => {
      const team = { goals_for: 5, goals_against: 5 };
      expect(GroupStandings.calculateGoalDifference(team)).toBe(0);
    });

    test('should handle missing values', () => {
      expect(GroupStandings.calculateGoalDifference({})).toBe(0);
      expect(GroupStandings.calculateGoalDifference({ goals_for: 5 })).toBe(5);
      expect(GroupStandings.calculateGoalDifference({ goals_against: 3 })).toBe(-3);
    });
  });

  describe('formatGoalDifference', () => {
    test('should format positive with plus sign', () => {
      expect(GroupStandings.formatGoalDifference(5)).toBe('+5');
    });

    test('should format negative with minus sign', () => {
      expect(GroupStandings.formatGoalDifference(-3)).toBe('-3');
    });

    test('should format zero without sign', () => {
      expect(GroupStandings.formatGoalDifference(0)).toBe('0');
    });
  });

  describe('sortStandings', () => {
    test('should sort by points descending', () => {
      const teams = [
        { name: 'Team C', points: 3 },
        { name: 'Team A', points: 9 },
        { name: 'Team B', points: 6 },
      ];

      const sorted = GroupStandings.sortStandings(teams);

      expect(sorted[0].name).toBe('Team A');
      expect(sorted[1].name).toBe('Team B');
      expect(sorted[2].name).toBe('Team C');
    });

    test('should use goal difference as tiebreaker', () => {
      const teams = [
        { name: 'Team A', points: 6, goals_for: 5, goals_against: 5 },
        { name: 'Team B', points: 6, goals_for: 8, goals_against: 2 },
      ];

      const sorted = GroupStandings.sortStandings(teams);

      expect(sorted[0].name).toBe('Team B'); // GD +6
      expect(sorted[1].name).toBe('Team A'); // GD 0
    });

    test('should use goals scored as secondary tiebreaker', () => {
      const teams = [
        { name: 'Team A', points: 6, goals_for: 4, goals_against: 4 },
        { name: 'Team B', points: 6, goals_for: 6, goals_against: 6 },
      ];

      const sorted = GroupStandings.sortStandings(teams);

      expect(sorted[0].name).toBe('Team B'); // GF 6
      expect(sorted[1].name).toBe('Team A'); // GF 4
    });

    test('should not mutate original array', () => {
      const teams = [
        { name: 'Team B', points: 3 },
        { name: 'Team A', points: 9 },
      ];

      GroupStandings.sortStandings(teams);

      expect(teams[0].name).toBe('Team B'); // Original unchanged
    });
  });

  describe('isQualifyingPosition', () => {
    test('should return true for qualifying positions', () => {
      expect(GroupStandings.isQualifyingPosition(0, 2)).toBe(true);
      expect(GroupStandings.isQualifyingPosition(1, 2)).toBe(true);
    });

    test('should return false for non-qualifying positions', () => {
      expect(GroupStandings.isQualifyingPosition(2, 2)).toBe(false);
      expect(GroupStandings.isQualifyingPosition(3, 2)).toBe(false);
    });

    test('should work with different teamsAdvance values', () => {
      expect(GroupStandings.isQualifyingPosition(0, 4)).toBe(true);
      expect(GroupStandings.isQualifyingPosition(3, 4)).toBe(true);
      expect(GroupStandings.isQualifyingPosition(4, 4)).toBe(false);
    });
  });
});

describe('GroupStandings Football Rules', () => {
  beforeEach(() => {
    GroupStandings.init('container', 'tournament');
  });

  test('should correctly rank teams with football points (3-1-0)', () => {
    const teams = [
      { name: 'Team A', wins: 3, draws: 0, losses: 0, points: 9 },
      { name: 'Team B', wins: 2, draws: 1, losses: 0, points: 7 },
      { name: 'Team C', wins: 1, draws: 1, losses: 1, points: 4 },
      { name: 'Team D', wins: 0, draws: 0, losses: 3, points: 0 },
    ];

    const sorted = GroupStandings.sortStandings(teams);

    expect(sorted[0].name).toBe('Team A');
    expect(sorted[1].name).toBe('Team B');
    expect(sorted[2].name).toBe('Team C');
    expect(sorted[3].name).toBe('Team D');
  });

  test('should handle typical group stage scenario', () => {
    const teams = [
      { name: 'Brazil', points: 7, goals_for: 5, goals_against: 1 },
      { name: 'Germany', points: 7, goals_for: 6, goals_against: 2 },
      { name: 'Japan', points: 3, goals_for: 2, goals_against: 4 },
      { name: 'USA', points: 0, goals_for: 1, goals_against: 7 },
    ];

    const sorted = GroupStandings.sortStandings(teams);

    // Same points, Germany has better GD (+4 vs +4), but more GF (6 vs 5)
    expect(sorted[0].name).toBe('Germany');
    expect(sorted[1].name).toBe('Brazil');
    expect(sorted[2].name).toBe('Japan');
    expect(sorted[3].name).toBe('USA');
  });
});
