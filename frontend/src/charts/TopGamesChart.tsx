import { Bar, BarChart, Cell, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { RankedPlaytime } from '../types';
import { formatDuration } from '../utils/time';

const truncate = (label: string, max = 22) => (label.length <= max ? label : `${label.slice(0, max - 1)}...`);
const formatLabelDuration = (value: unknown) => formatDuration(Number(value || 0));

interface TopGamesChartProps {
  data: RankedPlaytime[];
  title?: string;
  height?: number;
  selectedGameId?: number;
  onGameSelect?: (gameId: number) => void;
  splitMode?: boolean;
  splitRows?: Array<Record<string, string | number>>;
  splitPlayers?: Array<{ key: string; name: string; color: string }>;
  showLegend?: boolean;
  showValues?: boolean;
}

function resolveGameId(entry: any): number {
  const raw = entry?.id ?? entry?.payload?.id;
  return Number(raw || 0);
}

function renderSplitTooltip({ active, label, payload, splitPlayers }: any) {
  if (!active || !payload || payload.length === 0) return null;

  const rows = payload
    .map((item: any) => {
      const value = Number(item?.value || 0);
      const key = String(item?.dataKey || '');
      if (key === 'total_seconds') return null;
      const player = splitPlayers?.find((p: any) => p.key === key);
      return {
        key,
        name: player?.name || key,
        color: player?.color || item?.color || '#cbd5e1',
        value,
      };
    })
    .filter((item: any) => item)
    .filter((item: any) => item.value > 0)
    .sort((a: any, b: any) => b.value - a.value);

  if (rows.length === 0) return null;

  return (
    <div style={{ background: '#0b1117', border: '1px solid #1f2937', padding: '8px 10px', borderRadius: 8 }}>
      <div style={{ color: '#e2e8f0', marginBottom: 6 }}>{String(label)}</div>
      {rows.map((row: any) => (
        <div key={row.key} style={{ display: 'flex', gap: 8, alignItems: 'center', color: '#cbd5e1', marginBottom: 2 }}>
          <span style={{ width: 10, height: 10, borderRadius: 999, background: row.color, display: 'inline-block' }} />
          <span>{row.name}</span>
          <span style={{ marginLeft: 'auto' }}>{formatDuration(row.value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function TopGamesChart({
  data,
  title = 'Most Played Games',
  height = 320,
  selectedGameId,
  onGameSelect,
  splitMode = false,
  splitRows,
  splitPlayers,
  showLegend = true,
  showValues = false,
}: TopGamesChartProps) {
  const yAxisWidth = Math.min(
    280,
    Math.max(
      140,
      data.reduce((max, row) => Math.max(max, Math.min(row.name.length, 36) * 7), 140)
    )
  );

  const chartRows = splitMode && splitRows && splitRows.length > 0 ? splitRows : data;

  const handleBarClick = (entry: any) => {
    if (!onGameSelect) return;
    const id = resolveGameId(entry);
    if (id > 0) onGameSelect(id);
  };

  return (
    <div className="panel">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={chartRows} layout="vertical" margin={{ top: 8, right: 24, left: 16, bottom: 8 }}>
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={yAxisWidth} stroke="#A5B4FC" tickFormatter={(v) => truncate(String(v))} />
          <Tooltip
            formatter={(value: number, key: string) => {
              if (splitMode) {
                const player = splitPlayers?.find((p) => p.key === key);
                return [formatDuration(Number(value || 0)), player?.name || key];
              }
              return [formatDuration(Number(value || 0)), 'Total play time'];
            }}
            labelFormatter={(label) => String(label)}
            contentStyle={{ background: '#0b1117', border: '1px solid #1f2937' }}
            content={splitMode ? (props) => renderSplitTooltip({ ...props, splitPlayers }) : undefined}
          />
          {splitMode && splitPlayers && splitPlayers.length > 0 ? (
            <>
              {showLegend && <Legend wrapperStyle={{ color: '#cbd5e1' }} />}
              {splitPlayers.map((player, idx) => (
                <Bar key={player.key} dataKey={player.key} name={player.name} stackId="players" fill={player.color} onClick={handleBarClick}>
                  {showValues && idx === splitPlayers.length - 1 && (
                    <LabelList
                      dataKey={player.key}
                      valueAccessor={(entry: any) => Number(entry?.total_seconds || 0)}
                      position="right"
                      formatter={(value: unknown) => (Number(value || 0) >= 1800 ? formatLabelDuration(value) : '')}
                      fill="#cbd5e1"
                    />
                  )}
                </Bar>
              ))}
            </>
          ) : (
            <Bar dataKey="total_seconds" fill="#FB7185" radius={[6, 6, 6, 6]} onClick={handleBarClick}>
              {data.map((row) => (
                <Cell
                  key={`game-${row.id}`}
                  fill={selectedGameId && row.id === selectedGameId ? '#f97316' : '#FB7185'}
                  cursor={onGameSelect ? 'pointer' : 'default'}
                />
              ))}
              {showValues && (
                <LabelList dataKey="total_seconds" position="right" formatter={formatLabelDuration} fill="#cbd5e1" />
              )}
            </Bar>
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
