import { FormEvent, useEffect, useState } from 'react';
import { adminResetPassword, listAdminUsers, setAccountRole, setAccountStatus, unlockAccount } from '../api/adminApi';

export default function AccountsPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [rows, setRows] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [targetAccountId, setTargetAccountId] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const data = await listAdminUsers(guildId);
      setRows(data || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load accounts');
    }
  };

  useEffect(() => {
    void load();
  }, [guildId]);

  const visibleRows = rows.filter((row) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return (`${row.username} ${row.display_name}`.toLowerCase().includes(q));
  });

  const handleRoleChange = async (accountId: number, role: 'guest' | 'user' | 'admin') => {
    try {
      await setAccountRole(accountId, role);
      setMessage('Role updated.');
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleStatusChange = async (accountId: number, status: 'pending' | 'active' | 'locked' | 'disabled') => {
    try {
      await setAccountStatus(accountId, status);
      setMessage('Status updated.');
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update status');
    }
  };

  const handleUnlock = async (accountId: number) => {
    try {
      await unlockAccount(accountId);
      setMessage('Account unlocked.');
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to unlock account');
    }
  };

  const handleResetPassword = async (e: FormEvent) => {
    e.preventDefault();
    if (!targetAccountId) {
      setError('Select an account first.');
      return;
    }
    try {
      await adminResetPassword(targetAccountId, newPassword);
      setMessage('Password reset completed.');
      setNewPassword('');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to reset password');
    }
  };

  return (
    <div className="page-grid">
      <div className="panel">
        <h2>Accounts</h2>
        <p className="subtle">Manage account roles, status, and administrator password reset actions.</p>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search users" />
      </div>
      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <div className="panel">
        <h3>User Accounts</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={row.user_id}>
                  <td>{row.display_name} ({row.username})</td>
                  <td>
                    {row.account_id ? (
                      <select value={row.role || 'user'} onChange={(e) => void handleRoleChange(row.account_id, e.target.value as any)}>
                        <option value="guest">Guest</option>
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
                      </select>
                    ) : 'No account'}
                  </td>
                  <td>
                    {row.account_id ? (
                      <select value={row.account_status || 'pending'} onChange={(e) => void handleStatusChange(row.account_id, e.target.value as any)}>
                        <option value="pending">Pending</option>
                        <option value="active">Active</option>
                        <option value="locked">Locked</option>
                        <option value="disabled">Disabled</option>
                      </select>
                    ) : '-'}
                  </td>
                  <td>{row.last_login_at ? new Date(row.last_login_at).toLocaleString() : '-'}</td>
                  <td>
                    {row.account_id ? (
                      <>
                        <button type="button" onClick={() => void handleUnlock(row.account_id)}>Unlock</button>{' '}
                        <button type="button" onClick={() => setTargetAccountId(row.account_id)}>Set Reset Target</button>
                      </>
                    ) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <form className="panel" onSubmit={handleResetPassword}>
        <h3>Administrator Reset Password</h3>
        <p className="subtle">Target account ID: {targetAccountId || 'none selected'}</p>
        <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="New password" />
        <button type="submit" disabled={!targetAccountId || newPassword.length < 8}>Reset Password</button>
      </form>
    </div>
  );
}
