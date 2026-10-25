import { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import { getSystemStatus } from '../api/adminApi';
import { useAppPreferences } from '../context/AppPreferencesContext';
import { formatDuration } from '../utils/time';
import { SystemStatus } from '../types';
import { SkeletonCard } from '../components/SkeletonLoader';

export default function SystemStatusPage() {
  const { autoRefreshEnabled } = useAppPreferences();
  const [status, setStatus] = useState<SystemStatus | null>(null);
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
    const interval = autoRefreshEnabled ? window.setInterval(load, 20_000) : null;
    return () => {
      if (interval) window.clearInterval(interval);
    };
  }, [autoRefreshEnabled]);

  if (error) return <div className="error-box">{error}</div>;
  if (!status) {
    return (
      <div className="panel">
        <h2>System Status</h2>
        <div style={{ display: 'grid', gap: 12 }}>
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  const statusColor = (s: string) => s === 'healthy' || s === 'online' ? '#4ade80' : s === 'degraded' ? '#facc15' : '#fb7185';

  return (
    <div className="panel">
      <h2>System Status</h2>
      <div className="status-grid">
        <div>
          <strong>Health:</strong>{' '}
          <span style={{ color: statusColor(status.status) }}>{status.status}</span>
        </div>
        <div>
          <strong>Discord:</strong>{' '}
          <span style={{ color: statusColor(status.discord_status) }}>{status.discord_status}</span>
        </div>
        <div>
          <strong>Database:</strong>{' '}
          <span style={{ color: statusColor(status.database_status) }}>{status.database_status}</span>
        </div>
        <div><strong>Bot uptime:</strong> {formatDuration(Number(status.bot_uptime_seconds || 0))}</div>
        <div><strong>Active sessions:</strong> {status.active_sessions}</div>
        <div><strong>Last Discord event:</strong> {status.last_discord_event_at ? dayjs(status.last_discord_event_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</div>
        <div><strong>Last DB write:</strong> {status.last_database_write_at ? dayjs(status.last_database_write_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</div>
        <div><strong>Version:</strong> {status.app_version}</div>
      </div>
    </div>
  );
}
