import { useEffect, useMemo, useState } from 'react';
import client from '../api/client';
import { formatDuration } from '../utils/time';
import { listUsers } from '../api/adminApi';

function normalizeError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item?.msg) return String(item.msg);
        return JSON.stringify(item);
      })
      .join('; ');
  }
  if (detail && typeof detail === 'object') {
    return JSON.stringify(detail);
  }
  return fallback;
}

function compareParams(guildId: number, userIds: number[]): URLSearchParams {
  const params = new URLSearchParams();
  params.set('guild_id', String(guildId));
  userIds.forEach((id) => params.append('user_ids', String(id)));
  return params;
}

export default function ComparePage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [users, setUsers] = useState<any[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [compareRows, setCompareRows] = useState<any[]>([]);
  const [sharedGames, setSharedGames] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadUsers = async () => {
      try {
        setError(null);
        const data = await listUsers(guildId);
        setUsers(data);
        setSelected(data.slice(0, 2).map((u: any) => u.id));
      } catch (err: any) {
        setError(normalizeError(err, 'Failed to load users'));
      }
    };
    void loadUsers();
  }, [guildId]);

  useEffect(() => {
    const runCompare = async () => {
      if (selected.length < 2) {
        setCompareRows([]);
        setSharedGames([]);
        return;
      }
      try {
        setError(null);
        const params = compareParams(guildId, selected);
        const [compareRes, sharedRes] = await Promise.all([
          client.get('/compare/users', { params }),
          client.get('/compare/shared-games', { params }),
        ]);
        setCompareRows(compareRes.data);
        setSharedGames(sharedRes.data);
      } catch (err: any) {
        setError(normalizeError(err, 'Failed to compare users'));
      }
    };
    void runCompare();
  }, [guildId, selected]);

  const toggle = (id: number) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(0, 6)));
  };

  const selectedNames = useMemo(() => users.filter((u) => selected.includes(u.id)).map((u) => u.display_name), [users, selected]);

  return (
    <div className="page-grid">
      {error && <div className="error-box">{error}</div>}

      <div className="panel">
        <h2>Compare Users</h2>
        <p className="subtle">Select 2-6 users and compare total/historical/automatic/adjustment playtime.</p>
        <div className="chip-wrap">
          {users.map((u) => (
            <button
              key={u.id}
              className={selected.includes(u.id) ? 'chip chip-active' : 'chip'}
              onClick={() => toggle(u.id)}
            >
              {u.display_name}
            </button>
          ))}
        </div>
        <div className="subtle" style={{ marginTop: 8 }}>
          Selected: {selectedNames.join(', ') || 'None'}
        </div>
      </div>

      <div className="panel">
        <h3>Totals</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Automatic</th>
                <th>Historical</th>
                <th>Adjustments</th>
                <th>Combined</th>
              </tr>
            </thead>
            <tbody>
              {compareRows.map((row) => (
                <tr key={row.user_id}>
                  <td>{row.display_name}</td>
                  <td>{formatDuration(row.automatic_seconds)}</td>
                  <td>{formatDuration(row.historical_seconds)}</td>
                  <td>{formatDuration(Math.abs(row.adjustment_seconds))}</td>
                  <td>{formatDuration(row.total_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <h3>Shared Games</h3>
        {sharedGames.length === 0 && <div className="empty">No shared games for the current selection.</div>}
        {sharedGames.map((game: any) => (
          <div key={game.game_id} className="session-item">
            <div className="session-user">{game.game_name}</div>
            {Object.values(game.players).map((player: any) => (
              <div className="session-time" key={player.user_id}>
                {player.display_name}: {formatDuration(player.total_seconds)}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
