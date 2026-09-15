import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getGameUsers, getTopGames } from '../api/trackerApi';
import DateRangeTabs from '../components/DateRangeTabs';
import TopUsersChart from '../charts/TopUsersChart';
import { DateRangeKey } from '../types';
import { selectedGameRangeOptions } from '../utils/dateRanges';
import { formatDuration } from '../utils/time';

export default function GamesPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const ALL_ROWS_LIMIT = 5000;
  const [rowLimit, setRowLimit] = useState<number>(30);
  const [rows, setRows] = useState<any[]>([]);
  const [selectedGameId, setSelectedGameId] = useState<number>(0);
  const [selectedUsers, setSelectedUsers] = useState<any[]>([]);
  const [selectedGameRange, setSelectedGameRange] = useState<DateRangeKey>('all');
  const [selectedFrom, setSelectedFrom] = useState('');
  const [selectedTo, setSelectedTo] = useState('');
  const [showValues, setShowValues] = useState(true);
  const [loadingBreakdown, setLoadingBreakdown] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedGame = useMemo(() => rows.find((r) => r.id === selectedGameId), [rows, selectedGameId]);

  useEffect(() => {
    const load = async () => {
      try {
        const games = await getTopGames(guildId, 'combined', rowLimit <= 0 ? ALL_ROWS_LIMIT : rowLimit);
        setRows(games);
        setSelectedGameId((current) => (games.some((g: any) => g.id === current) ? current : games[0]?.id || 0));
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load games');
      }
    };
    void load();
  }, [guildId, rowLimit]);

  useEffect(() => {
    let cancelled = false;
    const loadBreakdown = async () => {
      if (!selectedGameId) {
        setSelectedUsers([]);
        return;
      }
      setLoadingBreakdown(true);
      try {
        const users = await getGameUsers(
          guildId,
          selectedGameId,
          selectedGameRange,
          selectedGameRange === 'custom'
            ? {
                from: selectedFrom ? new Date(`${selectedFrom}T00:00:00Z`).toISOString() : undefined,
                to: selectedTo ? new Date(`${selectedTo}T23:59:59Z`).toISOString() : undefined,
              }
            : undefined,
        );
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
  }, [guildId, selectedGameId, selectedGameRange, selectedFrom, selectedTo]);

  return (
    <div className="page-grid">
      <div className="top-row">
        <h2>Games</h2>
        <div className="filters">
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            Rows
            <select value={String(rowLimit)} onChange={(e) => setRowLimit(Number(e.target.value))}>
              <option value="30">30</option>
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="250">250</option>
              <option value="0">All</option>
            </select>
          </label>
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
          <div className="subtle" style={{ marginBottom: 10 }}>
            Showing {rows.length} games. Click any row to view who contributes to that total.
          </div>
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

        <div className="panel">
          <h3>{selectedGame ? `Most Active In ${selectedGame.name}` : 'Select a game'}</h3>
          <DateRangeTabs
            options={selectedGameRangeOptions}
            value={selectedGameRange}
            onChange={setSelectedGameRange}
            ariaLabel="Game page activity range"
          />
          {selectedGameRange === 'custom' && (
            <div className="form-grid-3" style={{ marginBottom: 8 }}>
              <input type="date" value={selectedFrom} onChange={(e) => setSelectedFrom(e.target.value)} />
              <input type="date" value={selectedTo} onChange={(e) => setSelectedTo(e.target.value)} />
              <div className="subtle">Custom range applies to this game only.</div>
            </div>
          )}
          <TopUsersChart
            data={selectedUsers}
            title=""
            height={320}
            showValues={showValues}
            frameless
          />
          {loadingBreakdown && <div className="subtle" style={{ marginTop: 8 }}>Loading player breakdown...</div>}
        </div>
      </section>
      </div>
  );
}
