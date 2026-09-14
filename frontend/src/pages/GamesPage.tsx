import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getGameUsers, getTopGames } from '../api/trackerApi';
import TopUsersChart from '../charts/TopUsersChart';
import { formatDuration } from '../utils/time';

export default function GamesPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [rows, setRows] = useState<any[]>([]);
  const [selectedGameId, setSelectedGameId] = useState<number>(0);
  const [selectedUsers, setSelectedUsers] = useState<any[]>([]);
  const [showValues, setShowValues] = useState(true);
  const [loadingBreakdown, setLoadingBreakdown] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedGame = useMemo(() => rows.find((r) => r.id === selectedGameId), [rows, selectedGameId]);

  useEffect(() => {
    const load = async () => {
      try {
        const games = await getTopGames(guildId, 'combined', 25);
        setRows(games);
        setSelectedGameId((current) => (games.some((g: any) => g.id === current) ? current : games[0]?.id || 0));
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load games');
      }
    };
    void load();
  }, [guildId]);

  useEffect(() => {
    let cancelled = false;
    const loadBreakdown = async () => {
      if (!selectedGameId) {
        setSelectedUsers([]);
        return;
      }
      setLoadingBreakdown(true);
      try {
        const users = await getGameUsers(guildId, selectedGameId);
        if (!cancelled) setSelectedUsers(users.slice(0, 12));
      } catch {
        if (!cancelled) setSelectedUsers([]);
      } finally {
        if (!cancelled) setLoadingBreakdown(false);
      }
    };

    void loadBreakdown();
    return () => {
      cancelled = true;
    };
  }, [guildId, selectedGameId]);

  return (
    <div className="page-grid">
      <div className="top-row">
        <h2>Games</h2>
        <div className="filters">
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input type="checkbox" checked={showValues} onChange={(e) => setShowValues(e.target.checked)} />
            Values
          </label>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      <section className="two-col">
        <div className="panel">
          <h3>Game Totals</h3>
          <div className="subtle" style={{ marginBottom: 10 }}>Click any row to view who contributes to that total.</div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Game</th>
                  <th>Total Playtime</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => setSelectedGameId(row.id)}
                    style={{ background: selectedGameId === row.id ? 'rgba(34, 211, 238, 0.12)' : 'transparent', cursor: 'pointer' }}
                  >
                    <td><Link to={`/games/${row.id}`}>{row.name}</Link></td>
                    <td>{formatDuration(row.total_seconds)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <TopUsersChart
            data={selectedUsers}
            title={selectedGame ? `Most Active In ${selectedGame.name}` : 'Select a game'}
            height={380}
            showValues={showValues}
          />
          {loadingBreakdown && <div className="subtle" style={{ marginTop: 8 }}>Loading player breakdown...</div>}
        </div>
      </section>
      </div>
  );
}
