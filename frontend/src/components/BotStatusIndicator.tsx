import { useEffect, useState, useCallback } from 'react';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import client from '../api/client';

dayjs.extend(relativeTime);

interface BotStatus {
  connected: boolean;
  bot_uptime_seconds: number | null;
  last_event_at: string | null;
}

export default function BotStatusIndicator() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await client.get('/api/health/bot-status');
      setStatus(data);
      setError(null);
    } catch {
      setError('Failed to load bot status');
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  if (error && !status) {
    return (
      <div className="bot-status-indicator" title="Status unavailable">
        <span className="bot-status-dot bot-status-unknown" />
        <span className="bot-status-text">Status unavailable</span>
      </div>
    );
  }

  const isConnected = status?.connected ?? false;
  const uptimeText = status?.bot_uptime_seconds
    ? formatUptime(status.bot_uptime_seconds)
    : null;
  const lastEventText = status?.last_event_at
    ? `Last event: ${dayjs(status.last_event_at).fromNow()}`
    : null;

  return (
    <div
      className="bot-status-indicator"
      title={lastEventText || 'Bot status'}
    >
      <span className={`bot-status-dot ${isConnected ? 'bot-status-online' : 'bot-status-offline'}`} />
      <span className="bot-status-text">{isConnected ? 'Bot online' : 'Bot offline'}</span>
      {uptimeText && <span className="bot-status-uptime">{uptimeText}</span>}
    </div>
  );
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}
