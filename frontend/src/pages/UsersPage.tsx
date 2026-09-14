import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getTopUsers } from '../api/trackerApi';
import { deleteUser, getMe, listUsers } from '../api/adminApi';
import { formatDuration } from '../utils/time';

export default function UsersPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [rows, setRows] = useState<any[]>([]);
  const [totalsByUserId, setTotalsByUserId] = useState<Record<number, number>>({});
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [users, ranked, me] = await Promise.all([listUsers(guildId), getTopUsers(guildId, 'combined'), getMe()]);
        const totalMap: Record<number, number> = {};
        for (const row of ranked) {
          totalMap[row.id] = row.total_seconds;
        }
        setTotalsByUserId(totalMap);
        setRows(users || []);
        setIsAdmin(me.role === 'admin');
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load users');
      }
    };
    void load();
  }, [guildId]);

  const handleDelete = async (userId: number, displayName: string) => {
    const ok = window.confirm(`Delete user ${displayName} and all tracked sessions/manual entries/adjustments?`);
    if (!ok) return;

    setError(null);
    setMessage(null);
    try {
      await deleteUser(guildId, userId);
      setRows((prev) => prev.filter((row) => row.id !== userId));
      setTotalsByUserId((prev) => {
        const next = { ...prev };
        delete next[userId];
        return next;
      });
      setMessage(`Deleted ${displayName}.`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to delete user');
    }
  };

  return (
    <div className="panel">
      <h2>Users</h2>
      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Player</th>
              <th>Total Playtime</th>
              {isAdmin && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td><Link to={`/users/${row.id}`}>{row.display_name}</Link></td>
                <td>{formatDuration(totalsByUserId[row.id] || 0)}</td>
                {isAdmin && (
                  <td>
                    <button type="button" onClick={() => void handleDelete(row.id, row.display_name)}>Delete</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
