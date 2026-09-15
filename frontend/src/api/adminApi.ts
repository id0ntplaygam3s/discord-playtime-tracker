import client from './client';
import { AdminUserAccountRow, MeResponse } from '../types';

export async function getMe(): Promise<MeResponse> {
  const { data } = await client.get('/auth/me');
  return data;
}

export async function listRegistrations() {
  const { data } = await client.get('/auth/registrations');
  return data;
}

export async function approveRegistration(accountId: number) {
  const { data } = await client.post(`/auth/registrations/${accountId}/approve`);
  return data;
}

export async function rejectRegistration(accountId: number) {
  const { data } = await client.post(`/auth/registrations/${accountId}/reject`);
  return data;
}

export async function listPasswordResetRequests() {
  const { data } = await client.get('/auth/password-resets');
  return data;
}

export async function approvePasswordResetRequest(requestId: number) {
  const { data } = await client.post(`/auth/password-resets/${requestId}/approve`);
  return data;
}

export async function addManualPlaytime(payload: {
  guild_id: number;
  user_id: number;
  game_id?: number;
  use_custom_game_title?: boolean;
  custom_game_title?: string;
  hours: number;
  minutes: number;
  source: 'historical' | 'imported' | 'correction';
  note?: string;
}) {
  const { data } = await client.post('/management/manual-playtime', payload);
  return data;
}

export async function listManualPlaytime(guildId: number, userId?: number, gameId?: number, limit = 50) {
  const { data } = await client.get('/management/manual-playtime', {
    params: {
      guild_id: guildId,
      user_id: userId || undefined,
      game_id: gameId || undefined,
      limit,
    },
  });
  return data;
}

export async function listOwnManualPlaytime(guildId: number, gameId?: number, limit = 50) {
  const { data } = await client.get('/management/self/manual-playtime', {
    params: {
      guild_id: guildId,
      game_id: gameId || undefined,
      limit,
    },
  });
  return data;
}

export async function deleteManualPlaytime(guildId: number, entryId: number) {
  const { data } = await client.delete(`/management/manual-playtime/${entryId}`, {
    params: { guild_id: guildId },
  });
  return data;
}

export async function deleteOwnManualPlaytime(guildId: number, entryId: number) {
  const { data } = await client.delete(`/management/self/manual-playtime/${entryId}`, {
    params: { guild_id: guildId },
  });
  return data;
}

export async function addOwnManualPlaytime(payload: {
  guild_id: number;
  user_id: number;
  game_id?: number;
  use_custom_game_title?: boolean;
  custom_game_title?: string;
  hours: number;
  minutes: number;
  source: 'historical' | 'imported' | 'correction';
  note?: string;
}) {
  const { data } = await client.post('/management/self/manual-playtime', payload);
  return data;
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

export async function listAdminUsers(guildId: number): Promise<AdminUserAccountRow[]> {
  const { data } = await client.get('/admin/users', { params: { guild_id: guildId } });
  return data;
}

export async function setAccountRole(accountId: number, role: 'guest' | 'user' | 'admin') {
  const { data } = await client.post(`/admin/users/${accountId}/role`, { role });
  return data;
}

export async function setAccountStatus(accountId: number, status: 'pending' | 'active' | 'locked' | 'disabled') {
  const { data } = await client.post(`/admin/users/${accountId}/status`, { status });
  return data;
}

export async function unlockAccount(accountId: number) {
  const { data } = await client.post(`/admin/users/${accountId}/unlock`);
  return data;
}

export async function adminResetPassword(accountId: number, newPassword: string) {
  const { data } = await client.post(`/admin/users/${accountId}/reset-password`, { new_password: newPassword });
  return data;
}

export async function getPermissions() {
  const { data } = await client.get('/admin/permissions');
  return data;
}

export async function updateRolePermissions(roleName: 'guest' | 'user' | 'admin', permissions: Record<string, boolean>) {
  const { data } = await client.post(`/admin/permissions/roles/${roleName}`, { permissions });
  return data;
}

export async function getUserPermissionOverrides(accountId: number) {
  const { data } = await client.get(`/admin/permissions/users/${accountId}`);
  return data;
}

export async function setUserPermissionOverride(accountId: number, permission: string, mode: 'inherit' | 'allow' | 'deny') {
  const { data } = await client.post(`/admin/permissions/users/${accountId}`, { permission, mode });
  return data;
}

export async function getRuntimeSettings() {
  const { data } = await client.get('/admin/settings');
  return data;
}

export async function updateRuntimeSettings(payload: Record<string, unknown>) {
  const { data } = await client.post('/admin/settings', payload);
  return data;
}

export async function deleteUser(guildId: number, userId: number) {
  const { data } = await client.delete(`/users/${userId}`, { params: { guild_id: guildId } });
  return data;
}

export async function listGames(guildId: number) {
  const { data } = await client.get('/games', { params: { guild_id: guildId, page: 1, page_size: 100 } });
  return data;
}

export async function getGamesAdminCatalog(guildId: number, includeHidden = true) {
  const { data } = await client.get('/games/meta/catalog', { params: { guild_id: guildId, include_hidden: includeHidden } });
  return data;
}

export async function renameGame(guildId: number, gameId: number, displayName: string) {
  const { data } = await client.post(`/games/${gameId}/rename`, { guild_id: guildId, display_name: displayName });
  return data;
}

export async function mergeGames(guildId: number, sourceGameId: number, targetGameId: number, reason: string) {
  const { data } = await client.post('/games/merge', {
    guild_id: guildId,
    source_game_id: sourceGameId,
    target_game_id: targetGameId,
    reason,
  });
  return data;
}

export async function unmergeGame(guildId: number, gameId: number, reason: string) {
  const { data } = await client.post(`/games/${gameId}/unmerge`, { guild_id: guildId, reason });
  return data;
}

export async function getMergeSuggestions(limit = 100, confidence?: 'high' | 'medium' | 'low') {
  const { data } = await client.get('/games/meta/merge-suggestions', { params: { limit, confidence: confidence || undefined } });
  return data;
}

export async function ignoreMergeSuggestion(guildId: number, sourceGameId: number, targetGameId: number) {
  const { data } = await client.post(`/games/meta/merge-suggestions/${sourceGameId}/${targetGameId}/ignore`, { guild_id: guildId });
  return data;
}
