import { useEffect, useMemo, useState } from 'react';
import { getPermissions, getUserPermissionOverrides, listAdminUsers, setUserPermissionOverride, updateRolePermissions } from '../api/adminApi';

export default function PermissionsPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [permissions, setPermissions] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [roleMatrix, setRoleMatrix] = useState<Record<string, Record<string, boolean>>>({});
  const [accounts, setAccounts] = useState<any[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number>(0);
  const [overrides, setOverrides] = useState<Record<string, 'allow' | 'deny'>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const [permissionsData, userRows] = await Promise.all([getPermissions(), listAdminUsers(guildId)]);
      setPermissions(permissionsData.permissions || []);
      setRoles(permissionsData.roles || []);
      setRoleMatrix(permissionsData.role_permissions || {});
      setAccounts((userRows || []).filter((row: any) => row.account_id));
      setSelectedAccountId((current) => (userRows.some((row: any) => row.account_id === current) ? current : userRows.find((r: any) => r.account_id)?.account_id || 0));
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load permissions');
    }
  };

  const loadOverrides = async (accountId: number) => {
    if (!accountId) {
      setOverrides({});
      return;
    }
    try {
      const rows = await getUserPermissionOverrides(accountId);
      const map: Record<string, 'allow' | 'deny'> = {};
      for (const row of rows || []) {
        map[row.permission] = row.is_allowed ? 'allow' : 'deny';
      }
      setOverrides(map);
    } catch {
      setOverrides({});
    }
  };

  useEffect(() => {
    void load();
  }, [guildId]);

  useEffect(() => {
    void loadOverrides(selectedAccountId);
  }, [selectedAccountId]);

  const roleNames = useMemo(() => roles.map((r) => r.name), [roles]);

  const handleRoleToggle = async (roleName: 'guest' | 'user' | 'admin', permissionCode: string, next: boolean) => {
    try {
      const existing = roleMatrix[roleName] || {};
      await updateRolePermissions(roleName, { ...existing, [permissionCode]: next });
      setMessage('Role permissions updated.');
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update role permissions');
    }
  };

  const handleOverrideChange = async (permissionCode: string, mode: 'inherit' | 'allow' | 'deny') => {
    if (!selectedAccountId) return;
    try {
      await setUserPermissionOverride(selectedAccountId, permissionCode, mode);
      setMessage('User permission override updated.');
      await loadOverrides(selectedAccountId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update user override');
    }
  };

  return (
    <div className="page-grid">
      <div className="panel">
        <h2>Permissions</h2>
        <p className="subtle">Manage role defaults and per-user overrides.</p>
      </div>
      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <div className="panel">
        <h3>Role Permission Matrix</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Permission</th>
                {roleNames.map((roleName: string) => (
                  <th key={roleName}>{roleName}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {permissions.map((permission) => (
                <tr key={permission.code}>
                  <td>{permission.code}</td>
                  {roleNames.map((roleName: 'guest' | 'user' | 'admin') => {
                    const checked = !!roleMatrix[roleName]?.[permission.code];
                    return (
                      <td key={`${permission.code}-${roleName}`}>
                        <label>
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => void handleRoleToggle(roleName, permission.code, e.target.checked)}
                          />{' '}
                          {checked ? 'ON' : 'OFF'}
                        </label>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <h3>User Permission Overrides</h3>
        <label>Select account</label>
        <select value={selectedAccountId} onChange={(e) => setSelectedAccountId(Number(e.target.value))}>
          <option value={0}>Choose an account</option>
          {accounts.map((row) => (
            <option key={row.account_id} value={row.account_id}>
              {row.display_name} ({row.username})
            </option>
          ))}
        </select>

        {selectedAccountId > 0 && (
          <div className="table-wrap" style={{ marginTop: 10 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Permission</th>
                  <th>Override</th>
                </tr>
              </thead>
              <tbody>
                {permissions.map((permission) => {
                  const mode = overrides[permission.code] || 'inherit';
                  return (
                    <tr key={`override-${permission.code}`}>
                      <td>{permission.code}</td>
                      <td>
                        <select value={mode} onChange={(e) => void handleOverrideChange(permission.code, e.target.value as any)}>
                          <option value="inherit">Inherited</option>
                          <option value="allow">Enabled</option>
                          <option value="deny">Disabled</option>
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
