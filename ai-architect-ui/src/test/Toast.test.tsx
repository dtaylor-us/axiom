import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ToastProvider, useToast, emitToast } from '../components/Toast';

/**
 * Wrapper component that exposes the show() function for testing by
 * rendering a button that triggers toast display.
 */
function ShowToastButton({
  message,
  type,
  duration,
}: {
  message: string;
  type?: 'error' | 'warning' | 'info';
  duration?: number;
}) {
  const { show } = useToast();
  return (
    <button type="button" onClick={() => show(message, type, duration)}>
      Show
    </button>
  );
}

function WithProvider({ children }: { children: React.ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}

describe('Toast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('rendersToastMessageWhenShown', async () => {
    render(
      <WithProvider>
        <ShowToastButton message="Something went wrong" />
      </WithProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Show' }));

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('rendersErrorToastWithAlertRole', () => {
    render(
      <WithProvider>
        <ShowToastButton message="Error toast" type="error" />
      </WithProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Show' }));

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('rendersWarningToast', () => {
    render(
      <WithProvider>
        <ShowToastButton message="Warning toast" type="warning" />
      </WithProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Show' }));

    expect(screen.getByText('Warning toast')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('rendersInfoToast', () => {
    render(
      <WithProvider>
        <ShowToastButton message="Info toast" type="info" />
      </WithProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Show' }));

    expect(screen.getByText('Info toast')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('dismissesOnButtonClick', () => {
    render(
      <WithProvider>
        <ShowToastButton message="Dismissable" />
      </WithProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Show' }));
    expect(screen.getByText('Dismissable')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Dismiss notification' }));
    expect(screen.queryByText('Dismissable')).not.toBeInTheDocument();
  });

  it('autoDismissesAfterDuration', async () => {
    render(
      <WithProvider>
        <ShowToastButton message="Auto dismiss" duration={1000} />
      </WithProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Show' }));
    expect(screen.getByText('Auto dismiss')).toBeInTheDocument();

    // Advance past the duration and flush React state updates.
    await act(async () => {
      vi.advanceTimersByTime(1001);
    });

    expect(screen.queryByText('Auto dismiss')).not.toBeInTheDocument();
  });

  it('capsAtFourToastsAndDropsOldest', () => {
    render(
      <WithProvider>
        <ShowToastButton message="toast" />
      </WithProvider>,
    );

    const btn = screen.getByRole('button', { name: 'Show' });
    // Show 5 toasts — only 4 should remain (oldest is dropped)
    for (let i = 0; i < 5; i++) {
      fireEvent.click(btn);
    }

    expect(screen.getAllByRole('alert')).toHaveLength(4);
  });

  it('showsToastViaWindowEvent', () => {
    render(<ToastProvider><div /></ToastProvider>);

    act(() => {
      emitToast('Event toast', 'info');
    });

    expect(screen.getByText('Event toast')).toBeInTheDocument();
  });

  it('ignoresWindowEventWithoutMessage', () => {
    render(<ToastProvider><div /></ToastProvider>);

    act(() => {
      window.dispatchEvent(
        new CustomEvent('archon:toast', { detail: { message: '' } }),
      );
    });

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('rendersNothingWhenNoToasts', () => {
    render(<ToastProvider><div data-testid="child" /></ToastProvider>);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
