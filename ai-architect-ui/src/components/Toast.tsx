import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import type { ReactElement, ReactNode } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────

export type ToastType = 'error' | 'warning' | 'info';

interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
  /** Duration in ms. Defaults: error 8 000, warning 5 000, info 4 000. */
  duration: number;
}

interface ToastContextValue {
  show: (message: string, type?: ToastType, duration?: number) => void;
}

const DEFAULT_DURATIONS: Record<ToastType, number> = {
  error:   8_000,
  warning: 5_000,
  info:    4_000,
};

// ── Context ───────────────────────────────────────────────────────────────────

const ToastContext = createContext<ToastContextValue>({
  show: () => undefined,
});

// ── Custom event bridge ───────────────────────────────────────────────────────
// Non-React code (e.g. api modules) can show toasts without importing React
// by dispatching a 'archon:toast' CustomEvent on window.

export interface ToastEventDetail {
  message: string;
  type?: ToastType;
  duration?: number;
}

/** Emit a toast from anywhere — api modules, plain TS utilities, etc. */
export function emitToast(message: string, type: ToastType = 'error', duration?: number): void {
  const detail: ToastEventDetail = { message, type, duration };
  window.dispatchEvent(new CustomEvent('archon:toast', { detail }));
}

// ── ToastProvider ─────────────────────────────────────────────────────────────

let _idCounter = 0;
function nextId(): string {
  return `toast-${++_idCounter}`;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const t = timersRef.current.get(id);
    if (t !== undefined) {
      clearTimeout(t);
      timersRef.current.delete(id);
    }
  }, []);

  const show = useCallback(
    (message: string, type: ToastType = 'error', duration?: number) => {
      const id = nextId();
      const ms = duration ?? DEFAULT_DURATIONS[type];
      setToasts((prev) => {
        // Cap at 4 visible toasts — drop the oldest
        const capped = prev.length >= 4 ? prev.slice(1) : prev;
        return [...capped, { id, message, type, duration: ms }];
      });
      const timer = setTimeout(() => dismiss(id), ms);
      timersRef.current.set(id, timer);
    },
    [dismiss],
  );

  // Listen for window-level events from non-React code
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<ToastEventDetail>).detail;
      if (detail?.message) show(detail.message, detail.type, detail.duration);
    };
    window.addEventListener('archon:toast', handler);
    return () => window.removeEventListener('archon:toast', handler);
  }, [show]);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useToast(): ToastContextValue {
  return useContext(ToastContext);
}

// ── ToastContainer ────────────────────────────────────────────────────────────

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

const ICON: Record<ToastType, ReactElement> = {
  error: (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <circle cx="8" cy="8" r="6.5" />
      <path d="M8 5v3.5" />
      <circle cx="8" cy="11" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  ),
  warning: (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M8 2L1.5 13.5h13L8 2z" />
      <path d="M8 6.5v3" />
      <circle cx="8" cy="11.5" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  ),
  info: (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <circle cx="8" cy="8" r="6.5" />
      <path d="M8 7v5" />
      <circle cx="8" cy="4.5" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  ),
};

const STYLE: Record<ToastType, string> = {
  error:   'bg-white border border-red-200 text-red-800 shadow-lg shadow-red-100/50',
  warning: 'bg-white border border-amber-200 text-amber-800 shadow-lg shadow-amber-100/50',
  info:    'bg-white border border-gray-200 text-gray-700 shadow-lg shadow-gray-100/50',
};

const ICON_STYLE: Record<ToastType, string> = {
  error:   'text-red-500',
  warning: 'text-amber-500',
  info:    'text-gray-400',
};

function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 left-4 z-50 flex flex-col gap-2 w-80 max-w-[calc(100vw-2rem)]"
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="alert"
          className={`flex items-start gap-3 rounded-xl px-4 py-3 text-sm animate-in slide-in-from-bottom-2 fade-in duration-200 ${STYLE[toast.type]}`}
        >
          <span className={`mt-0.5 ${ICON_STYLE[toast.type]}`}>
            {ICON[toast.type]}
          </span>
          <p className="flex-1 leading-snug">{toast.message}</p>
          <button
            type="button"
            onClick={() => onDismiss(toast.id)}
            className="shrink-0 opacity-50 hover:opacity-80 transition-opacity mt-0.5"
            aria-label="Dismiss notification"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M2 2l8 8M10 2l-8 8" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
