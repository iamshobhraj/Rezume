export default function ResumePreview({ content }) {
  if (!content) return null;

  let data;
  try {
    data = typeof content === 'string' ? JSON.parse(content) : content;
  } catch {
    return (
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
          {content}
        </pre>
      </div>
    );
  }

  if (data.error) {
    return (
      <div className="alert-banner alert-error">
        <span>✕</span>
        <span>{data.error}</span>
      </div>
    );
  }

  return (
    <div className="glass-panel animate-fade-in-up" style={{ padding: '2rem' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>{data.name || 'Candidate'}</h2>
        {data.contact && (
          <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', marginTop: '0.375rem' }}>
            {[data.contact.email, data.contact.phone, data.contact.linkedin, data.contact.location]
              .filter(Boolean)
              .join(' · ')}
          </div>
        )}
      </div>

      {/* Summary */}
      {data.summary && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '0.875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-accent-violet)', marginBottom: '0.5rem' }}>
            Professional Summary
          </h3>
          <p style={{ margin: 0, fontSize: '0.875rem', lineHeight: 1.7, color: 'var(--color-text-secondary)' }}>
            {data.summary}
          </p>
        </div>
      )}

      {/* Experience */}
      {data.experience?.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '0.875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-accent-violet)', marginBottom: '0.75rem' }}>
            Experience
          </h3>
          {data.experience.map((exp, i) => (
            <div key={i} style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.25rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9375rem' }}>{exp.title}</span>
                <span style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>{exp.date_range}</span>
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', marginBottom: '0.375rem', fontStyle: 'italic' }}>
                {exp.company}
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8125rem', lineHeight: 1.7, color: 'var(--color-text-secondary)' }}>
                {exp.bullets?.map((b, j) => <li key={j}>{b}</li>)}
              </ul>
            </div>
          ))}
        </div>
      )}

      {/* Skills */}
      {data.skills && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '0.875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-accent-violet)', marginBottom: '0.5rem' }}>
            Technical Skills
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            {Object.entries(data.skills).map(([cat, skills]) =>
              skills?.length > 0 ? (
                <div key={cat} style={{ fontSize: '0.8125rem' }}>
                  <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {cat.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}:
                  </span>{' '}
                  <span style={{ color: 'var(--color-text-secondary)' }}>{skills.join(', ')}</span>
                </div>
              ) : null
            )}
          </div>
        </div>
      )}

      {/* ATS Score */}
      {data.ats_score && (
        <div style={{
          marginTop: '1.5rem',
          padding: '1rem',
          background: 'rgba(139, 92, 246, 0.08)',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            background: `conic-gradient(var(--color-accent-violet) ${data.ats_score}%, transparent ${data.ats_score}%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              background: 'var(--color-bg-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.75rem',
              fontWeight: 700,
            }}>
              {data.ats_score}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>ATS Compatibility Score</div>
            {data.ats_notes && (
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>
                {data.ats_notes}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
