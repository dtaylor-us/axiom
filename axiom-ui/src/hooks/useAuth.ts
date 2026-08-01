import { useStore } from '../store/useStore';

/**
 * Hook exposing auth state and actions from the store.
 *
 * Views must access auth through this hook instead of importing
 * the store directly (ADL-022: State Management Boundary).
 */
export function useAuth() {
  const token = useStore((s) => s.token);
  const username = useStore((s) => s.username);
  const setAuth = useStore((s) => s.setAuth);
  const clearAuth = useStore((s) => s.clearAuth);

  return { token, username, setAuth, clearAuth };
}
