// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Login from './Login';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

describe('<Login />', () => {
  beforeEach(() => fetchMock.mockReset());
  afterEach(cleanup);

  it('renders login form and toggles to registration', async () => {
    render(<Login onLoggedIn={async () => {}} />);
    expect(screen.getByRole('button', { name: 'Log in' })).toBeTruthy();
    expect(screen.queryByLabelText('Display name')).toBeNull();

    await userEvent.click(screen.getByText(/create an account/i));
    expect(screen.getByLabelText('Display name')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Create account' })).toBeTruthy();
  });

  it('shows an error message on failed login', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ detail: 'Incorrect email or password' }),
    });
    render(<Login onLoggedIn={async () => {}} />);
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.com');
    await userEvent.type(screen.getByLabelText('Password'), 'password123');
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }));
    await waitFor(() =>
      expect(screen.getByText('Incorrect email or password')).toBeTruthy(),
    );
  });

  it('stores the token and calls onLoggedIn on success', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'token-123' }),
    });
    const onLoggedIn = vi.fn(async () => {});
    render(<Login onLoggedIn={onLoggedIn} />);
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.com');
    await userEvent.type(screen.getByLabelText('Password'), 'password123');
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }));
    await waitFor(() => expect(onLoggedIn).toHaveBeenCalled());
    expect(localStorage.getItem('rli_token')).toBe('token-123');
  });
});
