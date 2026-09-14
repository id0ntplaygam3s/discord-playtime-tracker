import client from './client';
import { OverviewStats, RankedPlaytime, SourceFilter, TimeBucketPoint } from '../types';

export async function login(username: string, password: string): Promise<string> {
  const { data } = await client.post('/auth/login', { username, password });
  return data.access_token;
}

export async function guestLogin(): Promise<string> {
  const { data } = await client.post('/auth/guest');
  return data.access_token;
}

export async function getOverview(guildId: number): Promise<OverviewStats> {
  const { data } = await client.get('/stats/overview', { params: { guild_id: guildId } });
  return data;
}

export async function getTopGames(guildId: number, source: SourceFilter): Promise<RankedPlaytime[]> {
  const { data } = await client.get('/stats/games', { params: { guild_id: guildId, source, limit: 10 } });
  return data;
}

export async function getTopUsers(guildId: number, source: SourceFilter): Promise<RankedPlaytime[]> {
  const { data } = await client.get('/stats/users', { params: { guild_id: guildId, source, limit: 10 } });
  return data;
}

export async function getDaily(guildId: number): Promise<TimeBucketPoint[]> {
  const { data } = await client.get('/stats/daily', { params: { guild_id: guildId } });
  return data;
}

export async function getActiveSessions(guildId: number): Promise<any[]> {
  const { data } = await client.get('/activity/active', { params: { guild_id: guildId } });
  return data;
}
