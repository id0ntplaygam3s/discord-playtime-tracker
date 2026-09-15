import { FormEvent, useEffect, useState } from 'react';
import {
  accountLogin,
  completePasswordReset,
  getAccountOptions,
  getRegistrationOptions,
  guestLogin,
  login,
  registerAccount,
  requestPasswordReset,
} from '../api/trackerApi';

export default function LoginPage({ onAuth }: { onAuth: () => void }) {
  const [mode, setMode] = useState<'account' | 'admin' | 'register' | 'forgot' | 'reset'>('account');
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [accountUserId, setAccountUserId] = useState<number>(0);
  const [registrationUserId, setRegistrationUserId] = useState<number>(0);
  const [resetUserId, setResetUserId] = useState<number>(0);
  const [registrationPassword, setRegistrationPassword] = useState('');
  const [registrationConfirm, setRegistrationConfirm] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [accountRows, setAccountRows] = useState<Array<{ user_id: number; username: string; display_name: string; status: string }>>([]);
  const [registrationRows, setRegistrationRows] = useState<Array<{ id: number; username: string; display_name: string }>>([]);
  const [isGuestLoading, setIsGuestLoading] = useState(false);
  const [isAdminLoading, setIsAdminLoading] = useState(false);
  const [isAccountLoading, setIsAccountLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (localStorage.getItem('tracker_force_admin_login') === '1') {
      localStorage.removeItem('tracker_force_admin_login');
      setMode('admin');
    }

    const loadOptions = async () => {
      try {
        const [accounts, registrations] = await Promise.all([getAccountOptions(), getRegistrationOptions()]);
        setAccountRows(accounts || []);
        setRegistrationRows(registrations || []);
        setAccountUserId(accounts?.[0]?.user_id || 0);
        setResetUserId(accounts?.[0]?.user_id || 0);
        setRegistrationUserId(registrations?.[0]?.id || 0);
      } catch {
        // Keep guest/admin flows available even if options fail.
      }
    };
    void loadOptions();
  }, []);

  const handleAdminSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
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

  const handleAccountSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsAccountLoading(true);
    try {
      const token = await accountLogin(accountUserId, password);
      localStorage.setItem('tracker_token', token);
      onAuth();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Account login failed');
    } finally {
      setIsAccountLoading(false);
    }
  };

  const handleRegister = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const result = await registerAccount(registrationUserId, registrationPassword, registrationConfirm);
      setMessage(result.status === 'pending' ? 'Registration submitted and pending approval.' : 'Registration submitted.');
      setRegistrationPassword('');
      setRegistrationConfirm('');
      setMode('account');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed');
    }
  };

  const handleForgot = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await requestPasswordReset(resetUserId);
      setMessage('If the account is eligible, a reset request has been submitted for admin approval.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Reset request failed');
    }
  };

  const handleResetComplete = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await completePasswordReset(resetToken, newPassword, newPasswordConfirm);
      setMessage('Password reset complete. You can now sign in.');
      setResetToken('');
      setNewPassword('');
      setNewPasswordConfirm('');
      setMode('account');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Reset completion failed');
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
        <h1>Discord Playtime Tracker</h1>
        <p>Private playtime analytics for your Discord guild.</p>

        <button type="button" className="primary-login-btn" onClick={handleGuestLogin} disabled={isGuestLoading || isAdminLoading}>
          {isGuestLoading ? 'Entering Dashboard...' : 'Continue as Guest'}
        </button>

        <div className="filters">
          <button type="button" className="secondary-login-btn" onClick={() => setMode('account')}>User Sign In</button>
          <button type="button" className="secondary-login-btn" onClick={() => setMode('admin')}>Admin Sign In</button>
          <button type="button" className="secondary-login-btn" onClick={() => setMode('register')}>Register</button>
          <button type="button" className="secondary-login-btn" onClick={() => setMode('forgot')}>Forgot Password</button>
          <button type="button" className="secondary-login-btn" onClick={() => setMode('reset')}>Reset With Token</button>
        </div>

        {mode === 'account' && (
          <form className="admin-login-form" onSubmit={handleAccountSubmit}>
            <label>Discord User</label>
            <select value={accountUserId} onChange={(e) => setAccountUserId(Number(e.target.value))}>
              {accountRows.map((row) => (
                <option key={row.user_id} value={row.user_id}>
                  {row.display_name} ({row.status})
                </option>
              ))}
            </select>
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="submit" disabled={isAccountLoading || isGuestLoading}>
              {isAccountLoading ? 'Signing In...' : 'Sign in'}
            </button>
          </form>
        )}

        {mode === 'admin' && (
          <form className="admin-login-form" onSubmit={handleAdminSubmit}>
            <label>Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} />
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="submit" disabled={isAdminLoading || isGuestLoading}>
              {isAdminLoading ? 'Signing In...' : 'Sign in as Admin'}
            </button>
          </form>
        )}

        {mode === 'register' && (
          <form className="admin-login-form" onSubmit={handleRegister}>
            <label>Discord User</label>
            <select value={registrationUserId} onChange={(e) => setRegistrationUserId(Number(e.target.value))}>
              {registrationRows.map((row) => (
                <option key={row.id} value={row.id}>{row.display_name}</option>
              ))}
            </select>
            <label>Password</label>
            <input type="password" value={registrationPassword} onChange={(e) => setRegistrationPassword(e.target.value)} />
            <label>Confirm Password</label>
            <input type="password" value={registrationConfirm} onChange={(e) => setRegistrationConfirm(e.target.value)} />
            <button type="submit" disabled={!registrationUserId}>Submit Registration</button>
          </form>
        )}

        {mode === 'forgot' && (
          <form className="admin-login-form" onSubmit={handleForgot}>
            <label>Account</label>
            <select value={resetUserId} onChange={(e) => setResetUserId(Number(e.target.value))}>
              {accountRows.map((row) => (
                <option key={row.user_id} value={row.user_id}>{row.display_name}</option>
              ))}
            </select>
            <button type="submit" disabled={!resetUserId}>Request Password Reset</button>
          </form>
        )}

        {mode === 'reset' && (
          <form className="admin-login-form" onSubmit={handleResetComplete}>
            <label>Reset Token</label>
            <input value={resetToken} onChange={(e) => setResetToken(e.target.value)} />
            <label>New Password</label>
            <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            <label>Confirm New Password</label>
            <input type="password" value={newPasswordConfirm} onChange={(e) => setNewPasswordConfirm(e.target.value)} />
            <button type="submit">Complete Reset</button>
          </form>
        )}

        {error && <div className="error-box">{error}</div>}
        {message && <div className="success-box">{message}</div>}
      </div>
    </div>
  );
}
