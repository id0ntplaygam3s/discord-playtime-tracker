import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import client from '../api/client';
import { formatDuration, formatSignedDuration } from '../utils/time';

export default function GameProfilePage() {
  const { gameId } = useParams();
  const id = Number(gameId || 0);
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [profile, setProfile] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      try {
        const [p, u, s] = await Promise.all([
          client.get(`/games/${id}`, { params: { guild_id: guildId } }),
          client.get(`/games/${id}/users`, { params: { guild_id: guildId } }),
          client.get(`/games/${id}/sessions`, { params: { guild_id: guildId, page: 1, page_size: 25 } }),
        ]);
        setProfile(p.data);
        setUsers(u.data);
        setSessions(s.data);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load game profile');
      }
    };
    void load();
  }, [id, guildId]);

  if (error) return <div className="error-box">{error}</div>;
  if (!profile) return <div className="panel">Loading game profile...</div>;

  return (
    <div className="page-grid">
      <div className="panel">
        <Link to="/games">Back to games</Link>
        <h2>{profile.display_name}</h2>
        <div className="status-grid">
          <div><strong>Combined:</strong> {formatDuration(profile.total_seconds)}</div>
          <div><strong>Automatic:</strong> {formatDuration(profile.automatic_seconds)}</div>
          <div><strong>Historical:</strong> {formatDuration(profile.historical_seconds)}</div>
          <div><strong>Adjustments:</strong> {formatSignedDuration(profile.adjustment_seconds)}</div>
          <div><strong>Unique players:</strong> {profile.unique_players}</div>
        </div>
      </div>

      <div className="panel">
        <h3>Top Players</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.name}</td>
                  <td>{formatDuration(u.total_seconds)}</td>
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
                <th>User</th>
                <th>Started</th>
                <th>Ended</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.session_id}>
                  <td>{s.user}</td>
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
