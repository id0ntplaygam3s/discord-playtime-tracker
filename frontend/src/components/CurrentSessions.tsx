import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

interface CurrentSessionsProps {
  sessions: any[];
  title?: string;
  compact?: boolean;
}

export default function CurrentSessions({ sessions, title = 'Currently Playing', compact = false }: CurrentSessionsProps) {
  return (
    <div className={`panel ${compact ? 'panel-compact' : ''}`}>
      <h3>{title}</h3>
      <div className="list-grid">
        {sessions.length === 0 && <div className="empty">No active sessions right now.</div>}
        {sessions.map((s) => (
          <div key={s.session_id} className="session-item">
            <div className="session-user">{s.user_name}</div>
            <div className="session-game">{s.game_name}</div>
            <div className="session-time">Started {dayjs(s.started_at).fromNow()}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
