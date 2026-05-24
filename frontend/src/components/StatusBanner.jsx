export default function StatusBanner({ type = 'warning', message, onDismiss }) {
  if (!message) return null;

  const className = `alert-banner alert-${type}`;

  return (
    <div className={className} style={{ marginBottom: '1.5rem' }}>
      <span style={{ fontSize: '1.1rem' }}>
        {type === 'warning' && '⚠'}
        {type === 'error' && '✕'}
        {type === 'success' && '✓'}
      </span>
      <div style={{ flex: 1 }}>
        <div>{message}</div>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            background: 'none',
            border: 'none',
            color: 'inherit',
            cursor: 'pointer',
            fontSize: '1.1rem',
            padding: '0 0.25rem',
          }}
        >
          ×
        </button>
      )}
    </div>
  );
}
