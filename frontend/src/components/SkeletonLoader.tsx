interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

export function SkeletonText({ className, style }: SkeletonProps) {
  return <div className={`skeleton skeleton-text ${className || ''}`} style={style} />;
}

export function SkeletonRow({ className, style }: SkeletonProps) {
  return (
    <div className={`skeleton-row ${className || ''}`} style={style}>
      <div className="skeleton skeleton-avatar" />
      <div style={{ flex: 1 }}>
        <SkeletonText style={{ width: '60%' }} />
        <SkeletonText style={{ width: '40%' }} />
      </div>
    </div>
  );
}

export function SkeletonCard({ className, style }: SkeletonProps) {
  return <div className={`skeleton skeleton-card ${className || ''}`} style={style} />;
}

export function SkeletonGraph({ className, style }: SkeletonProps) {
  return <div className={`skeleton skeleton-graph ${className || ''}`} style={style} />;
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th style={{ width: '40%' }}>
              <div className="skeleton skeleton-text" style={{ height: 12 }} />
            </th>
            <th style={{ width: '30%' }}>
              <div className="skeleton skeleton-text" style={{ height: 12 }} />
            </th>
            <th style={{ width: '30%' }}>
              <div className="skeleton skeleton-text" style={{ height: 12 }} />
            </th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i} style={{ height: 44 }}>
              <td>
                <div className="skeleton" style={{ height: 16, width: '70%' }} />
              </td>
              <td>
                <div className="skeleton" style={{ height: 16, width: '50%' }} />
              </td>
              <td>
                <div className="skeleton" style={{ height: 16, width: '30%' }} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="stat-card">
      <div className="skeleton skeleton-text" style={{ width: '60%' }} />
      <div className="skeleton skeleton-text" style={{ width: '40%', height: 24, marginTop: 8 }} />
    </div>
  );
}
