import { FormEvent, useEffect, useState } from 'react';
import { getRuntimeSettings, updateRuntimeSettings } from '../api/adminApi';

const editableKeys = [
  'application_name',
  'guest_access_enabled',
  'registration_enabled',
  'registration_requires_approval',
  'default_registration_role',
  'auth_min_password_length',
  'auth_max_failed_login_attempts',
  'auth_lock_minutes',
  'dashboard_default_range',
  'dashboard_selected_game_default_range',
  'users_can_create_own_manual',
  'users_can_edit_own_manual',
  'users_can_delete_own_manual',
];

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, any>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const data = await getRuntimeSettings();
      setSettings(data || {});
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load settings');
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await updateRuntimeSettings(settings);
      setMessage('Settings updated.');
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save settings');
    }
  };

  return (
    <form className="page-grid" onSubmit={handleSubmit}>
      <div className="panel">
        <h2>Settings</h2>
        <p className="subtle">Runtime settings stored in PostgreSQL. Secrets remain environment-managed.</p>
      </div>
      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <div className="panel">
        <h3>General</h3>
        <div className="form-row" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          {editableKeys.map((key) => {
            const value = settings[key];
            const isBoolean = typeof value === 'boolean';
            const isNumber = typeof value === 'number';
            return (
              <label key={key} style={{ display: 'grid', gap: 6 }}>
                <span>{key}</span>
                {isBoolean ? (
                  <input
                    type="checkbox"
                    checked={Boolean(value)}
                    onChange={(e) => setSettings((prev) => ({ ...prev, [key]: e.target.checked }))}
                  />
                ) : isNumber ? (
                  <input
                    type="number"
                    value={Number(value || 0)}
                    onChange={(e) => setSettings((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                  />
                ) : (
                  <input
                    value={String(value ?? '')}
                    onChange={(e) => setSettings((prev) => ({ ...prev, [key]: e.target.value }))}
                  />
                )}
              </label>
            );
          })}
        </div>
        <button type="submit">Save Settings</button>
      </div>
    </form>
  );
}
