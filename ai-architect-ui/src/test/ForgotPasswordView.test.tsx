import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { ForgotPasswordView } from '../views/ForgotPasswordView';

vi.mock('../api/auth', () => ({
  requestPasswordReset: vi.fn(),
  RateLimitError: class RateLimitError extends Error {},
  NetworkError: class NetworkError extends Error {},
}));

import {
  NetworkError,
  RateLimitError,
  requestPasswordReset,
} from '../api/auth';

const mockRequestPasswordReset = vi.mocked(requestPasswordReset);

describe('ForgotPasswordView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('showsConfirmationStateAfterSuccessfulRequest', async () => {
    mockRequestPasswordReset.mockResolvedValue({ message: 'ok' });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <ForgotPasswordView />
      </MemoryRouter>,
    );

    await user.type(screen.getByTestId('forgot-password-email'), 'a@b.com');
    await user.click(screen.getByTestId('forgot-password-submit'));

    await waitFor(() => {
      expect(screen.getByTestId('forgot-password-success')).toBeInTheDocument();
    });
  });

  it('showsRateLimitErrorInline', async () => {
    mockRequestPasswordReset.mockRejectedValue(
      new RateLimitError('Too many requests. Please wait before trying again.'),
    );
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <ForgotPasswordView />
      </MemoryRouter>,
    );

    await user.type(screen.getByTestId('forgot-password-email'), 'a@b.com');
    await user.click(screen.getByTestId('forgot-password-submit'));

    await waitFor(() => {
      expect(screen.getByTestId('forgot-password-error')).toHaveTextContent(
        'Too many requests. Please wait before trying again.',
      );
    });
  });

  it('showsRetryButtonForNetworkErrors', async () => {
    mockRequestPasswordReset.mockRejectedValue(
      new NetworkError('Unable to send a reset link right now. Please try again.'),
    );
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <ForgotPasswordView />
      </MemoryRouter>,
    );

    await user.type(screen.getByTestId('forgot-password-email'), 'a@b.com');
    await user.click(screen.getByTestId('forgot-password-submit'));

    await waitFor(() => {
      expect(screen.getByTestId('forgot-password-retry')).toBeInTheDocument();
    });
  });
});
