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
