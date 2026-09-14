import { useEffect, useState } from 'react';
import { getActiveSessions, getDaily, getOverview, getTopGames, getTopUsers } from '../api/trackerApi';
import { OverviewStats, RankedPlaytime, SourceFilter, TimeBucketPoint } from '../types';

export function useDashboardData(guildId: number, source: SourceFilter) {
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
          getOverview(guildId),
          getTopGames(guildId, source),
          getTopUsers(guildId, source),
          getDaily(guildId),
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
    const interval = window.setInterval(load, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [guildId, source]);

  return { overview, games, users, daily, active, loading, error };
}
