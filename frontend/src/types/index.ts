export type SourceFilter = 'combined' | 'automatic' | 'historical' | 'adjustments';

export interface OverviewStats {
  total_combined_seconds: number;
  total_automatic_seconds: number;
  total_historical_seconds: number;
  total_adjustment_seconds: number;
  tracked_users: number;
  games: number;
  currently_playing: number;
  most_played_game: string | null;
  most_active_user: string | null;
}

export interface RankedPlaytime {
  id: number;
  name: string;
  total_seconds: number;
}

export interface GameUserPlaytime {
  id: number;
  name: string;
  total_seconds: number;
}

export interface TimeBucketPoint {
  bucket: string;
  total_seconds: number;
}

export type DateRangeKey = '7d' | '14d' | '30d' | '60d' | '90d' | '180d' | '365d' | 'ytd' | 'all' | 'custom';

export interface MeResponse {
  username: string;
  role: 'admin' | 'viewer';
  role_name: 'guest' | 'user' | 'admin';
  is_guest: boolean;
  account_status: 'pending' | 'active' | 'locked' | 'disabled' | null;
  tracked_user_id: number | null;
  permissions: string[];
}

export interface RegistrationOption {
  id: number;
  username: string;
  display_name: string;
}

export interface AdminUserAccountRow {
  user_id: number;
  discord_user_id: number;
  username: string;
  display_name: string;
  account_id: number | null;
  account_status: 'pending' | 'active' | 'locked' | 'disabled' | null;
  role: 'guest' | 'user' | 'admin' | null;
  created_at: string | null;
  last_login_at: string | null;
}

export interface PermissionDefinition {
  code: string;
  description: string;
}

export interface AdminGameCatalogRow {
  id: number;
  display_name: string;
  normalized_name: string;
  is_hidden: boolean;
  canonical_game_id: number | null;
  canonical_game_name: string | null;
  has_guild_data: boolean;
}

export interface MergeSuggestionRow {
  source_game_id: number;
  source_name: string;
  target_game_id: number;
  target_name: string;
  confidence: 'high' | 'medium' | 'low';
  reason: string;
  score: number;
}

export interface GameProfile {
  id: number;
  display_name: string;
  icon_url: string | null;
  automatic_seconds: number;
  historical_seconds: number;
  adjustment_seconds: number;
  total_seconds: number;
  unique_players: number;
}

export interface UserProfile {
  id: number;
  display_name: string;
  username: string;
  avatar_url: string | null;
  automatic_seconds: number;
  historical_seconds: number;
  adjustment_seconds: number;
  total_seconds: number;
}

export interface SystemStatus {
  status: string;
  discord_status: string;
  database_status: string;
  bot_uptime_seconds: number | null;
  last_discord_event_at: string | null;
  last_database_write_at: string | null;
  active_sessions: number;
  app_version: string;
}

export interface UserGameBreakdown {
  id: number;
  name: string;
  total_seconds: number;
}

export interface UserSession {
  session_id: number;
  game: string;
  started_at: string;
  ended_at: string | null;
}

export interface GameSession {
  session_id: number;
  user: string;
  started_at: string;
  ended_at: string | null;
}

export interface ActiveSession {
  session_id: number;
  user_id: number;
  user_name: string;
  game_name: string;
  started_at: string;
}
