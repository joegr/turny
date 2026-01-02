/**
 * Jest setup file for client-side tests.
 * Configures DOM testing environment and global mocks.
 */

require('@testing-library/jest-dom');

// Mock fetch API
global.fetch = jest.fn();

// Mock EventSource for SSE
global.EventSource = jest.fn(() => ({
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  close: jest.fn(),
  onmessage: null,
  onerror: null,
  onopen: null,
}));

// Mock window.showToast
global.showToast = jest.fn();

// Mock window.currentTournamentId
global.currentTournamentId = 'test-tournament-id';

// Reset mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
  document.body.innerHTML = '';
});

// Helper to create mock fetch responses
global.mockFetchResponse = (data, status = 200) => {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
};

// Helper to create mock fetch error
global.mockFetchError = (message) => {
  return Promise.reject(new Error(message));
};
