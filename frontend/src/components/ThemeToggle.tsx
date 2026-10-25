import { useTheme } from '../context/ThemeProvider';

export default function ThemeToggle() {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();

  const iconMap = {
    dark: '☀️',
    light: '🌙',
    auto: '💻',
  };

  const labelMap = {
    dark: 'Dark',
    light: 'Light',
    auto: 'Auto',
  };

  return (
    <div className="theme-switcher" role="group" aria-label="Theme selection">
      <button
        type="button"
        className={`theme-btn ${theme === 'auto' ? 'theme-btn-active' : ''}`}
        onClick={() => setTheme('auto')}
        title="Follow system theme"
        aria-pressed={theme === 'auto'}
      >
        {iconMap.auto}
        <span className="theme-label">{labelMap.auto}</span>
      </button>
      <button
        type="button"
        className={`theme-btn ${theme === 'dark' ? 'theme-btn-active' : ''}`}
        onClick={() => setTheme('dark')}
        title="Force dark theme"
        aria-pressed={theme === 'dark'}
      >
        {iconMap.dark}
        <span className="theme-label">{labelMap.dark}</span>
      </button>
      <button
        type="button"
        className={`theme-btn ${theme === 'light' ? 'theme-btn-active' : ''}`}
        onClick={() => setTheme('light')}
        title="Force light theme"
        aria-pressed={theme === 'light'}
      >
        {iconMap.light}
        <span className="theme-label">{labelMap.light}</span>
      </button>
    </div>
  );
}
