import { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import client from '../api/client';

dayjs.extend(relativeTime);

export default function ActivityPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [active, setActive] = useState<any[]>([]);
  const [recent, setRecent] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [activeRes, recentRes] = await Promise.all([
          client.get('/activity/active', { params: { guild_id: guildId } }),
          client.get('/activity/recent', { params: { guild_id: guildId, page: 1, page_size: 30 } }),
        ]);
        setActive(activeRes.data);
        setRecent(recentRes.data);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load activity');
      }
    };

    void load();
    const timer = window.setInterval(load, 30_000);
    return () => window.clearInterval(timer);
  }, [guildId]);

  return (
    <div className="page-grid">
      {error && <div className="error-box">{error}</div>}

      <div className="panel">
        <h2>Currently Playing</h2>
        {active.length === 0 && <div className="empty">Nobody is currently playing.</div>}
        {active.map((row) => (
          <div className="session-item" key={row.session_id}>
            <div className="session-user">{row.user_name}</div>
            <div className="session-game">{row.game_name}</div>
            <div className="session-time">Started {dayjs(row.started_at).fromNow()}</div>
          </div>
        ))}
      </div>

      <div className="panel">
        <h2>Recent Activity</h2>
        {recent.length === 0 && <div className="empty">No recent activity.</div>}
        <div className="list-grid">
          {recent.map((row, idx) => (
            <div className="session-item" key={idx}>
              <div className="session-user">
                {row.user_name} {row.event === 'started' ? 'started' : 'stopped'} playing {row.game_name}
              </div>
              <div className="session-time" title={dayjs(row.happened_at).format('YYYY-MM-DD HH:mm:ss')}>
                {dayjs(row.happened_at).fromNow()}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
