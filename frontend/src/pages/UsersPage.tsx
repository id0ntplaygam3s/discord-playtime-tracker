import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getTopUsers } from '../api/trackerApi';
import { deleteUser, getMe, listUsers } from '../api/adminApi';
import { SearchInput, useSearch } from '../components/SearchInput';
import { SkeletonTable } from '../components/SkeletonLoader';
import { formatDuration } from '../utils/time';

export default function UsersPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [rows, setRows] = useState<any[]>([]);
  const [totalsByUserId, setTotalsByUserId] = useState<Record<number, number>>({});
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const { query, setQuery, filtered } = useSearch(rows, ['display_name', 'username']);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
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
      } finally {
        setLoading(false);
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

  if (loading) {
    return (
      <div className="panel">
        <h2>Users</h2>
        <SkeletonTable rows={5} />
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="top-row" style={{ marginBottom: 16 }}>
        <h2>Users</h2>
        <SearchInput value={query} onChange={setQuery} placeholder="Search users..." ariaLabel="Search users" />
      </div>
      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}
      {filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">👥</div>
          <div className="empty-state-title">No users found</div>
          <div className="empty-state-desc">
            {query ? 'No users match your search.' : 'No users have been tracked yet.'}
          </div>
        </div>
      ) : (
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
              {filtered.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      {row.avatar_url && (
                        <img
                          src={row.avatar_url}
                          alt=""
                          className="avatar"
                          loading="lazy"
                        />
                      )}
                      <Link to={`/users/${row.id}`}>{row.display_name}</Link>
                    </div>
                  </td>
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
      )}
    </div>
  );
}
