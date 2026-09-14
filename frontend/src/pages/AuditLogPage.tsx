import { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import { getAudit } from '../api/adminApi';
import { formatSignedDuration } from '../utils/time';

export default function AuditLogPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [rows, setRows] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getAudit(guildId, 1, 50);
        setRows(data);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load audit log');
      }
    };
    load();
  }, [guildId]);

  return (
    <div className="panel">
      <h2>Audit Log</h2>
      {error && <div className="error-box">{error}</div>}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Admin</th>
              <th>User</th>
              <th>Game</th>
              <th>Action</th>
              <th>Change</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx}>
                <td>{dayjs(row.date).format('YYYY-MM-DD HH:mm')}</td>
                <td>{row.administrator || '-'}</td>
                <td>{row.user || '-'}</td>
                <td>{row.game || '-'}</td>
                <td>{row.action}</td>
                <td>{typeof row.change_seconds === 'number' ? formatSignedDuration(row.change_seconds) : '-'}</td>
                <td>{row.reason || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
