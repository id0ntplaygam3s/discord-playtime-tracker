interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ icon = '📭', title, description, action }: EmptyStateProps) {
  return (
    <div className="panel">
      <div className="empty-state">
        <div className="empty-state-icon">{icon}</div>
        <div className="empty-state-title">{title}</div>
        {description && <div className="empty-state-desc">{description}</div>}
        {action && <div style={{ marginTop: 16 }}>{action}</div>}
      </div>
    </div>
  );
}
