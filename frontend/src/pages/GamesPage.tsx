import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getTopGames } from '../api/trackerApi';
import { formatDuration } from '../utils/time';

export default function GamesPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [rows, setRows] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setRows(await getTopGames(guildId, 'combined'));
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load games');
      }
    };
    void load();
  }, [guildId]);

  return (
    <div className="panel">
      <h2>Games</h2>
      {error && <div className="error-box">{error}</div>}
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
              <tr key={row.id}>
                <td><Link to={`/games/${row.id}`}>{row.name}</Link></td>
                <td>{formatDuration(row.total_seconds)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
