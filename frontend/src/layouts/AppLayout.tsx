import { NavLink, Outlet } from 'react-router-dom';
import { MeResponse } from '../types';

type NavItem = [string, string, string?];

const navItems: NavItem[] = [
  ['/', 'Dashboard', 'dashboard.view'],
  ['/games', 'Games', 'games.view'],
  ['/games-graph', 'Games (Graph)', 'games.view'],
  ['/games-admin', 'Games Admin', 'permissions.manage'],
  ['/users', 'Users', 'users.view'],
  ['/users-graph', 'User Activity (Graph)', 'users.view'],
  ['/activity', 'Activity', 'playtime.view'],
  ['/compare', 'Compare', 'playtime.view'],
  ['/playtime-management', 'Playtime Management', 'playtime.manage_own'],
  ['/imports', 'Imports', 'imports.manage'],
  ['/audit-log', 'Audit Log', 'audit.view'],
  ['/system-status', 'System Status', 'settings.view'],
  ['/registrations', 'Registrations', 'registrations.view'],
  ['/accounts', 'Accounts', 'users.manage'],
  ['/permissions', 'Permissions', 'permissions.view'],
  ['/settings', 'Settings', 'settings.view'],
];

interface AppLayoutProps {
  me: MeResponse;
  onSignOut: () => void;
  onSwitchToAdmin: () => void;
  layoutMode: 'mobile' | 'desktop';
  layoutPreference: 'auto' | 'mobile' | 'desktop';
  onLayoutPreferenceChange: (mode: 'auto' | 'mobile' | 'desktop') => void;
  autoRefreshEnabled: boolean;
  onAutoRefreshChange: (enabled: boolean) => void;
}

export default function AppLayout({
  me,
  onSignOut,
  onSwitchToAdmin,
  layoutMode,
  layoutPreference,
  onLayoutPreferenceChange,
  autoRefreshEnabled,
  onAutoRefreshChange,
}: AppLayoutProps) {
  const permissionSet = new Set(me.permissions || []);
  const visibleNavItems = navItems.filter((item) => {
    const permission = item[2];
    return permission ? permissionSet.has(permission) : true;
  });

  return (
    <div className={`layout-shell layout-${layoutMode}`}>
      <aside className="sidebar">
        <div className="brand">Discord Playtime Tracker</div>
        <nav>
          {visibleNavItems.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'} className="nav-link">
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="subtle" style={{ marginTop: 10, fontSize: '0.85rem' }}>
          Signed in as: {me.is_guest ? 'Guest' : me.username} ({me.role_name})
        </div>
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
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={autoRefreshEnabled}
              onChange={(e) => onAutoRefreshChange(e.target.checked)}
            />
            Auto refresh
          </label>
        </div>
        <div className="sidebar-actions">
          {me.is_guest && (
            <button type="button" className="sidebar-btn" onClick={onSwitchToAdmin}>
              Return to Login
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
