import client from './client';

export async function getMe(): Promise<{ username: string; role: 'admin' | 'viewer' }> {
  const { data } = await client.get('/auth/me');
  return data;
}

export async function addManualPlaytime(payload: {
  guild_id: number;
  user_id: number;
  game_id: number;
  hours: number;
  minutes: number;
  source: 'historical' | 'imported' | 'correction';
  note?: string;
}) {
  return client.post('/management/manual-playtime', payload);
}

export async function addAdjustment(payload: {
  guild_id: number;
  user_id: number;
  game_id: number;
  hours: number;
  minutes: number;
  sign: number;
  reason: string;
}) {
  return client.post('/management/adjustments', payload);
}

export async function setTotal(payload: {
  guild_id: number;
  user_id: number;
  game_id: number;
  desired_total_seconds: number;
  reason: string;
}) {
  return client.post('/management/set-total', payload);
}

export async function csvPreview(file: File) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await client.post('/management/csv/preview', form);
  return data;
}

export async function csvImport(payload: {
  guild_id: number;
  all_or_nothing: boolean;
  rows: any[];
}) {
  const { data } = await client.post('/management/csv/import', payload);
  return data;
}

export async function steamPreview(payload: {
  guild_id: number;
  user_id: number;
  steam_profile: string;
}) {
  const { data } = await client.post('/management/steam/preview', payload);
  return data;
}

export async function steamImport(payload: {
  guild_id: number;
  user_id: number;
  steam_profile: string;
  replace_previous: boolean;
  max_games: number;
}) {
  const { data } = await client.post('/management/steam/import', payload);
  return data;
}

export async function getAudit(guildId: number, page = 1, pageSize = 50) {
  const { data } = await client.get('/audit', { params: { guild_id: guildId, page, page_size: pageSize } });
  return data;
}

export async function getSystemStatus() {
  const { data } = await client.get('/system/status');
  return data;
}

export async function listUsers(guildId: number) {
  const { data } = await client.get('/users', { params: { guild_id: guildId, page: 1, page_size: 100 } });
  return data;
}

export async function listGames(guildId: number) {
  const { data } = await client.get('/games', { params: { guild_id: guildId, page: 1, page_size: 200 } });
  return data;
}
