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
