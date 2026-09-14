export function formatDuration(totalSeconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    const remHours = hours % 24;
    return `${days}d ${remHours}h`;
  }
  return `${hours}h ${minutes}m`;
}

export function formatSignedDuration(totalSeconds: number): string {
  const value = Math.floor(Number(totalSeconds || 0));
  if (value === 0) return '0h 0m';
  return `${value < 0 ? '-' : '+'}${formatDuration(Math.abs(value))}`;
}
