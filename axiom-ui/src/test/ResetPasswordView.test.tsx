import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { ResetPasswordView } from '../views/ResetPasswordView';

vi.mock('../api/auth', () => ({
  validateResetToken: vi.fn(),
  confirmPasswordReset: vi.fn(),
  ExpiredTokenError: class ExpiredTokenError extends Error {},
  NetworkError: class NetworkError extends Error {},
  PasswordResetValidationError: class PasswordResetValidationError extends Error {
    field: 'newPassword' | 'confirmPassword' | 'form';

    constructor(
      message: string,
      field: 'newPassword' | 'confirmPassword' | 'form' = 'form',
    ) {
      super(message);
      this.field = field;
    }
  },
}));

import {
  ExpiredTokenError,
  PasswordResetValidationError,
  confirmPasswordReset,
  validateResetToken,
} from '../api/auth';

const mockValidateResetToken = vi.mocked(validateResetToken);
const mockConfirmPasswordReset = vi.mocked(confirmPasswordReset);

function renderResetView(path = '/reset-password?token=abc123') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPasswordView />} />
        <Route path="/login" element={<div data-testid="login-route">Login Route</div>} />
        <Route path="/forgot-password" element={<div data-testid="forgot-route">Forgot Route</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ResetPasswordView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('showsExpiredStateWhenTokenValidationFails', async () => {
    mockValidateResetToken.mockResolvedValue({
      valid: false,
      message: 'This reset link has expired.',
    });

    renderResetView();

    await waitFor(() => {
      expect(screen.getByText('This link has expired')).toBeInTheDocument();
    });
  });

  it('submitsNewPasswordAfterSuccessfulValidation', async () => {
    mockValidateResetToken.mockResolvedValue({ valid: true });
    mockConfirmPasswordReset.mockResolvedValue({ message: 'updated' });
    const user = userEvent.setup();

    renderResetView();

    await waitFor(() => {
      expect(screen.getByTestId('reset-password-submit')).toBeInTheDocument();
    });

    await user.type(screen.getByTestId('reset-password-new'), 'NewSecurePassword123');
    await user.type(screen.getByTestId('reset-password-confirm'), 'NewSecurePassword123');
    await user.click(screen.getByTestId('reset-password-submit'));

    await waitFor(() => {
      expect(mockConfirmPasswordReset).toHaveBeenCalledWith(
        'abc123',
        'NewSecurePassword123',
        'NewSecurePassword123',
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId('reset-password-sign-in')).toBeInTheDocument();
    });
  });

  it('showsInlineFieldErrorForPasswordValidationFailures', async () => {
    mockValidateResetToken.mockResolvedValue({ valid: true });
    mockConfirmPasswordReset.mockRejectedValue(
      new PasswordResetValidationError(
        'New password must be different from your current password.',
        'newPassword',
      ),
    );
    const user = userEvent.setup();

    renderResetView();

    await waitFor(() => {
      expect(screen.getByTestId('reset-password-submit')).toBeInTheDocument();
    });

    await user.type(screen.getByTestId('reset-password-new'), 'NewSecurePassword123');
    await user.type(screen.getByTestId('reset-password-confirm'), 'NewSecurePassword123');
    await user.click(screen.getByTestId('reset-password-submit'));

    await waitFor(() => {
      expect(screen.getByTestId('reset-password-new-error')).toHaveTextContent(
        'New password must be different from your current password.',
      );
    });
  });

  it('switchesToExpiredStateWhenSubmissionTokenExpires', async () => {
    mockValidateResetToken.mockResolvedValue({ valid: true });
    mockConfirmPasswordReset.mockRejectedValue(
      new ExpiredTokenError('This reset link has expired or has already been used.'),
    );
    const user = userEvent.setup();

    renderResetView();

    await waitFor(() => {
      expect(screen.getByTestId('reset-password-submit')).toBeInTheDocument();
    });

    await user.type(screen.getByTestId('reset-password-new'), 'NewSecurePassword123');
    await user.type(screen.getByTestId('reset-password-confirm'), 'NewSecurePassword123');
    await user.click(screen.getByTestId('reset-password-submit'));

    await waitFor(() => {
      expect(screen.getByText('This link has expired')).toBeInTheDocument();
    });
  });
});
