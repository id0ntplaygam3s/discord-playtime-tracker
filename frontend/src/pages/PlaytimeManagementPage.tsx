import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  addAdjustment,
  addManualPlaytime,
  addOwnManualPlaytime,
  deleteManualPlaytime,
  deleteOwnManualPlaytime,
  getMe,
  listGames,
  listManualPlaytime,
  listOwnManualPlaytime,
  listUsers,
  setTotal,
} from '../api/adminApi';
import { formatDuration, formatSignedDuration } from '../utils/time';

type OptionRow = {
  id: number;
  display_name: string;
};

function normalizeRows(payload: any): OptionRow[] {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.results)) return payload.results;
  if (Array.isArray(payload?.rows)) return payload.rows;
  if (Array.isArray(payload?.data)) return payload.data;
  return [];
}

type ManualEntry = {
  row_key?: string;
  entry_kind?: 'manual' | 'adjustment';
  id: number;
  user_id: number;
  game_id: number;
  game_display_name?: string;
  canonical_game_id?: number;
  duration_seconds: number;
  source: 'historical' | 'imported' | 'correction' | 'adjustment';
  note?: string | null;
  created_at?: string;
  can_delete?: boolean;
};

export default function PlaytimeManagementPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [users, setUsers] = useState<OptionRow[]>([]);
  const [games, setGames] = useState<OptionRow[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingGames, setLoadingGames] = useState(false);
  const [loadingEntries, setLoadingEntries] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [entries, setEntries] = useState<ManualEntry[]>([]);
  const [canManageAll, setCanManageAll] = useState(false);
  const [currentTrackedUserId, setCurrentTrackedUserId] = useState<number | null>(null);
  const [initialized, setInitialized] = useState(false);

  const [userId, setUserId] = useState<number>(0);
  const [gameId, setGameId] = useState<number>(0);
  const [hours, setHours] = useState<number>(0);
  const [minutes, setMinutes] = useState<number>(0);
  const [source, setSource] = useState<'historical' | 'imported' | 'correction'>('historical');
  const [note, setNote] = useState('');
  const [useCustomGame, setUseCustomGame] = useState(false);
  const [customGameTitle, setCustomGameTitle] = useState('');

  const [adjHours, setAdjHours] = useState<number>(0);
  const [adjMinutes, setAdjMinutes] = useState<number>(0);
  const [adjSign, setAdjSign] = useState<number>(1);
  const [adjReason, setAdjReason] = useState('');

  const [targetHours, setTargetHours] = useState<number>(0);
  const [targetMinutes, setTargetMinutes] = useState<number>(0);
  const [targetReason, setTargetReason] = useState('');

  const upsertGameOption = (id: number, displayName?: string) => {
    if (!id) return;
    setGames((current) => {
      if (current.some((g) => g.id === id)) return current;
      return [{ id, display_name: displayName || `Game #${id}` }, ...current];
    });
  };

  const refreshOptions = async (manageAll: boolean = canManageAll) => {
    if (!manageAll) {
      setLoadingGames(true);
      try {
        const gamesResult = await listGames(guildId);
        const nextGames = normalizeRows(gamesResult);
        setGames((current) => {
          const currentOption = current.find((g) => g.id === gameId);
          if (currentOption && !nextGames.some((g) => g.id === currentOption.id)) {
            return [currentOption, ...nextGames];
          }
          return nextGames;
        });
        setGameId((current) => (current > 0 ? current : nextGames[0]?.id || 0));
      } catch (err: any) {
        setGames([]);
        setError(err?.response?.data?.detail || 'Failed to load games');
      } finally {
        setLoadingGames(false);
      }
      return;
    }

    setLoadingUsers(true);
    setLoadingGames(true);

    const [usersResult, gamesResult] = await Promise.allSettled([listUsers(guildId), listGames(guildId)]);

    if (usersResult.status === 'fulfilled') {
      const nextUsers = normalizeRows(usersResult.value);
      setUsers(nextUsers);
      setUserId((current) => (nextUsers.some((u) => u.id === current) ? current : nextUsers[0]?.id || 0));
    } else {
      setUsers([]);
      setError(usersResult.reason?.response?.data?.detail || 'Failed to load users');
    }

    if (gamesResult.status === 'fulfilled') {
      const nextGames = normalizeRows(gamesResult.value);
      setGames((current) => {
        const currentOption = current.find((g) => g.id === gameId);
        if (currentOption && !nextGames.some((g) => g.id === currentOption.id)) {
          return [currentOption, ...nextGames];
        }
        return nextGames;
      });
      setGameId((current) => (current > 0 ? current : nextGames[0]?.id || 0));
    } else {
      setGames([]);
      setError(gamesResult.reason?.response?.data?.detail || 'Failed to load games');
    }

    setLoadingUsers(false);
    setLoadingGames(false);
  };

  const refreshEntries = async (nextUserId?: number, nextGameId?: number, manageAll: boolean = canManageAll) => {
    setLoadingEntries(true);
    try {
      const rows = manageAll
        ? await listManualPlaytime(guildId, nextUserId || userId || undefined, nextGameId || gameId || undefined, 40)
        : await listOwnManualPlaytime(guildId, nextGameId || gameId || undefined, 40);
      setEntries(Array.isArray(rows) ? rows : []);
      setError((current) => (current === 'Failed to load manual entries' ? null : current));
    } catch (err: any) {
      setEntries([]);
      setError(err?.response?.data?.detail || 'Failed to load manual entries');
    } finally {
      setLoadingEntries(false);
    }
  };

  useEffect(() => {
    void (async () => {
      try {
        const me = await getMe();
        const permissionSet = new Set(me.permissions || []);
        const all = permissionSet.has('playtime.manage_all');
        setCanManageAll(all);
        setCurrentTrackedUserId(me.tracked_user_id || null);
        if (!all && me.tracked_user_id) {
          setUserId(me.tracked_user_id);
          setUsers([{ id: me.tracked_user_id, display_name: me.username }]);
        }
        await refreshOptions(all);
        await refreshEntries(me.tracked_user_id || undefined, undefined, all);
        setInitialized(true);
        return;
      } catch {
        setCanManageAll(false);
      }
      await refreshOptions();
      await refreshEntries();
      setInitialized(true);
    })();
  }, [guildId]);

  useEffect(() => {
    if (!initialized) return;
    void refreshEntries();
  }, [userId, gameId, canManageAll, initialized]);

  const selectedUser = useMemo(() => users.find((u) => u.id === Number(userId)), [users, userId]);
  const selectedGame = useMemo(() => games.find((g) => g.id === Number(gameId)), [games, gameId]);
  const gameLabel = useCustomGame ? customGameTitle.trim() : selectedGame?.display_name;
  const canUseSavedGame = gameId > 0;
  const hasUnsavedCustomTarget = useCustomGame
    && customGameTitle.trim().length > 0
    && (selectedGame?.display_name || '').trim().toLowerCase() !== customGameTitle.trim().toLowerCase();

  const handleManual = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    const customTitle = customGameTitle.trim();
    const targetUserId = canManageAll ? Number(userId) : Number(currentTrackedUserId || userId);
    if (!targetUserId) {
      setError('Select a user before saving manual playtime');
      return;
    }
    if (!useCustomGame && !gameId) {
      setError('Select a game before saving manual playtime');
      return;
    }
    if (useCustomGame && !customTitle) {
      setError('Enter a custom game title or uncheck override');
      return;
    }

    try {
      const payload = {
        guild_id: guildId,
        user_id: targetUserId,
        game_id: useCustomGame ? undefined : Number(gameId),
        use_custom_game_title: useCustomGame,
        custom_game_title: useCustomGame ? customTitle : undefined,
        hours: Number(hours),
        minutes: Number(minutes),
        source,
        note,
      };
      const result = canManageAll ? await addManualPlaytime(payload) : await addOwnManualPlaytime(payload);
      if (result?.game_id) {
        setGameId(Number(result.game_id));
      }
      setMessage('Manual playtime saved.');
      await refreshOptions();
      await refreshEntries(targetUserId, result?.game_id ? Number(result.game_id) : undefined, canManageAll);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save manual playtime');
    }
  };

  const handleAdjustment = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const customTitle = customGameTitle.trim();
    if (!userId || (!useCustomGame && !gameId) || (useCustomGame && !customTitle)) {
      setError('Select a user and game before saving an adjustment');
      return;
    }
    try {
      const result = await addAdjustment({
        guild_id: guildId,
        user_id: Number(userId),
        game_id: useCustomGame ? undefined : Number(gameId),
        use_custom_game_title: useCustomGame,
        custom_game_title: useCustomGame ? customTitle : undefined,
        hours: Number(adjHours),
        minutes: Number(adjMinutes),
        sign: Number(adjSign),
        reason: adjReason,
      });
      if (result?.game_id) {
        upsertGameOption(Number(result.game_id), result?.game_display_name);
        setGameId(Number(result.game_id));
      }
      setMessage('Adjustment saved.');
      await refreshOptions();
      await refreshEntries(Number(userId), result?.game_id ? Number(result.game_id) : undefined, canManageAll);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save adjustment');
    }
  };

  const handleSetTotal = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const customTitle = customGameTitle.trim();
    if (!userId || (!useCustomGame && !gameId) || (useCustomGame && !customTitle)) {
      setError('Select a user and game before applying an absolute total');
      return;
    }
    try {
      const desiredTotalSeconds = Number(targetHours) * 3600 + Number(targetMinutes) * 60;
      const result = await setTotal({
        guild_id: guildId,
        user_id: Number(userId),
        game_id: useCustomGame ? undefined : Number(gameId),
        use_custom_game_title: useCustomGame,
        custom_game_title: useCustomGame ? customTitle : undefined,
        desired_total_seconds: desiredTotalSeconds,
        reason: targetReason,
      });
      if (result?.game_id) {
        upsertGameOption(Number(result.game_id), result?.game_display_name);
        setGameId(Number(result.game_id));
      }
      setMessage('Absolute total correction applied via adjustment.');
      await refreshOptions();
      await refreshEntries(Number(userId), result?.game_id ? Number(result.game_id) : undefined, canManageAll);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to set absolute total');
    }
  };

  const handleDeleteEntry = async (entryId: number) => {
    setError(null);
    setMessage(null);
    try {
      if (canManageAll) {
        await deleteManualPlaytime(guildId, entryId);
      } else {
        await deleteOwnManualPlaytime(guildId, entryId);
      }
      setMessage('Manual entry deleted.');
      await refreshEntries();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to delete manual entry');
    }
  };

  return (
    <div className="page-grid">
      <div className="panel">
        <h2>Playtime Management</h2>
        <p className="subtle">Choose who and what to edit once, then apply manual time, adjustments, or absolute totals.</p>

        <div className="subtle" style={{ marginTop: 8 }}>
          Loading: {loadingUsers ? 'users...' : 'users ready'} / {loadingGames ? 'games...' : 'games ready'}
        </div>

        <div className="form-row">
          {canManageAll ? (
            <>
              <label>User</label>
              <select value={userId} onChange={(e) => setUserId(Number(e.target.value))}>
                {users.length === 0 && <option value={0}>No users found</option>}
                {users.map((u) => (
                  <option value={u.id} key={u.id}>
                    {u.display_name}
                  </option>
                ))}
              </select>
            </>
          ) : (
            <>
              <label>User</label>
              <input value={selectedUser?.display_name || 'Current user'} disabled />
            </>
          )}

          <label>Game</label>
          {!useCustomGame ? (
            <select value={gameId} onChange={(e) => setGameId(Number(e.target.value))}>
              {games.length === 0 && <option value={0}>No games found yet</option>}
              {games.map((g) => (
                <option value={g.id} key={g.id}>
                  {g.display_name}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={customGameTitle}
              onChange={(e) => setCustomGameTitle(e.target.value)}
              placeholder="Custom game title"
            />
          )}

          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={useCustomGame} onChange={(e) => setUseCustomGame(e.target.checked)} />
            Override with custom game title
          </label>

          <button type="button" onClick={() => void refreshOptions()}>
            Refresh Users/Games
          </button>
        </div>

        <div className="subtle" style={{ marginTop: 8 }}>
          Selected: {selectedUser?.display_name || '-'} / {gameLabel || '-'}
        </div>

        {!useCustomGame && games.length === 0 && (
          <div className="subtle" style={{ marginTop: 8 }}>
            No existing game records found. Enable custom title override to create one with your manual entry.
          </div>
        )}
      </div>

      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <form className="panel" onSubmit={handleManual}>
        <h3>Add Manual Historical/Imported Time</h3>
        <p className="subtle" style={{ marginTop: -8 }}>
          Use this for missing past time or imports that never came from live Discord sessions.
        </p>
        <div className="form-grid-3">
          <div style={{ display: 'grid', gap: 4 }}>
            <label htmlFor="manual-hours" className="subtle">Hours</label>
            <input id="manual-hours" type="number" min={0} value={hours} onChange={(e) => setHours(Number(e.target.value))} placeholder="0" />
          </div>
          <div style={{ display: 'grid', gap: 4 }}>
            <label htmlFor="manual-minutes" className="subtle">Minutes</label>
            <input id="manual-minutes" type="number" min={0} max={59} value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} placeholder="0" />
          </div>
          <select value={source} onChange={(e) => setSource(e.target.value as any)}>
            <option value="historical">Historical</option>
            <option value="imported">Imported</option>
            <option value="correction">Correction</option>
          </select>
        </div>
        <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note" />
        <button type="submit" disabled={!userId || (!useCustomGame && !gameId) || (useCustomGame && !customGameTitle.trim())}>
          Save Manual Playtime
        </button>
      </form>

      {canManageAll && (
        <form className="panel" onSubmit={handleAdjustment}>
          <h3>Add Adjustment</h3>
          <p className="subtle" style={{ marginTop: -8 }}>
            Use adjustments for quick corrections only. Positive adds time, negative subtracts time.
          </p>
          <div className="form-grid-4">
            <select value={adjSign} onChange={(e) => setAdjSign(Number(e.target.value))}>
              <option value={1}>+</option>
              <option value={-1}>-</option>
            </select>
            <div style={{ display: 'grid', gap: 4 }}>
              <label htmlFor="adjust-hours" className="subtle">Hours</label>
              <input id="adjust-hours" type="number" min={0} value={adjHours} onChange={(e) => setAdjHours(Number(e.target.value))} placeholder="0" />
            </div>
            <div style={{ display: 'grid', gap: 4 }}>
              <label htmlFor="adjust-minutes" className="subtle">Minutes</label>
              <input id="adjust-minutes" type="number" min={0} max={59} value={adjMinutes} onChange={(e) => setAdjMinutes(Number(e.target.value))} placeholder="0" />
            </div>
            <input value={adjReason} onChange={(e) => setAdjReason(e.target.value)} placeholder="Reason" />
          </div>
          <button type="submit" disabled={!userId || (!useCustomGame && !canUseSavedGame) || (useCustomGame && !customGameTitle.trim())}>Save Adjustment</button>
        </form>
      )}

      {canManageAll && (
        <form className="panel" onSubmit={handleSetTotal}>
          <h3>Set Absolute Total</h3>
          <p className="subtle" style={{ marginTop: -8 }}>
            Sets final total by calculating a hidden adjustment delta; this does not rewrite existing session history.
          </p>
          <div className="form-grid-3">
            <div style={{ display: 'grid', gap: 4 }}>
              <label htmlFor="target-hours" className="subtle">Target Hours</label>
              <input id="target-hours" type="number" min={0} value={targetHours} onChange={(e) => setTargetHours(Number(e.target.value))} placeholder="0" />
            </div>
            <div style={{ display: 'grid', gap: 4 }}>
              <label htmlFor="target-minutes" className="subtle">Target Minutes</label>
              <input id="target-minutes" type="number" min={0} max={59} value={targetMinutes} onChange={(e) => setTargetMinutes(Number(e.target.value))} placeholder="0" />
            </div>
            <input value={targetReason} onChange={(e) => setTargetReason(e.target.value)} placeholder="Reason" />
          </div>
          <button type="submit" disabled={!userId || (!useCustomGame && !canUseSavedGame) || (useCustomGame && !customGameTitle.trim())}>Apply Absolute Total</button>
        </form>
      )}

      <div className="panel">
        <h3>Recent Entries</h3>
        <div className="subtle" style={{ marginBottom: 8 }}>
          Showing latest manual entries and adjustments for the selected user/game.
        </div>
        {hasUnsavedCustomTarget && (
          <div className="subtle" style={{ marginBottom: 8 }}>
            Custom title mode is active. Save one manual entry first, then this table will follow that custom game.
          </div>
        )}
        {!hasUnsavedCustomTarget && loadingEntries && <div className="subtle">Loading entries...</div>}
        {!hasUnsavedCustomTarget && !loadingEntries && entries.length === 0 && <div className="empty">No entries found for this selection.</div>}
        {!hasUnsavedCustomTarget && !loadingEntries && entries.length > 0 && (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Game</th>
                  <th>Source</th>
                  <th>Duration</th>
                  <th>Note</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.row_key || `${entry.entry_kind || 'manual'}-${entry.id}`}>
                    <td>{entry.created_at ? new Date(entry.created_at).toLocaleString() : '-'}</td>
                    <td>{entry.game_display_name || `#${entry.game_id}`}</td>
                    <td>{entry.source}</td>
                    <td>{entry.source === 'adjustment' ? formatSignedDuration(entry.duration_seconds) : formatDuration(entry.duration_seconds)}</td>
                    <td>{entry.note || '-'}</td>
                    <td>
                      {entry.can_delete !== false ? (
                        <button type="button" onClick={() => void handleDeleteEntry(entry.id)}>Delete</button>
                      ) : (
                        <span className="subtle">-</span>
                      )}
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
