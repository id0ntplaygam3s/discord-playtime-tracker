import { useEffect, useMemo, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { getMe } from './api/adminApi';
import AppLayout from './layouts/AppLayout';
import ActivityPage from './pages/ActivityPage';
import AuditLogPage from './pages/AuditLogPage';
import ComparePage from './pages/ComparePage';
import DashboardPage from './pages/DashboardPage';
import GameProfilePage from './pages/GameProfilePage';
import GamesPage from './pages/GamesPage';
import GamesGraphPage from './pages/GamesGraphPage';
import ImportsPage from './pages/ImportsPage';
import LoginPage from './pages/LoginPage';
import PlaytimeManagementPage from './pages/PlaytimeManagementPage';
import SimpleListPage from './pages/SimpleListPage';
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
  const [role, setRole] = useState<'admin' | 'viewer' | null>(null);
  const [layoutPreference, setLayoutPreference] = useState<LayoutModePreference>(() => {
    const stored = localStorage.getItem('tracker_layout_mode');
    return stored === 'mobile' || stored === 'desktop' || stored === 'auto' ? stored : 'auto';
  });
  const [deviceIsMobile, setDeviceIsMobile] = useState<boolean>(detectDeviceMobile);
  const statusText = useMemo(
    () =>
      'This page scaffolds the complete feature area and can be extended with dedicated API-backed tables and controls.',
    []
  );
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
    if (!authed) {
      setRole(null);
      return;
    }
    const loadRole = async () => {
      try {
        const me = await getMe();
        setRole(me.role);
      } catch {
        localStorage.removeItem('tracker_token');
        setAuthed(false);
      }
    };
    void loadRole();
  }, [authed]);

  const handleSignOut = () => {
    localStorage.removeItem('tracker_token');
    localStorage.removeItem('tracker_force_admin_login');
    setRole(null);
    setAuthed(false);
  };

  const handleSwitchToAdmin = () => {
    localStorage.setItem('tracker_force_admin_login', '1');
    handleSignOut();
  };

  if (!authed) {
    return <LoginPage onAuth={() => setAuthed(true)} />;
  }

  if (!role) {
    return <div className="panel">Loading account...</div>;
  }

  const isAdmin = role === 'admin';

  return (
    <Routes>
      <Route
        element={
          <AppLayout
            isAdmin={isAdmin}
            onSignOut={handleSignOut}
            onSwitchToAdmin={handleSwitchToAdmin}
            layoutMode={resolvedLayoutMode}
            layoutPreference={layoutPreference}
            onLayoutPreferenceChange={setLayoutPreference}
          />
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/games" element={<GamesPage />} />
        <Route path="/games-graph" element={<GamesGraphPage />} />
        <Route path="/games/:gameId" element={<GameProfilePage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/users-graph" element={<UsersGraphPage />} />
        <Route path="/users/:userId" element={<UserProfilePage />} />
        <Route path="/activity" element={<ActivityPage />} />
        <Route path="/compare" element={<ComparePage />} />
        {isAdmin && <Route path="/playtime-management" element={<PlaytimeManagementPage />} />}
        {isAdmin && <Route path="/imports" element={<ImportsPage />} />}
        {isAdmin && <Route path="/audit-log" element={<AuditLogPage />} />}
        {isAdmin && <Route path="/system-status" element={<SystemStatusPage />} />}
        {isAdmin && <Route path="/settings" element={<SimpleListPage title="Settings" text={statusText} />} />}
      </Route>
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
