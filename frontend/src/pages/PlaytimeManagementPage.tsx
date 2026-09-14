import { FormEvent, useEffect, useMemo, useState } from 'react';
import { addAdjustment, addManualPlaytime, listGames, listUsers, setTotal } from '../api/adminApi';

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

export default function PlaytimeManagementPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [users, setUsers] = useState<OptionRow[]>([]);
  const [games, setGames] = useState<OptionRow[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingGames, setLoadingGames] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const refreshOptions = async () => {
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
      setGames(nextGames);
      setGameId((current) => (nextGames.some((g) => g.id === current) ? current : nextGames[0]?.id || 0));
    } else {
      setGames([]);
      setError(gamesResult.reason?.response?.data?.detail || 'Failed to load games');
    }

    setLoadingUsers(false);
    setLoadingGames(false);
  };

  useEffect(() => {
    void refreshOptions();
  }, [guildId]);

  const selectedUser = useMemo(() => users.find((u) => u.id === Number(userId)), [users, userId]);
  const selectedGame = useMemo(() => games.find((g) => g.id === Number(gameId)), [games, gameId]);
  const gameLabel = useCustomGame ? customGameTitle.trim() : selectedGame?.display_name;
  const canUseSavedGame = gameId > 0;

  const handleManual = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    const customTitle = customGameTitle.trim();
    if (!userId) {
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
      await addManualPlaytime({
        guild_id: guildId,
        user_id: Number(userId),
        game_id: useCustomGame ? undefined : Number(gameId),
        custom_game_title: useCustomGame ? customTitle : undefined,
        hours: Number(hours),
        minutes: Number(minutes),
        source,
        note,
      });
      setMessage('Manual playtime saved.');
      await refreshOptions();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save manual playtime');
    }
  };

  const handleAdjustment = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (!userId || !gameId) {
      setError('Select a user and game before saving an adjustment');
      return;
    }
    try {
      await addAdjustment({
        guild_id: guildId,
        user_id: Number(userId),
        game_id: Number(gameId),
        hours: Number(adjHours),
        minutes: Number(adjMinutes),
        sign: Number(adjSign),
        reason: adjReason,
      });
      setMessage('Adjustment saved.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save adjustment');
    }
  };

  const handleSetTotal = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (!userId || !gameId) {
      setError('Select a user and game before applying an absolute total');
      return;
    }
    try {
      const desiredTotalSeconds = Number(targetHours) * 3600 + Number(targetMinutes) * 60;
      await setTotal({
        guild_id: guildId,
        user_id: Number(userId),
        game_id: Number(gameId),
        desired_total_seconds: desiredTotalSeconds,
        reason: targetReason,
      });
      setMessage('Absolute total correction applied via adjustment.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to set absolute total');
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
          <label>User</label>
          <select value={userId} onChange={(e) => setUserId(Number(e.target.value))}>
            {users.length === 0 && <option value={0}>No users found</option>}
            {users.map((u) => (
              <option value={u.id} key={u.id}>
                {u.display_name}
              </option>
            ))}
          </select>

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
        <div className="form-grid-3">
          <input type="number" min={0} value={hours} onChange={(e) => setHours(Number(e.target.value))} placeholder="Hours" />
          <input type="number" min={0} max={59} value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} placeholder="Minutes" />
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

      <form className="panel" onSubmit={handleAdjustment}>
        <h3>Add Adjustment</h3>
        <div className="form-grid-4">
          <select value={adjSign} onChange={(e) => setAdjSign(Number(e.target.value))}>
            <option value={1}>+</option>
            <option value={-1}>-</option>
          </select>
          <input type="number" min={0} value={adjHours} onChange={(e) => setAdjHours(Number(e.target.value))} placeholder="Hours" />
          <input type="number" min={0} max={59} value={adjMinutes} onChange={(e) => setAdjMinutes(Number(e.target.value))} placeholder="Minutes" />
          <input value={adjReason} onChange={(e) => setAdjReason(e.target.value)} placeholder="Reason" />
        </div>
        <button type="submit" disabled={!userId || !canUseSavedGame}>Save Adjustment</button>
      </form>

      <form className="panel" onSubmit={handleSetTotal}>
        <h3>Set Absolute Total</h3>
        <div className="form-grid-3">
          <input type="number" min={0} value={targetHours} onChange={(e) => setTargetHours(Number(e.target.value))} placeholder="Target hours" />
          <input type="number" min={0} max={59} value={targetMinutes} onChange={(e) => setTargetMinutes(Number(e.target.value))} placeholder="Target minutes" />
          <input value={targetReason} onChange={(e) => setTargetReason(e.target.value)} placeholder="Reason" />
        </div>
        <button type="submit" disabled={!userId || !canUseSavedGame}>Apply Absolute Total</button>
      </form>
    </div>
  );
}
