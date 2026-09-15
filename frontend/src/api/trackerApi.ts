import client from './client';
import { DateRangeKey, GameUserPlaytime, OverviewStats, RankedPlaytime, RegistrationOption, SourceFilter, TimeBucketPoint } from '../types';

type RangeParams = {
  range?: DateRangeKey;
  from?: string;
  to?: string;
};

export async function login(username: string, password: string): Promise<string> {
  const { data } = await client.post('/auth/login', { username, password });
  return data.access_token;
}

export async function guestLogin(): Promise<string> {
  const { data } = await client.post('/auth/guest');
  return data.access_token;
}

export async function accountLogin(userId: number, password: string): Promise<string> {
  const { data } = await client.post('/auth/account-login', { user_id: userId, password });
  return data.access_token;
}

export async function getRegistrationOptions(): Promise<RegistrationOption[]> {
  const { data } = await client.get('/auth/registration-options');
  return data;
}

export async function getAccountOptions(): Promise<Array<{ user_id: number; username: string; display_name: string; status: string }>> {
  const { data } = await client.get('/auth/account-options');
  return data;
}

export async function registerAccount(userId: number, password: string, confirmPassword: string): Promise<{ status: string }> {
  const { data } = await client.post('/auth/register', {
    user_id: userId,
    password,
    confirm_password: confirmPassword,
  });
  return data;
}

export async function requestPasswordReset(userId: number): Promise<{ ok: boolean }> {
  const { data } = await client.post('/auth/password-resets/request', { user_id: userId });
  return data;
}

export async function completePasswordReset(token: string, newPassword: string, confirmPassword: string): Promise<{ ok: boolean }> {
  const { data } = await client.post('/auth/password-resets/complete', {
    token,
    new_password: newPassword,
    confirm_password: confirmPassword,
  });
  return data;
}

export async function getOverview(guildId: number, range: DateRangeKey = 'all', custom?: RangeParams): Promise<OverviewStats> {
  const { data } = await client.get('/stats/overview', { params: { guild_id: guildId, range, ...(custom || {}) } });
  return data;
}

export async function getTopGames(guildId: number, source: SourceFilter, limit = 10, range: DateRangeKey = 'all', custom?: RangeParams): Promise<RankedPlaytime[]> {
  const { data } = await client.get('/stats/games', { params: { guild_id: guildId, source, limit, range, ...(custom || {}) } });
  return data;
}

export async function getTopUsers(guildId: number, source: SourceFilter, limit = 10, range: DateRangeKey = 'all', custom?: RangeParams): Promise<RankedPlaytime[]> {
  const { data } = await client.get('/stats/users', { params: { guild_id: guildId, source, limit, range, ...(custom || {}) } });
  return data;
}

export async function getActivityOverTime(guildId: number, range: DateRangeKey, custom?: RangeParams): Promise<TimeBucketPoint[]> {
  const { data } = await client.get('/stats/activity-over-time', { params: { guild_id: guildId, range, ...(custom || {}) } });
  return data;
}

export async function getActiveSessions(guildId: number): Promise<any[]> {
  const { data } = await client.get('/activity/active', { params: { guild_id: guildId } });
  return data;
}

export async function getGameUsers(guildId: number, gameId: number, range: DateRangeKey = 'all', custom?: RangeParams): Promise<GameUserPlaytime[]> {
  const { data } = await client.get(`/games/${gameId}/users`, { params: { guild_id: guildId, range, ...(custom || {}) } });
  return data;
}
