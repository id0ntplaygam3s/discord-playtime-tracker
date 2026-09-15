import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  getGamesAdminCatalog,
  getMergeSuggestions,
  ignoreMergeSuggestion,
  mergeGames,
  renameGame,
  setGameVisibility,
  unmergeGame,
} from '../api/adminApi';
import { AdminGameCatalogRow, MergeSuggestionRow } from '../types';

export default function GamesAdminPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [games, setGames] = useState<AdminGameCatalogRow[]>([]);
  const [suggestions, setSuggestions] = useState<MergeSuggestionRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [showHidden, setShowHidden] = useState(true);

  const [renameGameId, setRenameGameId] = useState<number>(0);
  const [renameTitle, setRenameTitle] = useState('');

  const [mergeSourceId, setMergeSourceId] = useState<number>(0);
  const [mergeTargetId, setMergeTargetId] = useState<number>(0);
  const [mergeReason, setMergeReason] = useState('Merged duplicate game identity');

  const [unmergeGameId, setUnmergeGameId] = useState<number>(0);
  const [unmergeReason, setUnmergeReason] = useState('Restore game identity');

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [catalog, mergeSuggestions] = await Promise.all([
        getGamesAdminCatalog(guildId, showHidden),
        getMergeSuggestions(200),
      ]);
      const nextGames = Array.isArray(catalog) ? catalog : [];
      const nextSuggestions = Array.isArray(mergeSuggestions) ? mergeSuggestions : [];
      setGames(nextGames);
      setSuggestions(nextSuggestions);

      if (!renameGameId && nextGames.length > 0) {
        setRenameGameId(nextGames[0].id);
        setRenameTitle(nextGames[0].display_name);
      }

      const mergeCandidates = nextGames.filter((g) => !g.is_hidden);
      if (!mergeSourceId && mergeCandidates.length > 0) {
        setMergeSourceId(mergeCandidates[0].id);
      }
      if (!mergeTargetId && mergeCandidates.length > 1) {
        setMergeTargetId(mergeCandidates[1].id);
      }

      const mergedCandidates = nextGames.filter((g) => Boolean(g.canonical_game_id));
      if (!unmergeGameId && mergedCandidates.length > 0) {
        setUnmergeGameId(mergedCandidates[0].id);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load games admin data');
      setGames([]);
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
  }, [guildId, showHidden]);

  const filteredGames = useMemo(() => {
    const token = search.trim().toLowerCase();
    if (!token) return games;
    return games.filter((g) => {
      const canonical = (g.canonical_game_name || '').toLowerCase();
      return g.display_name.toLowerCase().includes(token) || g.normalized_name.toLowerCase().includes(token) || canonical.includes(token);
    });
  }, [games, search]);

  const visibleGames = useMemo(() => games.filter((g) => !g.is_hidden), [games]);
  const mergedGames = useMemo(() => games.filter((g) => Boolean(g.canonical_game_id)), [games]);

  const handleRename = async (e: FormEvent) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    if (!renameGameId || !renameTitle.trim()) {
      setError('Choose a game and provide a new title');
      return;
    }
    try {
      await renameGame(guildId, renameGameId, renameTitle.trim());
      setMessage('Game renamed');
      await loadAll();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to rename game');
    }
  };

  const handleMerge = async (e: FormEvent) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    if (!mergeSourceId || !mergeTargetId || mergeSourceId === mergeTargetId) {
      setError('Select different source and target games');
      return;
    }
    try {
      await mergeGames(guildId, mergeSourceId, mergeTargetId, mergeReason.trim() || 'Merged duplicate game identity');
      setMessage('Games merged');
      await loadAll();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to merge games');
    }
  };

  const handleUnmerge = async (e: FormEvent) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    if (!unmergeGameId) {
      setError('Select a merged game to unmerge');
      return;
    }
    try {
      await unmergeGame(guildId, unmergeGameId, unmergeReason.trim() || 'Restore game identity');
      setMessage('Game unmerged');
      await loadAll();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to unmerge game');
    }
  };

  const acceptSuggestion = async (row: MergeSuggestionRow) => {
    setMessage(null);
    setError(null);
    try {
      await mergeGames(guildId, row.source_game_id, row.target_game_id, `Suggestion accepted (${row.confidence})`);
      setMessage(`Suggestion merged: ${row.source_name} -> ${row.target_name}`);
      await loadAll();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to accept suggestion');
    }
  };

  const dismissSuggestion = async (row: MergeSuggestionRow) => {
    setMessage(null);
    setError(null);
    try {
      await ignoreMergeSuggestion(guildId, row.source_game_id, row.target_game_id);
      setMessage(`Suggestion ignored: ${row.source_name} -> ${row.target_name}`);
      await loadAll();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to ignore suggestion');
    }
  };

  const toggleVisibility = async (row: AdminGameCatalogRow) => {
    setMessage(null);
    setError(null);
    try {
      await setGameVisibility(
        guildId,
        row.id,
        !row.is_hidden,
        row.is_hidden ? 'Unhidden from Games Admin catalog' : 'Hidden from Games Admin catalog'
      );
      setMessage(row.is_hidden ? `Game unhidden: ${row.display_name}` : `Game hidden: ${row.display_name}`);
      await loadAll();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update game visibility');
    }
  };

  return (
    <div className="page-grid">
      <div className="panel">
        <h2>Games Admin</h2>
        <p className="subtle">Rename games, merge duplicate identities, unmerge when needed, and review merge suggestions.</p>
        <div className="form-row">
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={showHidden} onChange={(e) => setShowHidden(e.target.checked)} />
            Show merged/hidden records
          </label>
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search games" />
          <button type="button" onClick={() => void loadAll()}>
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}
      {loading && <div className="panel">Loading admin game data...</div>}

      <form className="panel" onSubmit={handleRename}>
        <h3>Rename Game</h3>
        <div className="form-grid-3">
          <select
            value={renameGameId}
            onChange={(e) => {
              const id = Number(e.target.value);
              setRenameGameId(id);
              const found = games.find((g) => g.id === id);
              if (found) setRenameTitle(found.display_name);
            }}
          >
            {games.map((g) => (
              <option key={g.id} value={g.id}>
                #{g.id} {g.display_name}{g.is_hidden ? ' (hidden)' : ''}
              </option>
            ))}
          </select>
          <input value={renameTitle} onChange={(e) => setRenameTitle(e.target.value)} placeholder="New game title" />
          <button type="submit">Apply Rename</button>
        </div>
      </form>

      <form className="panel" onSubmit={handleMerge}>
        <h3>Merge Games</h3>
        <div className="subtle" style={{ marginBottom: 8 }}>
          Source becomes hidden and points to target as canonical. Historical records are not rewritten.
        </div>
        <div className="form-grid-4">
          <select value={mergeSourceId} onChange={(e) => setMergeSourceId(Number(e.target.value))}>
            {visibleGames.map((g) => (
              <option key={g.id} value={g.id}>
                Source: #{g.id} {g.display_name}
              </option>
            ))}
          </select>
          <select value={mergeTargetId} onChange={(e) => setMergeTargetId(Number(e.target.value))}>
            {visibleGames.map((g) => (
              <option key={g.id} value={g.id}>
                Target: #{g.id} {g.display_name}
              </option>
            ))}
          </select>
          <input value={mergeReason} onChange={(e) => setMergeReason(e.target.value)} placeholder="Reason" />
          <button type="submit">Merge</button>
        </div>
      </form>

      <form className="panel" onSubmit={handleUnmerge}>
        <h3>Unmerge Game</h3>
        <div className="form-grid-3">
          <select value={unmergeGameId} onChange={(e) => setUnmergeGameId(Number(e.target.value))}>
            {mergedGames.length === 0 && <option value={0}>No merged games found</option>}
            {mergedGames.map((g) => (
              <option key={g.id} value={g.id}>
                #{g.id} {g.display_name} -{'>'} #{g.canonical_game_id} {g.canonical_game_name || 'Unknown'}
              </option>
            ))}
          </select>
          <input value={unmergeReason} onChange={(e) => setUnmergeReason(e.target.value)} placeholder="Reason" />
          <button type="submit" disabled={!unmergeGameId}>Unmerge</button>
        </div>
      </form>

      <div className="panel">
        <h3>Merge Suggestions</h3>
        {suggestions.length === 0 ? (
          <div className="empty">No suggestions at the moment.</div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Target</th>
                  <th>Confidence</th>
                  <th>Reason</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {suggestions.map((row) => (
                  <tr key={`${row.source_game_id}-${row.target_game_id}`}>
                    <td>#{row.source_game_id} {row.source_name}</td>
                    <td>#{row.target_game_id} {row.target_name}</td>
                    <td>{row.confidence}</td>
                    <td>{row.reason}</td>
                    <td style={{ display: 'flex', gap: 8 }}>
                      <button type="button" onClick={() => void acceptSuggestion(row)}>Merge</button>
                      <button type="button" onClick={() => void dismissSuggestion(row)}>Ignore</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="panel">
        <h3>Game Catalog</h3>
        <div className="subtle" style={{ marginBottom: 8 }}>
          Showing {filteredGames.length} game records ({showHidden ? 'including hidden/merged' : 'visible only'}).
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Display Name</th>
                <th>Status</th>
                <th>Canonical Target</th>
                <th>Has Data</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredGames.map((g) => (
                <tr key={g.id}>
                  <td>#{g.id}</td>
                  <td>{g.display_name}</td>
                  <td>{g.is_hidden ? 'hidden/merged' : 'visible'}</td>
                  <td>{g.canonical_game_id ? `#${g.canonical_game_id} ${g.canonical_game_name || ''}` : '-'}</td>
                  <td>{g.has_guild_data ? 'yes' : 'no'}</td>
                  <td>
                    {g.canonical_game_id ? (
                      <span className="subtle">Use unmerge</span>
                    ) : (
                      <button type="button" onClick={() => void toggleVisibility(g)}>
                        {g.is_hidden ? 'Unhide' : 'Hide'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
