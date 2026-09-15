import { DateRangeKey } from '../types';

export const selectedGameRangeOptions: Array<{ key: DateRangeKey; label: string }> = [
  { key: 'all', label: 'All Time' },
  { key: '7d', label: '7 Days' },
  { key: '14d', label: '14 Days' },
  { key: '30d', label: '30 Days' },
  { key: '60d', label: '60 Days' },
  { key: '90d', label: '90 Days' },
  { key: '365d', label: '365 Days' },
  { key: 'ytd', label: 'YTD' },
  { key: 'custom', label: 'Custom' },
];

export const allGamesRangeOptions: Array<{ key: DateRangeKey; label: string }> = [
  { key: '7d', label: '7 Days' },
  { key: '14d', label: '14 Days' },
  { key: '30d', label: '30 Days' },
  { key: '60d', label: '60 Days' },
  { key: '90d', label: '90 Days' },
  { key: '365d', label: '365 Days' },
  { key: 'ytd', label: 'YTD' },
  { key: 'all', label: 'All Time' },
  { key: 'custom', label: 'Custom' },
];

export const activityRangeOptions: Array<{ key: DateRangeKey; label: string }> = [
  { key: '7d', label: '7 Days' },
  { key: '14d', label: '14 Days' },
  { key: '30d', label: '30 Days' },
  { key: '90d', label: '90 Days' },
  { key: '180d', label: '6 Months' },
  { key: 'ytd', label: 'YTD' },
  { key: '365d', label: '365 Days' },
  { key: 'all', label: 'All Time' },
  { key: 'custom', label: 'Custom' },
];
