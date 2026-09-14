import { FormEvent, useEffect, useMemo, useState } from 'react';
import { addAdjustment, addManualPlaytime, listGames, listUsers, setTotal } from '../api/adminApi';

export default function PlaytimeManagementPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [users, setUsers] = useState<any[]>([]);
  const [games, setGames] = useState<any[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [userId, setUserId] = useState<number>(0);
  const [gameId, setGameId] = useState<number>(0);
  const [hours, setHours] = useState<number>(0);
  const [minutes, setMinutes] = useState<number>(0);
  const [source, setSource] = useState<'historical' | 'imported' | 'correction'>('historical');
  const [note, setNote] = useState('');

  const [adjHours, setAdjHours] = useState<number>(0);
  const [adjMinutes, setAdjMinutes] = useState<number>(0);
  const [adjSign, setAdjSign] = useState<number>(1);
  const [adjReason, setAdjReason] = useState('');

  const [targetHours, setTargetHours] = useState<number>(0);
  const [targetMinutes, setTargetMinutes] = useState<number>(0);
  const [targetReason, setTargetReason] = useState('');

  useEffect(() => {
    const load = async () => {
      const [u, g] = await Promise.all([listUsers(guildId), listGames(guildId)]);
      setUsers(u);
      setGames(g);
      if (u.length > 0) setUserId(u[0].id);
      if (g.length > 0) setGameId(g[0].id);
    };
    load();
  }, [guildId]);

  const selectedUser = useMemo(() => users.find((u) => u.id === Number(userId)), [users, userId]);
  const selectedGame = useMemo(() => games.find((g) => g.id === Number(gameId)), [games, gameId]);

  const handleManual = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await addManualPlaytime({
        guild_id: guildId,
        user_id: Number(userId),
        game_id: Number(gameId),
        hours: Number(hours),
        minutes: Number(minutes),
        source,
        note,
      });
      setMessage('Manual playtime saved.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save manual playtime');
    }
  };

  const handleAdjustment = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
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
        <p className="subtle">Add historical records, corrections, and absolute total adjustments without faking sessions.</p>

        <div className="form-row">
          <label>User</label>
          <select value={userId} onChange={(e) => setUserId(Number(e.target.value))}>
            {users.map((u) => (
              <option value={u.id} key={u.id}>
                {u.display_name}
              </option>
            ))}
          </select>

          <label>Game</label>
          <select value={gameId} onChange={(e) => setGameId(Number(e.target.value))}>
            {games.map((g) => (
              <option value={g.id} key={g.id}>
                {g.display_name}
              </option>
            ))}
          </select>
        </div>

        <div className="subtle" style={{ marginTop: 8 }}>
          Selected: {selectedUser?.display_name || '-'} / {selectedGame?.display_name || '-'}
        </div>
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
        <button type="submit">Save Manual Playtime</button>
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
        <button type="submit">Save Adjustment</button>
      </form>

      <form className="panel" onSubmit={handleSetTotal}>
        <h3>Set Absolute Total</h3>
        <div className="form-grid-3">
          <input type="number" min={0} value={targetHours} onChange={(e) => setTargetHours(Number(e.target.value))} placeholder="Target hours" />
          <input type="number" min={0} max={59} value={targetMinutes} onChange={(e) => setTargetMinutes(Number(e.target.value))} placeholder="Target minutes" />
          <input value={targetReason} onChange={(e) => setTargetReason(e.target.value)} placeholder="Reason" />
        </div>
        <button type="submit">Apply Absolute Total</button>
      </form>
    </div>
  );
}
