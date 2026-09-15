import { useEffect, useState } from 'react';
import { getActiveSessions, getActivityOverTime, getOverview, getTopGames, getTopUsers } from '../api/trackerApi';
import { DateRangeKey, OverviewStats, RankedPlaytime, TimeBucketPoint } from '../types';

export function useDashboardData(
  guildId: number,
  autoRefreshEnabled: boolean,
  allGamesActivityRange: DateRangeKey,
  activityOverTimeRange: DateRangeKey,
  allGamesCustomRange?: { from?: string; to?: string },
  activityCustomRange?: { from?: string; to?: string },
) {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [games, setGames] = useState<RankedPlaytime[]>([]);
  const [users, setUsers] = useState<RankedPlaytime[]>([]);
  const [daily, setDaily] = useState<TimeBucketPoint[]>([]);
  const [active, setActive] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [overviewRes, gamesRes, usersRes, dailyRes, activeRes] = await Promise.all([
          getOverview(guildId, 'all'),
          getTopGames(guildId, 'combined', 10, 'all'),
          getTopUsers(guildId, 'combined', 10, allGamesActivityRange, allGamesActivityRange === 'custom' ? allGamesCustomRange : undefined),
          getActivityOverTime(guildId, activityOverTimeRange, activityOverTimeRange === 'custom' ? activityCustomRange : undefined),
          getActiveSessions(guildId),
        ]);

        if (!cancelled) {
          setOverview(overviewRes);
          setGames(gamesRes);
          setUsers(usersRes);
          setDaily(dailyRes);
          setActive(activeRes);
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.response?.data?.detail || 'Failed to load dashboard data');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();
    const interval = autoRefreshEnabled ? window.setInterval(load, 30_000) : null;
    return () => {
      cancelled = true;
      if (interval) window.clearInterval(interval);
    };
  }, [guildId, autoRefreshEnabled, allGamesActivityRange, activityOverTimeRange, allGamesCustomRange?.from, allGamesCustomRange?.to, activityCustomRange?.from, activityCustomRange?.to]);

  return { overview, games, users, daily, active, loading, error };
}
