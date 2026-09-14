import { useEffect, useMemo, useState } from 'react';
import { getGameUsers } from '../api/trackerApi';
import ActivityLineChart from '../charts/ActivityLineChart';
import TopGamesChart from '../charts/TopGamesChart';
import TopUsersChart from '../charts/TopUsersChart';
import CurrentSessions from '../components/CurrentSessions';
import StatCard from '../components/StatCard';
import { useDashboardData } from '../hooks/useDashboardData';
import { formatDuration } from '../utils/time';

export default function DashboardPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const [selectedGameId, setSelectedGameId] = useState<number>(0);
  const [selectedGameUsers, setSelectedGameUsers] = useState<any[]>([]);
  const [selectedGameLoading, setSelectedGameLoading] = useState(false);
  const [selectedGameError, setSelectedGameError] = useState<string | null>(null);
  const [splitByPlayer, setSplitByPlayer] = useState(false);
  const [showLegend, setShowLegend] = useState(true);
  const [showValues, setShowValues] = useState(true);
  const [splitRows, setSplitRows] = useState<Array<Record<string, string | number>>>([]);
  const [splitPlayers, setSplitPlayers] = useState<Array<{ key: string; name: string; color: string }>>([]);
  const [splitError, setSplitError] = useState<string | null>(null);
  const { overview, games, users, daily, active, loading, error } = useDashboardData(guildId);

  const palette = ['#22d3ee', '#f97316', '#4ade80', '#f43f5e', '#facc15', '#a78bfa', '#14b8a6', '#60a5fa'];

  const totalDisplay = useMemo(() => {
    if (!overview) return '0h';
    return formatDuration(overview.total_combined_seconds);
  }, [overview]);

  const selectedGame = useMemo(() => games.find((g) => g.id === selectedGameId), [games, selectedGameId]);
  const selectedGameTopPlayer = selectedGameUsers[0];
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

  useEffect(() => {
    if (games.length === 0) {
      setSelectedGameId(0);
      return;
    }
    setSelectedGameId((current) => (games.some((g) => g.id === current) ? current : games[0].id));
  }, [games]);

  useEffect(() => {
    let cancelled = false;
    const loadSelectedGameUsers = async () => {
      if (!selectedGameId) {
        setSelectedGameUsers([]);
        return;
      }
      setSelectedGameLoading(true);
      setSelectedGameError(null);
      try {
        const rows = await getGameUsers(guildId, selectedGameId);
        if (!cancelled) setSelectedGameUsers(rows.slice(0, 12));
      } catch (err: any) {
        if (!cancelled) {
          setSelectedGameUsers([]);
          setSelectedGameError(err?.response?.data?.detail || 'Failed to load player breakdown for selected game');
        }
      } finally {
        if (!cancelled) setSelectedGameLoading(false);
      }
    };
    void loadSelectedGameUsers();
    return () => {
      cancelled = true;
    };
  }, [guildId, selectedGameId]);

  useEffect(() => {
    let cancelled = false;
    const buildSplitRows = async () => {
      if (!splitByPlayer || games.length === 0) {
        setSplitRows([]);
        setSplitPlayers([]);
        setSplitError(null);
        return;
      }

      setSplitError(null);
      try {
        const targetGames = games.slice(0, 8);
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

        const rows = breakdown.map(({ game, users }) => {
          const row: Record<string, string | number> = {
            id: game.id,
            name: game.name,
            total_seconds: game.total_seconds,
          };

          for (const player of topPlayers) {
            const found = users.find((u) => u.name === player.name);
            row[player.key] = Number(found?.total_seconds || 0);
          }

          return row;
        });

        if (!cancelled) {
          setSplitPlayers(topPlayers);
          setSplitRows(rows);
        }
      } catch (err: any) {
        if (!cancelled) {
          setSplitRows([]);
          setSplitPlayers([]);
          setSplitError(err?.response?.data?.detail || 'Failed to build player-split game chart');
        }
      }
    };

    void buildSplitRows();
    return () => {
      cancelled = true;
    };
  }, [splitByPlayer, games, guildId]);

  if (loading) return <div className="panel">Loading dashboard...</div>;
  if (error) return <div className="panel error-box">{error}</div>;
  if (!overview) return <div className="panel">No data available.</div>;

  return (
    <div className="page-grid">
      <header className="top-row">
        <div>
          <h2>Discord Playtime Activity</h2>
          <p className="subtle">Total combined playtime across tracked sessions and admin-managed records.</p>
        </div>
        <div className="filters">
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input type="checkbox" checked={splitByPlayer} onChange={(e) => setSplitByPlayer(e.target.checked)} />
            Split games by player
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
      </header>

      <section className="stat-grid">
        <StatCard label="Total Playtime" value={totalDisplay} accent="red" />
        <StatCard label="Tracked Users" value={String(overview.tracked_users)} accent="blue" />
        <StatCard label="Games" value={String(overview.games)} accent="green" />
        <StatCard label="Playing Now" value={String(overview.currently_playing)} accent="blue" />
        <StatCard label="Selected Game" value={selectedGame?.name || 'None'} accent="green" />
        <StatCard
          label="Most Active In Selected"
          value={selectedGameTopPlayer ? `${selectedGameTopPlayer.name} (${formatDuration(selectedGameTopPlayer.total_seconds)})` : 'No data'}
          accent="red"
        />
      </section>

      <section className="two-col">
        <TopGamesChart
          data={games}
          selectedGameId={selectedGameId}
          onGameSelect={setSelectedGameId}
          splitMode={splitByPlayer}
          splitRows={splitRows}
          splitPlayers={splitPlayers}
          showLegend={showLegend}
          showValues={showValues}
          title={splitByPlayer ? 'Most Played Games (Split by Player)' : 'Most Played Games'}
        />
        <TopUsersChart
          data={selectedGameUsers}
          title={selectedGame ? `Most Active In ${selectedGame.name}` : 'Select a game to view player split'}
          height={320}
          showValues={showValues}
          barColor="#22D3EE"
          rowColorsByName={selectedGameColors}
        />
      </section>

      {selectedGameLoading && <div className="panel">Loading selected game breakdown...</div>}
      {selectedGameError && <div className="error-box">{selectedGameError}</div>}
      {splitError && <div className="error-box">{splitError}</div>}

      <section className="two-col dashboard-bottom">
        <TopUsersChart data={users} title="Most Active Players (All Games)" height={320} showValues={showValues} />
        <div className="split-stack">
          <ActivityLineChart data={daily} title="Activity Over Time" height={160} />
          <CurrentSessions sessions={active} title="Currently Playing" compact />
        </div>
      </section>
    </div>
  );
}
