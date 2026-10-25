import { useEffect, useMemo, useState } from 'react';
import client from '../api/client';
import { formatDuration } from '../utils/time';
import { listUsers } from '../api/adminApi';
import { SearchInput, useSearch } from '../components/SearchInput';

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

  const { query, setQuery, filtered: filteredUsers } = useSearch(users, ['display_name', 'username']);

  useEffect(() => {
    const loadUsers = async () => {
      try {
        setError(null);
        const data = await listUsers(guildId);
        setUsers(data);
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
    setSelected((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  const selectAll = () => {
    setSelected(users.map((u) => u.id));
  };

  const clearSelected = () => {
    setSelected([]);
  };

  const selectedNames = useMemo(() => users.filter((u) => selected.includes(u.id)).map((u) => u.display_name), [users, selected]);

  return (
    <div className="page-grid">
      {error && <div className="error-box">{error}</div>}

      <div className="panel">
        <h2>Compare Users</h2>
        <p className="subtle">Select 2-6 users and compare combined totals only.</p>
        <div className="filters" style={{ marginBottom: 10, flexDirection: 'column', alignItems: 'stretch', gap: 10 }}>
          <SearchInput value={query} onChange={setQuery} placeholder="Search users..." ariaLabel="Search users" />
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={selectAll}>Select All (Max 6)</button>
            <button type="button" onClick={clearSelected}>Clear</button>
          </div>
        </div>
        <div className="chip-wrap">
          {filteredUsers.map((u) => (
            <button
              key={u.id}
              className={selected.includes(u.id) ? 'chip chip-active' : 'chip'}
              onClick={() => toggle(u.id)}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              {u.avatar_url && (
                <img src={u.avatar_url} alt="" className="avatar avatar-sm" loading="lazy" />
              )}
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
                <th>Total Playtime</th>
              </tr>
            </thead>
            <tbody>
              {compareRows.map((row) => (
                <tr key={row.user_id}>
                  <td>{row.display_name}</td>
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
