import { useEffect, useState } from 'react';
import { csvImport, csvPreview, listUsers, steamImport, steamPreview } from '../api/adminApi';
import { formatDuration } from '../utils/time';

interface SteamPreviewGame {
  appid: number;
  name: string;
  playtime_minutes: number;
}

interface SteamPreviewResponse {
  steam_id: string;
  profile_label: string;
  total_games: number;
  games: SteamPreviewGame[];
}

export default function ImportsPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [previewRows, setPreviewRows] = useState<any[]>([]);
  const [invalidRows, setInvalidRows] = useState<any[]>([]);
  const [csvImportMode, setCsvImportMode] = useState<'add' | 'overwrite'>('add');
  const [users, setUsers] = useState<any[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number>(0);
  const [steamProfile, setSteamProfile] = useState('');
  const [steamPreviewData, setSteamPreviewData] = useState<SteamPreviewResponse | null>(null);
  const [replacePreviousSteam, setReplacePreviousSteam] = useState(true);
  const [steamMaxGames, setSteamMaxGames] = useState(200);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const rows = await listUsers(guildId);
        setUsers(rows || []);
      } catch {
        setUsers([]);
      }
    })();
  }, [guildId]);

  const handlePreview = async (file: File) => {
    setMessage(null);
    setError(null);
    try {
      const data = await csvPreview(file);
      setPreviewRows(data.valid_rows || []);
      setInvalidRows(data.invalid_rows || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Preview failed');
    }
  };

  const handleImport = async () => {
    setMessage(null);
    setError(null);
    try {
      const result = await csvImport({
        guild_id: guildId,
        all_or_nothing: true,
        import_mode: csvImportMode,
        rows: previewRows,
      });
      setMessage(`Imported ${result.imported} rows.`);
      setPreviewRows([]);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Import failed');
    }
  };

  const handleSteamPreview = async () => {
    setMessage(null);
    setError(null);
    try {
      const data = await steamPreview({
        guild_id: guildId,
        user_id: selectedUserId,
        steam_profile: steamProfile,
      });
      setSteamPreviewData(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Steam preview failed');
    }
  };

  const handleSteamImport = async () => {
    setMessage(null);
    setError(null);
    try {
      const result = await steamImport({
        guild_id: guildId,
        user_id: selectedUserId,
        steam_profile: steamProfile,
        replace_previous: replacePreviousSteam,
        max_games: steamMaxGames,
      });
      setMessage(`Steam import complete: imported ${result.imported}, replaced ${result.replaced}.`);
      setSteamPreviewData(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Steam import failed');
    }
  };

  return (
    <div className="page-grid">
      <div className="panel">
        <h2>CSV Imports</h2>
        <p className="subtle">Dry-run preview first, then commit in all-or-nothing mode.</p>
        <div className="filters" style={{ marginBottom: 10 }}>
          <label htmlFor="csv-import-mode">Import mode</label>
          <select
            id="csv-import-mode"
            value={csvImportMode}
            onChange={(e) => setCsvImportMode(e.target.value as 'add' | 'overwrite')}
          >
            <option value="add">Add CSV hours to existing totals</option>
            <option value="overwrite">Overwrite total hours with CSV values</option>
          </select>
        </div>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handlePreview(file);
          }}
        />
      </div>

      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <div className="panel">
        <h3>Preview</h3>
        <div>Valid rows: {previewRows.length}</div>
        <div>Invalid rows: {invalidRows.length}</div>
        {invalidRows.length > 0 && (
          <ul>
            {invalidRows.map((row, idx) => (
              <li key={idx}>Row {row.row_number}: {row.message}</li>
            ))}
          </ul>
        )}
        <button disabled={previewRows.length === 0 || invalidRows.length > 0} onClick={handleImport}>Import Valid Rows</button>
      </div>

      <div className="panel">
        <h2>Steam Profile Import</h2>
        <p className="subtle">Import historical playtime from a Steam profile into manual imported records.</p>

        <div className="form-grid-3">
          <select value={selectedUserId} onChange={(e) => setSelectedUserId(Number(e.target.value))}>
            <option value={0}>Select Discord user</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>{u.display_name}</option>
            ))}
          </select>
          <input
            placeholder="Steam vanity/profile URL or SteamID64"
            value={steamProfile}
            onChange={(e) => setSteamProfile(e.target.value)}
          />
          <button disabled={!selectedUserId || !steamProfile.trim()} onClick={handleSteamPreview}>Preview Steam Games</button>
        </div>

        <div className="form-grid-3">
          <label>
            <input
              type="checkbox"
              checked={replacePreviousSteam}
              onChange={(e) => setReplacePreviousSteam(e.target.checked)}
            />{' '}
            Replace previous Steam imports for this Steam profile
          </label>
          <input
            type="number"
            min={1}
            max={500}
            value={steamMaxGames}
            onChange={(e) => setSteamMaxGames(Number(e.target.value) || 200)}
            placeholder="Max games"
          />
          <button disabled={!steamPreviewData} onClick={handleSteamImport}>Import From Steam</button>
        </div>

        {steamPreviewData && (
          <div className="table-wrap" style={{ marginTop: 12 }}>
            <div className="subtle">Steam ID: {steamPreviewData.steam_id} • Games with playtime: {steamPreviewData.total_games}</div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Game</th>
                  <th>App ID</th>
                  <th>Playtime</th>
                </tr>
              </thead>
              <tbody>
                {steamPreviewData.games.slice(0, 25).map((g) => (
                  <tr key={g.appid}>
                    <td>{g.name}</td>
                    <td>{g.appid}</td>
                    <td title={`${g.playtime_minutes} minutes`}>{formatDuration(g.playtime_minutes * 60)}</td>
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
