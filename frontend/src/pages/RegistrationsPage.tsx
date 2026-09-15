import { useEffect, useState } from 'react';
import { approvePasswordResetRequest, approveRegistration, listPasswordResetRequests, listRegistrations, rejectRegistration } from '../api/adminApi';

export default function RegistrationsPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [resets, setResets] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const [registrationRows, resetRows] = await Promise.all([listRegistrations(), listPasswordResetRequests()]);
      setRows(Array.isArray(registrationRows) ? registrationRows : []);
      setResets(Array.isArray(resetRows) ? resetRows : []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load registration data');
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleApprove = async (accountId: number) => {
    try {
      await approveRegistration(accountId);
      setMessage('Registration approved.');
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Approval failed');
    }
  };

  const handleReject = async (accountId: number) => {
    try {
      await rejectRegistration(accountId);
      setMessage('Registration rejected.');
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Rejection failed');
    }
  };

  const handleApproveReset = async (requestId: number) => {
    try {
      const result = await approvePasswordResetRequest(requestId);
      const token = result?.reset_token ? ` Token: ${result.reset_token}` : '';
      setMessage(`Password reset approved.${token}`);
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Reset approval failed');
    }
  };

  return (
    <div className="page-grid">
      <div className="panel">
        <h2>Registrations</h2>
        <p className="subtle">Approve or reject pending user registration requests.</p>
      </div>
      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <div className="panel">
        <h3>Pending Registrations</h3>
        {rows.length === 0 ? (
          <div className="empty">No pending registrations.</div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Discord Username</th>
                  <th>Display Name</th>
                  <th>Requested</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.account_id}>
                    <td>{row.username}</td>
                    <td>{row.display_name}</td>
                    <td>{row.requested_at ? new Date(row.requested_at).toLocaleString() : '-'}</td>
                    <td>{row.status}</td>
                    <td>
                      <button type="button" onClick={() => void handleApprove(row.account_id)}>Approve</button>{' '}
                      <button type="button" onClick={() => void handleReject(row.account_id)}>Reject</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="panel">
        <h3>Password Reset Requests</h3>
        {resets.length === 0 ? (
          <div className="empty">No pending password reset requests.</div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Display Name</th>
                  <th>Requested</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {resets.map((row) => (
                  <tr key={row.request_id}>
                    <td>{row.username}</td>
                    <td>{row.display_name}</td>
                    <td>{row.created_at ? new Date(row.created_at).toLocaleString() : '-'}</td>
                    <td>
                      <button type="button" onClick={() => void handleApproveReset(row.request_id)}>Approve Reset</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
