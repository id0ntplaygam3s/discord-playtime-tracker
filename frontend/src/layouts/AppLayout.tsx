import { NavLink, Outlet } from 'react-router-dom';

const baseNavItems = [
  ['/', 'Dashboard'],
  ['/games', 'Games'],
  ['/games-graph', 'Games (Graph)'],
  ['/users', 'Users'],
  ['/users-graph', 'User Activity (Graph)'],
  ['/activity', 'Activity'],
  ['/compare', 'Compare'],
];

const adminNavItems = [
  ['/playtime-management', 'Playtime Management'],
  ['/imports', 'Imports'],
  ['/audit-log', 'Audit Log'],
  ['/system-status', 'System Status'],
  ['/settings', 'Settings'],
];

interface AppLayoutProps {
  isAdmin: boolean;
  onSignOut: () => void;
  onSwitchToAdmin: () => void;
  layoutMode: 'mobile' | 'desktop';
  layoutPreference: 'auto' | 'mobile' | 'desktop';
  onLayoutPreferenceChange: (mode: 'auto' | 'mobile' | 'desktop') => void;
}

export default function AppLayout({
  isAdmin,
  onSignOut,
  onSwitchToAdmin,
  layoutMode,
  layoutPreference,
  onLayoutPreferenceChange,
}: AppLayoutProps) {
  const navItems = isAdmin ? [...baseNavItems, ...adminNavItems] : baseNavItems;

  return (
    <div className={`layout-shell layout-${layoutMode}`}>
      <aside className="sidebar">
        <div className="brand">Discord Playtime Tracker</div>
        <nav>
          {navItems.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'} className="nav-link">
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mode-switcher">
          <label htmlFor="layout-mode">Layout Mode</label>
          <select
            id="layout-mode"
            value={layoutPreference}
            onChange={(e) => onLayoutPreferenceChange(e.target.value as 'auto' | 'mobile' | 'desktop')}
          >
            <option value="auto">Auto (device)</option>
            <option value="mobile">Force mobile</option>
            <option value="desktop">Force desktop</option>
          </select>
        </div>
        <div className="sidebar-actions">
          {!isAdmin && (
            <button type="button" className="sidebar-btn" onClick={onSwitchToAdmin}>
              Switch to Admin
            </button>
          )}
          <button type="button" className="sidebar-btn" onClick={onSignOut}>
            Sign out
          </button>
        </div>
        <div className="sidebar-credit">
          Created by{' '}
          <a
            className="sidebar-credit-link"
            href="https://github.com/id0ntplaygam3s/discord-playtime-tracker"
            target="_blank"
            rel="noreferrer"
          >
            id0ntplaygam3s
          </a>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
