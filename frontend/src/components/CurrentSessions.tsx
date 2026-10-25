import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { ActiveSession } from '../types';

dayjs.extend(relativeTime);

interface CurrentSessionsProps {
  sessions: ActiveSession[];
  title?: string;
  compact?: boolean;
}

export default function CurrentSessions({ sessions, title = 'Currently Playing', compact = false }: CurrentSessionsProps) {
  return (
    <div className={`panel ${compact ? 'panel-compact' : ''}`}>
      <h3>{title}</h3>
      <div className="list-grid">
        {sessions.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">🎮</div>
            <div className="empty-state-title">No active sessions</div>
            <div className="empty-state-desc">No one is currently playing tracked games.</div>
          </div>
        )}
        {sessions.map((s) => (
          <div key={s.session_id} className="session-item">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {s.avatar_url && (
                <img src={s.avatar_url} alt="" className="avatar" loading="lazy" />
              )}
              <div className="session-user">{s.user_name}</div>
            </div>
            <div className="session-game">{s.game_name}</div>
            <div className="session-time">Started {dayjs(s.started_at).fromNow()}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
