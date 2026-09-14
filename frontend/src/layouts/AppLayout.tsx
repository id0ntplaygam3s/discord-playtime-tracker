import { NavLink, Outlet } from 'react-router-dom';

const baseNavItems = [
  ['/', 'Dashboard'],
  ['/games', 'Games'],
  ['/users', 'Users'],
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
}

export default function AppLayout({ isAdmin, onSignOut, onSwitchToAdmin }: AppLayoutProps) {
  const navItems = isAdmin ? [...baseNavItems, ...adminNavItems] : baseNavItems;

  return (
    <div className="layout-shell">
      <aside className="sidebar">
        <div className="brand">Discord Game Tracker</div>
        <nav>
          {navItems.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'} className="nav-link">
              {label}
            </NavLink>
          ))}
        </nav>
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
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
