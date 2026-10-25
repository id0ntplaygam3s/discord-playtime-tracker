import { useEffect, useCallback, useRef } from 'react';

interface ShortcutConfig {
  key: string;
  shiftKey?: boolean;
  ctrlKey?: boolean;
  altKey?: boolean;
  action: () => void;
  description?: string;
}

export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]) {
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    const config = shortcutsRef.current.find(
      (s) =>
        s.key.toLowerCase() === e.key.toLowerCase() &&
        (!s.shiftKey || e.shiftKey === s.shiftKey) &&
        (!s.ctrlKey || e.ctrlKey === s.ctrlKey) &&
        (!s.altKey || e.altKey === s.altKey)
    );

    if (config) {
      const target = e.target as HTMLElement;
      const tagName = target.tagName;
      const isInput = target.isContentEditable || tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT';

      if (!isInput) {
        e.preventDefault();
        config.action();
      }
    }
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

export function useKeyboardShortcut(key: string, action: () => void, options?: { shiftKey?: boolean; ctrlKey?: boolean; altKey?: boolean }) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const tagName = target.tagName;
      const isInput = target.isContentEditable || tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT';

      if (!isInput &&
        e.key.toLowerCase() === key.toLowerCase() &&
        (!options?.shiftKey || e.shiftKey === options.shiftKey) &&
        (!options?.ctrlKey || e.ctrlKey === options.ctrlKey) &&
        (!options?.altKey || e.altKey === options.altKey)
      ) {
        e.preventDefault();
        action();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [key, action, options]);
}
