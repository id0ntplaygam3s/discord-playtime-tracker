import { useEffect, useMemo, useState } from 'react';
import TopGamesChart from '../charts/TopGamesChart';
import { getTopGames } from '../api/trackerApi';
import { RankedPlaytime, SourceFilter } from '../types';
import { formatDuration } from '../utils/time';

const sourceOptions: SourceFilter[] = ['combined', 'automatic', 'historical', 'adjustments'];

export default function GamesGraphPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [source, setSource] = useState<SourceFilter>('combined');
  const [rows, setRows] = useState<RankedPlaytime[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getTopGames(guildId, source, 30);
        if (!cancelled) setRows(data);
      } catch (err: any) {
        if (!cancelled) setError(err?.response?.data?.detail || 'Failed to load games graph');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [guildId, source]);

  const totalSeconds = useMemo(() => rows.reduce((sum, row) => sum + row.total_seconds, 0), [rows]);
  const topGame = rows[0];

  return (
    <div className="page-grid">
      <header className="panel graph-hero graph-hero-games">
        <div>
          <h2>Games (Graph)</h2>
          <p className="subtle">A large comparison view of game playtime across your guild.</p>
        </div>
        <div className="filters">
          <label>Data source</label>
          <select value={source} onChange={(e) => setSource(e.target.value as SourceFilter)}>
            {sourceOptions.map((option) => (
              <option value={option} key={option}>
                {option[0].toUpperCase() + option.slice(1)}
              </option>
            ))}
          </select>
        </div>
        <div className="graph-stats">
          <div>
            <span className="subtle">Games Compared</span>
            <strong>{rows.length}</strong>
          </div>
          <div>
            <span className="subtle">Combined Time</span>
            <strong>{formatDuration(totalSeconds)}</strong>
          </div>
          <div>
            <span className="subtle">Top Game</span>
            <strong>{topGame ? topGame.name : 'N/A'}</strong>
          </div>
        </div>
      </header>

      {loading && <div className="panel">Loading games graph...</div>}
      {error && <div className="error-box">{error}</div>}

      {!loading && !error && (
        <TopGamesChart
          data={rows}
          title="All Games Comparison"
          height={Math.max(460, Math.min(980, rows.length * 30 + 120))}
        />
      )}
    </div>
  );
}