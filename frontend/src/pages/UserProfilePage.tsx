import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import client from '../api/client';
import { formatDuration, formatSignedDuration } from '../utils/time';

export default function UserProfilePage() {
  const { userId } = useParams();
  const id = Number(userId || 0);
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [profile, setProfile] = useState<any>(null);
  const [games, setGames] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      try {
        const [p, g, s] = await Promise.all([
          client.get(`/users/${id}`, { params: { guild_id: guildId } }),
          client.get(`/users/${id}/games`, { params: { guild_id: guildId } }),
          client.get(`/users/${id}/sessions`, { params: { guild_id: guildId, page: 1, page_size: 25 } }),
        ]);
        setProfile(p.data);
        setGames(g.data);
        setSessions(s.data);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load user profile');
      }
    };
    void load();
  }, [id, guildId]);

  if (error) return <div className="error-box">{error}</div>;
  if (!profile) return <div className="panel">Loading user profile...</div>;

  return (
    <div className="page-grid">
      <div className="panel">
        <Link to="/users">Back to users</Link>
        <h2>{profile.display_name}</h2>
        <div className="status-grid">
          <div><strong>Combined:</strong> {formatDuration(profile.total_seconds)}</div>
          <div><strong>Automatic:</strong> {formatDuration(profile.automatic_seconds)}</div>
          <div><strong>Historical:</strong> {formatDuration(profile.historical_seconds)}</div>
          <div><strong>Adjustments:</strong> {formatSignedDuration(profile.adjustment_seconds)}</div>
        </div>
      </div>

      <div className="panel">
        <h3>Playtime By Game</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Game</th>
                <th>Total Playtime</th>
              </tr>
            </thead>
            <tbody>
              {games.map((g) => (
                <tr key={g.id}>
                  <td>{g.name}</td>
                  <td>{formatDuration(g.total_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <h3>Recent Sessions</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Game</th>
                <th>Started</th>
                <th>Ended</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.session_id}>
                  <td>{s.game}</td>
                  <td>{new Date(s.started_at).toLocaleString()}</td>
                  <td>{s.ended_at ? new Date(s.ended_at).toLocaleString() : 'Active'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
