import { FormEvent, useEffect, useState } from 'react';
import { guestLogin, login } from '../api/trackerApi';

export default function LoginPage({ onAuth }: { onAuth: () => void }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [showAdminForm, setShowAdminForm] = useState(() => localStorage.getItem('tracker_force_admin_login') === '1');
  const [isGuestLoading, setIsGuestLoading] = useState(false);
  const [isAdminLoading, setIsAdminLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (localStorage.getItem('tracker_force_admin_login') === '1') {
      localStorage.removeItem('tracker_force_admin_login');
    }
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsAdminLoading(true);
    try {
      const token = await login(username, password);
      localStorage.setItem('tracker_token', token);
      onAuth();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Login failed');
    } finally {
      setIsAdminLoading(false);
    }
  };

  const handleGuestLogin = async () => {
    setError(null);
    setIsGuestLoading(true);
    try {
      const token = await guestLogin();
      localStorage.setItem('tracker_token', token);
      onAuth();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Guest access failed');
    } finally {
      setIsGuestLoading(false);
    }
  };

  return (
    <div className="login-shell">
      <div className="login-card">
        <h1>Discord Game Tracker</h1>
        <p>Private playtime analytics for your Discord guild.</p>

        <button type="button" className="primary-login-btn" onClick={handleGuestLogin} disabled={isGuestLoading || isAdminLoading}>
          {isGuestLoading ? 'Entering Dashboard...' : 'Continue as Guest'}
        </button>

        <button
          type="button"
          className="secondary-login-btn"
          onClick={() => {
            setShowAdminForm((prev) => !prev);
            setError(null);
          }}
          disabled={isGuestLoading || isAdminLoading}
        >
          {showAdminForm ? 'Hide Admin Login' : 'Admin Sign In'}
        </button>

        {showAdminForm && (
          <form className="admin-login-form" onSubmit={handleSubmit}>
            <label>Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} />
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="submit" disabled={isAdminLoading || isGuestLoading}>
              {isAdminLoading ? 'Signing In...' : 'Sign in as Admin'}
            </button>
          </form>
        )}

        {error && <div className="error-box">{error}</div>}
      </div>
    </div>
  );
}
