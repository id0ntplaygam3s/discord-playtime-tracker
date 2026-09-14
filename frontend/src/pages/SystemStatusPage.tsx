import { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import { getSystemStatus } from '../api/adminApi';

export default function SystemStatusPage() {
  const [status, setStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getSystemStatus();
        setStatus(data);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load status');
      }
    };
    load();
    const interval = window.setInterval(load, 20_000);
    return () => window.clearInterval(interval);
  }, []);

  if (error) return <div className="error-box">{error}</div>;
  if (!status) return <div className="panel">Loading status...</div>;

  return (
    <div className="panel">
      <h2>System Status</h2>
      <div className="status-grid">
        <div><strong>Health:</strong> {status.status}</div>
        <div><strong>Discord:</strong> {status.discord_status}</div>
        <div><strong>Database:</strong> {status.database_status}</div>
        <div><strong>Bot uptime:</strong> {status.bot_uptime_seconds ?? 0}s</div>
        <div><strong>Active sessions:</strong> {status.active_sessions}</div>
        <div><strong>Last Discord event:</strong> {status.last_discord_event_at ? dayjs(status.last_discord_event_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</div>
        <div><strong>Last DB write:</strong> {status.last_database_write_at ? dayjs(status.last_database_write_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</div>
        <div><strong>Version:</strong> {status.app_version}</div>
      </div>
    </div>
  );
}
