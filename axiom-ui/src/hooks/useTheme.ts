import { useCallback, useEffect, useState } from 'react';

export type Theme = 'light' | 'dark';

const THEME_KEY = 'axiom.theme';
const THEME_EVENT = 'axiom:theme-change';

function systemTheme(): Theme {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function storedTheme(): Theme | null {
  try {
    const value = window.localStorage?.getItem(THEME_KEY);
    return value === 'light' || value === 'dark' ? value : null;
  } catch {
    return null;
  }
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  document.documentElement.style.colorScheme = theme;
}

export function initializeTheme() {
  applyTheme(storedTheme() ?? systemTheme());
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => storedTheme() ?? systemTheme());

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    const media = window.matchMedia?.('(prefers-color-scheme: dark)');
    const handleSystemChange = () => {
      if (!storedTheme()) setThemeState(systemTheme());
    };
    const handleThemeChange = (event: Event) => {
      setThemeState((event as CustomEvent<Theme>).detail);
    };

    media?.addEventListener('change', handleSystemChange);
    window.addEventListener(THEME_EVENT, handleThemeChange);
    return () => {
      media?.removeEventListener('change', handleSystemChange);
      window.removeEventListener(THEME_EVENT, handleThemeChange);
    };
  }, []);

  const setTheme = useCallback((next: Theme) => {
    try {
      window.localStorage?.setItem(THEME_KEY, next);
    } catch {
      // The selected theme still applies for this session when storage is unavailable.
    }
    applyTheme(next);
    window.dispatchEvent(new CustomEvent<Theme>(THEME_EVENT, { detail: next }));
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  }, [setTheme, theme]);

  return { theme, setTheme, toggleTheme };
}
