import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';

export type ThemeMode = 'dark' | 'light' | 'auto';

interface ThemeContextValue {
  theme: ThemeMode;
  resolvedTheme: 'dark' | 'light';
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: 'dark',
  resolvedTheme: 'dark',
  setTheme: () => {},
  toggleTheme: () => {},
});

function getSystemTheme(): 'dark' | 'light' {
  if (typeof window === 'undefined') return 'dark';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme: 'dark' | 'light') {
  document.documentElement.setAttribute('data-theme', theme);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem('tracker_theme') as ThemeMode | null;
    return stored === 'dark' || stored === 'light' || stored === 'auto' ? stored : 'dark';
  });

  const [resolvedTheme, setResolvedTheme] = useState<'dark' | 'light'>('dark');

  const setTheme = useCallback((newTheme: ThemeMode) => {
    setThemeState(newTheme);
    localStorage.setItem('tracker_theme', newTheme);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next: ThemeMode = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem('tracker_theme', next);
      return next;
    });
  }, []);

  useEffect(() => {
    const resolved = theme === 'auto' ? getSystemTheme() : theme;
    setResolvedTheme(resolved);
    applyTheme(resolved);
  }, [theme]);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      if (theme === 'auto') {
        setResolvedTheme(getSystemTheme());
        applyTheme(getSystemTheme());
      }
    };
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
