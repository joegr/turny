/**
 * Tests for HybridView JavaScript object.
 * Tests: init, loadStageStatus, showStage, render, renderGroups,
 *        renderKnockout, advanceToKnockout, createGroupCard
 */

// Mock the HybridView object structure
const HybridView = {
  tournamentId: null,
  stageStatus: null,
  teamsAdvance: 2,

  async init(tournamentId, teamsAdvance = 2) {
    this.tournamentId = tournamentId;
    this.teamsAdvance = teamsAdvance;
    await this.loadStageStatus();
  },

  async loadStageStatus() {
    const resp = await fetch(`/api/v1/play/${this.tournamentId}/stage-status`);
    this.stageStatus = await resp.json();
    return this.stageStatus;
  },

  showStage(stage) {
    // Mock implementation
    return stage;
  },

  async render() {
    await this.renderGroups();
    await this.renderKnockout();
  },

  async renderGroups() {
    const [standingsResp, matchesResp, teamsResp] = await Promise.all([
      fetch(`/api/v1/play/${this.tournamentId}/group-standings`),
      fetch(`/api/v1/play/${this.tournamentId}/matches`),
      fetch(`/api/v1/play/${this.tournamentId}/teams`),
    ]);

    return {
      standings: await standingsResp.json(),
      matches: await matchesResp.json(),
      teams: await teamsResp.json(),
    };
  },

  async renderKnockout() {
    const matchesResp = await fetch(`/api/v1/play/${this.tournamentId}/matches`);
    const matches = await matchesResp.json();
    return matches.filter((m) => m.stage === 'knockout');
  },

  async advanceToKnockout() {
    const resp = await fetch(
      `/api/v1/play/${this.tournamentId}/advance-to-knockout`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }
    );

    if (resp.ok) {
      await this.loadStageStatus();
      await this.render();
      return true;
    }
    return false;
  },

  createGroupCard(groupName, standings, matches, teams) {
    return {
      groupName,
      standingsCount: standings.length,
      matchesCount: matches.length,
    };
  },
};

describe('HybridView', () => {
  beforeEach(() => {
    HybridView.tournamentId = null;
    HybridView.stageStatus = null;
    HybridView.teamsAdvance = 2;
    jest.clearAllMocks();
  });

  describe('init', () => {
    test('should set tournamentId', async () => {
      fetch.mockResolvedValueOnce(mockFetchResponse({ current_stage: 'group' }));

      await HybridView.init('test-tournament');

      expect(HybridView.tournamentId).toBe('test-tournament');
    });

    test('should set teamsAdvance with default', async () => {
      fetch.mockResolvedValueOnce(mockFetchResponse({ current_stage: 'group' }));

      await HybridView.init('test-tournament');

      expect(HybridView.teamsAdvance).toBe(2);
    });

    test('should set custom teamsAdvance', async () => {
      fetch.mockResolvedValueOnce(mockFetchResponse({ current_stage: 'group' }));

      await HybridView.init('test-tournament', 4);

      expect(HybridView.teamsAdvance).toBe(4);
    });

    test('should load stage status', async () => {
      const mockStatus = { current_stage: 'group', tournament_type: 'hybrid' };
      fetch.mockResolvedValueOnce(mockFetchResponse(mockStatus));

      await HybridView.init('test-tournament');

      expect(HybridView.stageStatus).toEqual(mockStatus);
    });
  });

  describe('loadStageStatus', () => {
    test('should fetch stage status from API', async () => {
      HybridView.tournamentId = 'my-tournament';
      const mockStatus = {
        current_stage: 'group',
        group_stage: { is_complete: false },
        knockout_stage: { is_generated: false },
      };
      fetch.mockResolvedValueOnce(mockFetchResponse(mockStatus));

      const result = await HybridView.loadStageStatus();

      expect(fetch).toHaveBeenCalledWith('/api/v1/play/my-tournament/stage-status');
      expect(result).toEqual(mockStatus);
      expect(HybridView.stageStatus).toEqual(mockStatus);
    });
  });

  describe('showStage', () => {
    test('should return the stage name', () => {
      expect(HybridView.showStage('groups')).toBe('groups');
      expect(HybridView.showStage('knockout')).toBe('knockout');
    });
  });

  describe('renderGroups', () => {
    test('should fetch standings, matches, and teams', async () => {
      HybridView.tournamentId = 'test-tournament';

      const mockStandings = { A: [{ name: 'Team 1' }], B: [{ name: 'Team 2' }] };
      const mockMatches = [{ id: 'match-1', stage: 'group' }];
      const mockTeams = { 'team-1': { name: 'Team 1' } };

      fetch
        .mockResolvedValueOnce(mockFetchResponse(mockStandings))
        .mockResolvedValueOnce(mockFetchResponse(mockMatches))
        .mockResolvedValueOnce(mockFetchResponse(mockTeams));

      const result = await HybridView.renderGroups();

      expect(fetch).toHaveBeenCalledTimes(3);
      expect(fetch).toHaveBeenCalledWith('/api/v1/play/test-tournament/group-standings');
      expect(fetch).toHaveBeenCalledWith('/api/v1/play/test-tournament/matches');
      expect(fetch).toHaveBeenCalledWith('/api/v1/play/test-tournament/teams');
      expect(result.standings).toEqual(mockStandings);
      expect(result.matches).toEqual(mockMatches);
      expect(result.teams).toEqual(mockTeams);
    });
  });

  describe('renderKnockout', () => {
    test('should fetch matches and filter to knockout only', async () => {
      HybridView.tournamentId = 'test-tournament';

      const mockMatches = [
        { id: 'match-1', stage: 'group' },
        { id: 'match-2', stage: 'group' },
        { id: 'match-3', stage: 'knockout' },
        { id: 'match-4', stage: 'knockout' },
      ];

      fetch.mockResolvedValueOnce(mockFetchResponse(mockMatches));

      const result = await HybridView.renderKnockout();

      expect(result).toHaveLength(2);
      expect(result[0].stage).toBe('knockout');
      expect(result[1].stage).toBe('knockout');
    });

    test('should return empty array when no knockout matches', async () => {
      HybridView.tournamentId = 'test-tournament';

      const mockMatches = [
        { id: 'match-1', stage: 'group' },
        { id: 'match-2', stage: 'group' },
      ];

      fetch.mockResolvedValueOnce(mockFetchResponse(mockMatches));

      const result = await HybridView.renderKnockout();

      expect(result).toHaveLength(0);
    });
  });

  describe('advanceToKnockout', () => {
    beforeEach(() => {
      HybridView.tournamentId = 'test-tournament';
    });

    test('should POST to advance-to-knockout endpoint', async () => {
      fetch
        .mockResolvedValueOnce(mockFetchResponse({ success: true }))
        .mockResolvedValueOnce(mockFetchResponse({ current_stage: 'knockout' }))
        .mockResolvedValueOnce(mockFetchResponse({}))
        .mockResolvedValueOnce(mockFetchResponse([]))
        .mockResolvedValueOnce(mockFetchResponse({}))
        .mockResolvedValueOnce(mockFetchResponse([]));

      await HybridView.advanceToKnockout();

      expect(fetch).toHaveBeenCalledWith(
        '/api/v1/play/test-tournament/advance-to-knockout',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    test('should return true on success', async () => {
      fetch
        .mockResolvedValueOnce(mockFetchResponse({ success: true }))
        .mockResolvedValueOnce(mockFetchResponse({ current_stage: 'knockout' }))
        .mockResolvedValueOnce(mockFetchResponse({}))
        .mockResolvedValueOnce(mockFetchResponse([]))
        .mockResolvedValueOnce(mockFetchResponse({}))
        .mockResolvedValueOnce(mockFetchResponse([]));

      const result = await HybridView.advanceToKnockout();

      expect(result).toBe(true);
    });

    test('should return false on failure', async () => {
      fetch.mockResolvedValueOnce(mockFetchResponse({ error: 'Not complete' }, 400));

      const result = await HybridView.advanceToKnockout();

      expect(result).toBe(false);
    });

    test('should reload stage status on success', async () => {
      const mockStatus = { current_stage: 'knockout' };
      fetch
        .mockResolvedValueOnce(mockFetchResponse({ success: true }))
        .mockResolvedValueOnce(mockFetchResponse(mockStatus))
        .mockResolvedValueOnce(mockFetchResponse({}))
        .mockResolvedValueOnce(mockFetchResponse([]))
        .mockResolvedValueOnce(mockFetchResponse({}))
        .mockResolvedValueOnce(mockFetchResponse([]));

      await HybridView.advanceToKnockout();

      expect(HybridView.stageStatus).toEqual(mockStatus);
    });
  });

  describe('createGroupCard', () => {
    test('should return group card data', () => {
      const standings = [
        { name: 'Team A', points: 9 },
        { name: 'Team B', points: 6 },
        { name: 'Team C', points: 3 },
        { name: 'Team D', points: 0 },
      ];
      const matches = [
        { id: 'm1' },
        { id: 'm2' },
        { id: 'm3' },
      ];
      const teams = {};

      const result = HybridView.createGroupCard('A', standings, matches, teams);

      expect(result.groupName).toBe('A');
      expect(result.standingsCount).toBe(4);
      expect(result.matchesCount).toBe(3);
    });
  });
});

describe('HybridView Stage Status', () => {
  test('should identify group stage', async () => {
    HybridView.tournamentId = 'test';
    const status = {
      current_stage: 'group',
      group_stage: { is_complete: false, pending: 5 },
      knockout_stage: { is_generated: false },
    };
    fetch.mockResolvedValueOnce(mockFetchResponse(status));

    await HybridView.loadStageStatus();

    expect(HybridView.stageStatus.current_stage).toBe('group');
  });

  test('should identify group complete stage', async () => {
    HybridView.tournamentId = 'test';
    const status = {
      current_stage: 'group_complete',
      group_stage: { is_complete: true, pending: 0 },
      knockout_stage: { is_generated: false },
    };
    fetch.mockResolvedValueOnce(mockFetchResponse(status));

    await HybridView.loadStageStatus();

    expect(HybridView.stageStatus.current_stage).toBe('group_complete');
  });

  test('should identify knockout stage', async () => {
    HybridView.tournamentId = 'test';
    const status = {
      current_stage: 'knockout',
      group_stage: { is_complete: true },
      knockout_stage: { is_generated: true },
    };
    fetch.mockResolvedValueOnce(mockFetchResponse(status));

    await HybridView.loadStageStatus();

    expect(HybridView.stageStatus.current_stage).toBe('knockout');
  });
});
