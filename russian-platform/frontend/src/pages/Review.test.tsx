// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Review from './Review';

const CARD = {
  card_id: 7,
  state: 'new',
  direction: 'recognition',
  lexeme: {
    id: 1, lemma: 'спасибо', stressed: 'спаси́бо', ipa: '[spɐˈsʲibə]',
    transliteration: 'spasibo', translation: 'thank you',
    part_of_speech: 'phrase', mnemonic: null, examples: [],
  },
};

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);
vi.stubGlobal('speechSynthesis', { speak: vi.fn(), cancel: vi.fn() });
vi.stubGlobal('SpeechSynthesisUtterance', class { constructor(public text: string) {} });

function mockApi(queue: unknown[]) {
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    if (String(url).includes('/reviews/queue')) {
      return { ok: true, status: 200,
               json: async () => ({ total_due: queue.length, cards: queue }) };
    }
    if (init?.method === 'POST') {
      return { ok: true, status: 200,
               json: async () => ({ card_id: 7, state: 'review', stability: 3,
                                    difficulty: 5, interval_days: 3,
                                    due_at: '2026-01-01', achievements: [] }) };
    }
    return { ok: true, status: 200, json: async () => ({}) };
  });
}

describe('<Review />', () => {
  beforeEach(() => fetchMock.mockReset());
  afterEach(cleanup);

  it('shows the empty state when nothing is due', async () => {
    mockApi([]);
    render(<MemoryRouter><Review /></MemoryRouter>);
    await waitFor(() =>
      expect(screen.getByText(/Nothing due right now/)).toBeTruthy(),
    );
  });

  it('reveals the answer and rates a card', async () => {
    mockApi([CARD]);
    render(<MemoryRouter><Review /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/спаси́бо/)).toBeTruthy());
    expect(screen.queryByText('thank you')).toBeNull(); // hidden until reveal

    await userEvent.click(screen.getByRole('button', { name: 'Show answer' }));
    expect(screen.getByText('thank you')).toBeTruthy();

    await userEvent.click(screen.getByRole('button', { name: 'Good' }));
    await waitFor(() => {
      const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST');
      expect(post).toBeTruthy();
      expect(String(post![0])).toContain('/reviews/7');
    });
  });

  it('supports the keyboard flow: space reveals, 3 rates Good', async () => {
    mockApi([CARD]);
    render(<MemoryRouter><Review /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/спаси́бо/)).toBeTruthy());

    await userEvent.keyboard(' ');
    expect(screen.getByText('thank you')).toBeTruthy();

    await userEvent.keyboard('3');
    await waitFor(() => {
      const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST');
      expect(post).toBeTruthy();
      expect(JSON.parse(String(post![1]?.body))).toEqual({ rating: 3 });
    });
  });
});
