import { useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { getMe } from './api/adminApi';
import { AppPreferencesProvider } from './context/AppPreferencesContext';
import { MeResponse } from './types';
import AppLayout from './layouts/AppLayout';
import ActivityPage from './pages/ActivityPage';
import AuditLogPage from './pages/AuditLogPage';
import ComparePage from './pages/ComparePage';
import DashboardPage from './pages/DashboardPage';
import GameProfilePage from './pages/GameProfilePage';
import GamesAdminPage from './pages/GamesAdminPage';
import GamesPage from './pages/GamesPage';
import GamesGraphPage from './pages/GamesGraphPage';
import ImportsPage from './pages/ImportsPage';
import LoginPage from './pages/LoginPage';
import PlaytimeManagementPage from './pages/PlaytimeManagementPage';
import AccountsPage from './pages/AccountsPage';
import PermissionsPage from './pages/PermissionsPage';
import RegistrationsPage from './pages/RegistrationsPage';
import SettingsPage from './pages/SettingsPage';
import SystemStatusPage from './pages/SystemStatusPage';
import UserProfilePage from './pages/UserProfilePage';
import UsersGraphPage from './pages/UsersGraphPage';
import UsersPage from './pages/UsersPage';

function isAuthenticated(): boolean {
  return Boolean(localStorage.getItem('tracker_token'));
}

type LayoutModePreference = 'auto' | 'mobile' | 'desktop';
type LayoutMode = 'mobile' | 'desktop';

function detectDeviceMobile(): boolean {
  if (typeof window === 'undefined') return false;
  const mobileMedia = window.matchMedia('(max-width: 980px)').matches;
  const touchMedia = window.matchMedia('(pointer: coarse)').matches;
  return mobileMedia || touchMedia;
}

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [me, setMe] = useState<MeResponse | null>(null);
  const [layoutPreference, setLayoutPreference] = useState<LayoutModePreference>(() => {
    const stored = localStorage.getItem('tracker_layout_mode');
    return stored === 'mobile' || stored === 'desktop' || stored === 'auto' ? stored : 'auto';
  });
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState<boolean>(() => localStorage.getItem('tracker_auto_refresh') !== '0');
  const [deviceIsMobile, setDeviceIsMobile] = useState<boolean>(detectDeviceMobile);
  const resolvedLayoutMode: LayoutMode = layoutPreference === 'auto' ? (deviceIsMobile ? 'mobile' : 'desktop') : layoutPreference;

  useEffect(() => {
    document.title = 'Discord Playtime Tracker';
  }, []);

  useEffect(() => {
    const update = () => setDeviceIsMobile(detectDeviceMobile());
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  useEffect(() => {
    localStorage.setItem('tracker_layout_mode', layoutPreference);
  }, [layoutPreference]);

  useEffect(() => {
    localStorage.setItem('tracker_auto_refresh', autoRefreshEnabled ? '1' : '0');
  }, [autoRefreshEnabled]);

  useEffect(() => {
    if (!authed) {
      setMe(null);
      return;
    }
    const loadSession = async () => {
      try {
        const session = await getMe();
        setMe(session);
      } catch {
        localStorage.removeItem('tracker_token');
        setAuthed(false);
      }
    };
    void loadSession();
  }, [authed]);

  const handleSignOut = () => {
    localStorage.removeItem('tracker_token');
    localStorage.removeItem('tracker_force_admin_login');
    setMe(null);
    setAuthed(false);
  };

  const handleSwitchToAdmin = () => {
    localStorage.setItem('tracker_force_admin_login', '1');
    handleSignOut();
  };

  if (!authed) {
    return <LoginPage onAuth={() => setAuthed(true)} />;
  }

  if (!me) {
    return <div className="panel">Loading account...</div>;
  }

  const isAdmin = me.role_name === 'admin';
  const permissionSet = new Set(me.permissions || []);

  const canViewDashboard = permissionSet.has('dashboard.view');
  const canViewGames = permissionSet.has('games.view');
  const canViewUsers = permissionSet.has('users.view');
  const canViewPlaytime = permissionSet.has('playtime.view');
  const canManageOwnPlaytime = permissionSet.has('playtime.manage_own');
  const canManageAllPlaytime = permissionSet.has('playtime.manage_all');
  const canManageImports = permissionSet.has('imports.manage');
  const canViewAudit = permissionSet.has('audit.view');
  const canViewSettings = permissionSet.has('settings.view');
  const canManageUsers = permissionSet.has('users.manage');
  const canViewRegistrations = permissionSet.has('registrations.view');
  const canViewPermissions = permissionSet.has('permissions.view');
  const canManagePermissions = permissionSet.has('permissions.manage');

  return (
    <AppPreferencesProvider value={{ autoRefreshEnabled }}>
      <Routes>
      <Route
        element={
          <AppLayout
            isAdmin={isAdmin}
            me={me}
            onSignOut={handleSignOut}
            onSwitchToAdmin={handleSwitchToAdmin}
            layoutMode={resolvedLayoutMode}
            layoutPreference={layoutPreference}
            onLayoutPreferenceChange={setLayoutPreference}
            autoRefreshEnabled={autoRefreshEnabled}
            onAutoRefreshChange={setAutoRefreshEnabled}
          />
        }
      >
        {canViewDashboard && <Route path="/" element={<DashboardPage />} />}
        {canViewGames && <Route path="/games" element={<GamesPage />} />}
        {canViewGames && <Route path="/games-graph" element={<GamesGraphPage />} />}
        {canManagePermissions && <Route path="/games-admin" element={<GamesAdminPage />} />}
        {canViewGames && <Route path="/games/:gameId" element={<GameProfilePage />} />}
        {canViewUsers && <Route path="/users" element={<UsersPage />} />}
        {canViewUsers && <Route path="/users-graph" element={<UsersGraphPage />} />}
        {canViewUsers && <Route path="/users/:userId" element={<UserProfilePage />} />}
        {canViewPlaytime && <Route path="/activity" element={<ActivityPage />} />}
        {canViewPlaytime && <Route path="/compare" element={<ComparePage />} />}
        {(canManageAllPlaytime || canManageOwnPlaytime) && <Route path="/playtime-management" element={<PlaytimeManagementPage />} />}
        {canManageImports && <Route path="/imports" element={<ImportsPage />} />}
        {canViewAudit && <Route path="/audit-log" element={<AuditLogPage />} />}
        {canViewSettings && <Route path="/system-status" element={<SystemStatusPage />} />}
        {canViewRegistrations && <Route path="/registrations" element={<RegistrationsPage />} />}
        {canManageUsers && <Route path="/accounts" element={<AccountsPage />} />}
        {canViewPermissions && <Route path="/permissions" element={<PermissionsPage />} />}
        {canViewSettings && <Route path="/settings" element={<SettingsPage />} />}
      </Route>
      <Route path="*" element={<Navigate to={canViewDashboard ? '/' : '/games'} />} />
      </Routes>
    </AppPreferencesProvider>
  );
}
