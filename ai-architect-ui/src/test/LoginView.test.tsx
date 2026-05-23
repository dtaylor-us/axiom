import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginView } from '../views/LoginView';
import { useStore } from '../store/useStore';

vi.mock('../api/auth', () => ({
  getToken: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
}));

import { getToken, login, register } from '../api/auth';

const mockGetToken = vi.mocked(getToken);
const mockLogin = vi.mocked(login);
const mockRegister = vi.mocked(register);

function resetStore() {
  useStore.getState().clearAuth();
  useStore.getState().resetConversation();
}

describe('LoginView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStore();
  });

  it('defaultsToLoginMode', () => {
    render(<LoginView />);
    expect(screen.getByTestId('login-view')).toBeInTheDocument();
    expect(screen.queryByTestId('auth-name')).not.toBeInTheDocument();
    expect(screen.getByTestId('auth-email')).toBeInTheDocument();
    expect(screen.getByTestId('auth-password')).toBeInTheDocument();
    expect(screen.getByTestId('auth-submit')).toHaveTextContent('Sign in');
  });

  it('togglesToRegisterMode', async () => {
    const user = userEvent.setup();
    render(<LoginView />);

    await user.click(screen.getByTestId('auth-toggle'));
    expect(screen.getByTestId('auth-name')).toBeInTheDocument();
    expect(screen.getByTestId('auth-submit')).toHaveTextContent('Create account');
  });

  it('submitsLoginAndSetsAuth', async () => {
    mockLogin.mockResolvedValue({ token: 'jwt-login', email: 'a@b.com' });

    const user = userEvent.setup();
    render(<LoginView />);

    await user.type(screen.getByTestId('auth-email'), 'a@b.com');
    await user.type(screen.getByTestId('auth-password'), 'password1');
    await user.click(screen.getByTestId('auth-submit'));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('a@b.com', 'password1');
    });

    await waitFor(() => {
      expect(useStore.getState().token).toBe('jwt-login');
      expect(useStore.getState().username).toBe('a@b.com');
    });
  });

  it('showsErrorOnLoginFailure', async () => {
    mockLogin.mockRejectedValue(new Error('Invalid credentials'));

    const user = userEvent.setup();
    render(<LoginView />);

    await user.type(screen.getByTestId('auth-email'), 'a@b.com');
    await user.type(screen.getByTestId('auth-password'), 'password1');
    await user.click(screen.getByTestId('auth-submit'));

    await waitFor(() => {
      expect(screen.getByTestId('auth-error')).toBeInTheDocument();
    });
    expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
  });

  it('submitsRegisterAndSetsAuth', async () => {
    mockRegister.mockResolvedValue({ token: 'jwt-reg' });

    const user = userEvent.setup();
    render(<LoginView />);

    await user.click(screen.getByTestId('auth-toggle'));
    await user.type(screen.getByTestId('auth-name'), 'Alice');
    await user.type(screen.getByTestId('auth-email'), 'a@b.com');
    await user.type(screen.getByTestId('auth-password'), 'password1');
    await user.click(screen.getByTestId('auth-submit'));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith('a@b.com', 'password1', 'Alice');
    });

    await waitFor(() => {
      expect(useStore.getState().token).toBe('jwt-reg');
      expect(useStore.getState().username).toBe('Alice');
    });
  });

  it('continuesAsGuest', async () => {
    mockGetToken.mockResolvedValue('jwt-guest');

    const user = userEvent.setup();
    render(<LoginView />);

    await user.click(screen.getByTestId('auth-guest'));

    await waitFor(() => {
      expect(mockGetToken).toHaveBeenCalledWith('Guest');
    });

    await waitFor(() => {
      expect(useStore.getState().token).toBe('jwt-guest');
      expect(useStore.getState().username).toBe('Guest');
    });
  });
});
