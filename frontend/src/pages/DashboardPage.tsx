import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { getGameUsers } from '../api/trackerApi';
import ActivityLineChart from '../charts/ActivityLineChart';
import TopGamesChart from '../charts/TopGamesChart';
import TopUsersChart from '../charts/TopUsersChart';
import CurrentSessions from '../components/CurrentSessions';
import DateRangeTabs from '../components/DateRangeTabs';
import StatCard from '../components/StatCard';
import { useAppPreferences } from '../context/AppPreferencesContext';
import { useDashboardData } from '../hooks/useDashboardData';
import { DateRangeKey } from '../types';
import { activityRangeOptions, allGamesRangeOptions, selectedGameRangeOptions } from '../utils/dateRanges';
import { formatDuration } from '../utils/time';

function describeRangeWindow(range: DateRangeKey, from?: string, to?: string): string {
  const today = dayjs().endOf('day');
  if (range === 'all') return 'All time';
  if (range === 'ytd') return `${dayjs().startOf('year').format('DD MMM YYYY')} -> ${today.format('DD MMM YYYY')}`;
  if (range === 'custom') {
    if (from && to) return `${dayjs(from).format('DD MMM YYYY')} -> ${dayjs(to).format('DD MMM YYYY')}`;
    if (from) return `${dayjs(from).format('DD MMM YYYY')} -> now`;
    if (to) return `up to ${dayjs(to).format('DD MMM YYYY')}`;
    return 'Custom range';
  }
  const days = Number(range.replace('d', ''));
  if (Number.isNaN(days) || days <= 0) return 'Range selected';
  const start = today.subtract(days - 1, 'day').startOf('day');
  return `${start.format('DD MMM YYYY')} -> ${today.format('DD MMM YYYY')}`;
}

export default function DashboardPage() {
  const guildId = Number(import.meta.env.VITE_GUILD_ID || 0);
  const { autoRefreshEnabled } = useAppPreferences();
  const [selectedGameId, setSelectedGameId] = useState<number>(0);
  const [selectedGameUsers, setSelectedGameUsers] = useState<any[]>([]);
  const [selectedGameActivityRange, setSelectedGameActivityRange] = useState<DateRangeKey>('all');
  const [allGamesActivityRange, setAllGamesActivityRange] = useState<DateRangeKey>('30d');
  const [activityOverTimeRange, setActivityOverTimeRange] = useState<DateRangeKey>('30d');
  const [selectedFrom, setSelectedFrom] = useState('');
  const [selectedTo, setSelectedTo] = useState('');
  const [allGamesFrom, setAllGamesFrom] = useState('');
  const [allGamesTo, setAllGamesTo] = useState('');
  const [activityFrom, setActivityFrom] = useState('');
  const [activityTo, setActivityTo] = useState('');
  const [selectedGameLoading, setSelectedGameLoading] = useState(false);
  const [selectedGameError, setSelectedGameError] = useState<string | null>(null);
  const [splitByPlayer, setSplitByPlayer] = useState(false);
  const [showLegend, setShowLegend] = useState(true);
  const [showValues, setShowValues] = useState(true);
  const [showRangeWindow, setShowRangeWindow] = useState(true);
  const [showDateAxis, setShowDateAxis] = useState(true);
  const [splitRows, setSplitRows] = useState<Array<Record<string, string | number>>>([]);
  const [splitPlayers, setSplitPlayers] = useState<Array<{ key: string; name: string; color: string }>>([]);
  const [splitError, setSplitError] = useState<string | null>(null);
  const { overview, games, users, daily, active, loading, error } = useDashboardData(
    guildId,
    autoRefreshEnabled,
    allGamesActivityRange,
    activityOverTimeRange,
    { from: allGamesFrom ? new Date(`${allGamesFrom}T00:00:00Z`).toISOString() : undefined, to: allGamesTo ? new Date(`${allGamesTo}T23:59:59Z`).toISOString() : undefined },
    { from: activityFrom ? new Date(`${activityFrom}T00:00:00Z`).toISOString() : undefined, to: activityTo ? new Date(`${activityTo}T23:59:59Z`).toISOString() : undefined },
  );

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
        const rows = await getGameUsers(
          guildId,
          selectedGameId,
          selectedGameActivityRange,
          selectedGameActivityRange === 'custom'
            ? {
                from: selectedFrom ? new Date(`${selectedFrom}T00:00:00Z`).toISOString() : undefined,
                to: selectedTo ? new Date(`${selectedTo}T23:59:59Z`).toISOString() : undefined,
              }
            : undefined,
        );
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
  }, [guildId, selectedGameId, selectedGameActivityRange, selectedFrom, selectedTo]);

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
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input type="checkbox" checked={showRangeWindow} onChange={(e) => setShowRangeWindow(e.target.checked)} />
            Show range dates
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
        <div className="panel">
          <div className="panel-head-inline">
            <h3>{selectedGame ? `Most Active In ${selectedGame.name}` : 'Select a game to view player split'}</h3>
            {selectedGameLoading && (
              <div className="inline-loader" aria-live="polite">
                <span className="spinner" />
                <span>Loading</span>
              </div>
            )}
          </div>
          <DateRangeTabs
            options={selectedGameRangeOptions}
            value={selectedGameActivityRange}
            onChange={setSelectedGameActivityRange}
            ariaLabel="Selected game activity range"
          />
          {showRangeWindow && (
            <div className="subtle" style={{ marginTop: 8 }}>
              Window: {describeRangeWindow(selectedGameActivityRange, selectedFrom, selectedTo)}
            </div>
          )}
          {selectedGameActivityRange === 'custom' && (
            <div className="form-grid-3" style={{ marginTop: 8 }}>
              <input type="date" value={selectedFrom} onChange={(e) => setSelectedFrom(e.target.value)} />
              <input type="date" value={selectedTo} onChange={(e) => setSelectedTo(e.target.value)} />
              <div className="subtle">Custom range applies to selected game breakdown.</div>
            </div>
          )}
          <TopUsersChart
            data={selectedGameUsers}
            title=""
            height={270}
            showValues={showValues}
            barColor="#22D3EE"
            rowColorsByName={selectedGameColors}
            frameless
          />
        </div>
      </section>

      {selectedGameError && <div className="error-box">{selectedGameError}</div>}
      {splitError && <div className="error-box">{splitError}</div>}

      <section className="two-col dashboard-bottom">
        <div className="panel">
          <h3>Most Active Players (All Games)</h3>
          <DateRangeTabs
            options={allGamesRangeOptions}
            value={allGamesActivityRange}
            onChange={setAllGamesActivityRange}
            ariaLabel="All games activity range"
          />
          {showRangeWindow && (
            <div className="subtle" style={{ marginTop: 8 }}>
              Window: {describeRangeWindow(allGamesActivityRange, allGamesFrom, allGamesTo)}
            </div>
          )}
          {allGamesActivityRange === 'custom' && (
            <div className="form-grid-3" style={{ marginBottom: 8 }}>
              <input type="date" value={allGamesFrom} onChange={(e) => setAllGamesFrom(e.target.value)} />
              <input type="date" value={allGamesTo} onChange={(e) => setAllGamesTo(e.target.value)} />
              <div className="subtle">Custom range applies to all-players ranking.</div>
            </div>
          )}
          <TopUsersChart data={users} title="" height={270} showValues={showValues} frameless />
        </div>
        <div className="split-stack">
          <div className="panel">
            <h3>Activity Over Time</h3>
            <DateRangeTabs
              options={activityRangeOptions}
              value={activityOverTimeRange}
              onChange={setActivityOverTimeRange}
              ariaLabel="Activity over time range"
            />
            <div className="filters" style={{ marginTop: 8, marginBottom: 8 }}>
              <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <input type="checkbox" checked={showDateAxis} onChange={(e) => setShowDateAxis(e.target.checked)} />
                Show date axis
              </label>
            </div>
            {showRangeWindow && (
              <div className="subtle" style={{ marginBottom: 8 }}>
                Window: {describeRangeWindow(activityOverTimeRange, activityFrom, activityTo)}
              </div>
            )}
            {activityOverTimeRange === 'custom' && (
              <div className="form-grid-3" style={{ marginBottom: 8 }}>
                <input type="date" value={activityFrom} onChange={(e) => setActivityFrom(e.target.value)} />
                <input type="date" value={activityTo} onChange={(e) => setActivityTo(e.target.value)} />
                <div className="subtle">Custom range applies to the timeline chart.</div>
              </div>
            )}
            <ActivityLineChart data={daily} title="" height={120} frameless showDateAxis={showDateAxis} />
          </div>
          <CurrentSessions sessions={active} title="Currently Playing" compact />
        </div>
      </section>
    </div>
  );
}
