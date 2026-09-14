import { useEffect, useMemo, useState } from 'react';
import TopGamesChart from '../charts/TopGamesChart';
import TopUsersChart from '../charts/TopUsersChart';
import { getGameUsers, getTopGames } from '../api/trackerApi';
import { RankedPlaytime, SourceFilter } from '../types';
import { formatDuration } from '../utils/time';

const sourceOptions: SourceFilter[] = ['combined', 'automatic', 'historical', 'adjustments'];

export default function GamesGraphPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [source, setSource] = useState<SourceFilter>('combined');
  const [rows, setRows] = useState<RankedPlaytime[]>([]);
  const [selectedGameId, setSelectedGameId] = useState<number>(0);
  const [selectedUsers, setSelectedUsers] = useState<any[]>([]);
  const [splitByPlayer, setSplitByPlayer] = useState(false);
  const [showLegend, setShowLegend] = useState(true);
  const [showValues, setShowValues] = useState(true);
  const [splitRows, setSplitRows] = useState<Array<Record<string, string | number>>>([]);
  const [splitPlayers, setSplitPlayers] = useState<Array<{ key: string; name: string; color: string }>>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const palette = ['#22d3ee', '#f97316', '#4ade80', '#f43f5e', '#facc15', '#a78bfa', '#14b8a6', '#60a5fa'];

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getTopGames(guildId, source, 30);
        if (!cancelled) {
          setRows(data);
          setSelectedGameId((current) => (data.some((row) => row.id === current) ? current : data[0]?.id || 0));
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.response?.data?.detail || 'Failed to load games graph');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [guildId, source]);

  useEffect(() => {
    let cancelled = false;
    const loadUsers = async () => {
      if (!selectedGameId) {
        setSelectedUsers([]);
        return;
      }
      try {
        const users = await getGameUsers(guildId, selectedGameId);
        if (!cancelled) setSelectedUsers(users.slice(0, 12));
      } catch {
        if (!cancelled) setSelectedUsers([]);
      }
    };

    void loadUsers();
    return () => {
      cancelled = true;
    };
  }, [guildId, selectedGameId]);

  useEffect(() => {
    let cancelled = false;
    const buildSplitRows = async () => {
      if (!splitByPlayer || rows.length === 0) {
        setSplitRows([]);
        setSplitPlayers([]);
        return;
      }

      try {
        const targetGames = rows.slice(0, 10);
        const breakdown = await Promise.all(
          targetGames.map(async (game) => ({ game, users: (await getGameUsers(guildId, game.id)).slice(0, 12) }))
        );

        const totalsByPlayer = new Map<string, number>();
        for (const item of breakdown) {
          for (const user of item.users) {
            totalsByPlayer.set(user.name, (totalsByPlayer.get(user.name) || 0) + Number(user.total_seconds || 0));
          }
        }

        const topPlayers = [...totalsByPlayer.entries()]
          .sort((a, b) => b[1] - a[1])
          .slice(0, 6)
          .map(([name], idx) => ({ key: `player_${idx + 1}`, name, color: palette[idx % palette.length] }));

        const nextRows = breakdown.map(({ game, users }) => {
          const row: Record<string, string | number> = {
            id: game.id,
            name: game.name,
            total_seconds: game.total_seconds,
          };
          for (const player of topPlayers) {
            row[player.key] = Number(users.find((u) => u.name === player.name)?.total_seconds || 0);
          }
          return row;
        });

        if (!cancelled) {
          setSplitPlayers(topPlayers);
          setSplitRows(nextRows);
        }
      } catch {
        if (!cancelled) {
          setSplitRows([]);
          setSplitPlayers([]);
        }
      }
    };

    void buildSplitRows();
    return () => {
      cancelled = true;
    };
  }, [splitByPlayer, rows, guildId]);

  const totalSeconds = useMemo(() => rows.reduce((sum, row) => sum + row.total_seconds, 0), [rows]);
  const topGame = rows[0];
  const selectedGame = rows.find((r) => r.id === selectedGameId);
  const selectedGameColors = useMemo(
    () =>
      splitByPlayer
        ? splitPlayers.reduce((acc, player) => {
            acc[player.name] = player.color;
            return acc;
          }, {} as Record<string, string>)
        : undefined,
    [splitByPlayer, splitPlayers]
  );

  return (
    <div className="page-grid">
      <header className="panel graph-hero graph-hero-games">
        <div>
          <h2>Games (Graph)</h2>
          <p className="subtle">A large comparison view of game playtime across your guild.</p>
        </div>
        <div className="filters">
          <label>Data source</label>
          <select value={source} onChange={(e) => setSource(e.target.value as SourceFilter)}>
            {sourceOptions.map((option) => (
              <option value={option} key={option}>
                {option[0].toUpperCase() + option.slice(1)}
              </option>
            ))}
          </select>
            <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" checked={splitByPlayer} onChange={(e) => setSplitByPlayer(e.target.checked)} />
              Split by player
            </label>
            <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" checked={showLegend} onChange={(e) => setShowLegend(e.target.checked)} disabled={!splitByPlayer} />
              Legend
            </label>
            <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" checked={showValues} onChange={(e) => setShowValues(e.target.checked)} />
              Values
            </label>
        </div>
        <div className="graph-stats">
          <div>
            <span className="subtle">Games Compared</span>
            <strong>{rows.length}</strong>
          </div>
          <div>
            <span className="subtle">Combined Time</span>
            <strong>{formatDuration(totalSeconds)}</strong>
          </div>
          <div>
            <span className="subtle">Top Game</span>
            <strong>{topGame ? topGame.name : 'N/A'}</strong>
          </div>
        </div>
      </header>

      {loading && <div className="panel">Loading games graph...</div>}
      {error && <div className="error-box">{error}</div>}

      {!loading && !error && (
        <>
          <TopGamesChart
            data={rows}
            selectedGameId={selectedGameId}
            onGameSelect={setSelectedGameId}
            splitMode={splitByPlayer}
            splitRows={splitRows}
            splitPlayers={splitPlayers}
            showLegend={showLegend}
            showValues={showValues}
            title={splitByPlayer ? 'All Games Comparison (Split by Player)' : 'All Games Comparison'}
            height={Math.max(460, Math.min(980, rows.length * 30 + 120))}
          />

          <TopUsersChart
            data={selectedUsers}
            title={selectedGame ? `Most Active In ${selectedGame.name}` : 'Select a game bar for player breakdown'}
            height={360}
            showValues={showValues}
            rowColorsByName={selectedGameColors}
          />
        </>
      )}
    </div>
  );
}