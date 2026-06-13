import { useState } from 'react';
import api from '../api/client';

export default function ResumePreview({ content, resumeId }) {
  const [data, setData] = useState(() => {
    try {
      return typeof content === 'string' ? JSON.parse(content) : content;
    } catch (e) {
      return null;
    }
  });

  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState(null);
  const [recompiling, setRecompiling] = useState(false);

  if (!data) return <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>Invalid JSON format</div>;

  const handleEditClick = () => {
    setEditData(JSON.stringify(data, null, 2));
    setEditing(true);
  };

  const handleSaveEdit = () => {
    try {
      const parsed = JSON.parse(editData);
      setData(parsed);
      setEditing(false);
    } catch (e) {
      alert("Invalid JSON format");
    }
  };

  const handleRecompile = async () => {
    if (!resumeId) return;
    setRecompiling(true);
    try {
      // Send the updated JSON back to the backend to re-render the PDF
      await api.post(`/resumes/${resumeId}/recompile`, { resume_json: data });
      // Reload the page or fetch updated resume to get the new PDF link
      window.location.reload();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to recompile PDF");
    } finally {
      setRecompiling(false);
    }
  };

  if (editing) {
    return (
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0 }}>Edit JSON</h3>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn-secondary" onClick={() => setEditing(false)}>Cancel</button>
            <button className="btn-gradient" onClick={handleSaveEdit}>Apply Changes</button>
          </div>
        </div>
        <textarea
          style={{
            width: '100%',
            minHeight: '600px',
            fontFamily: 'monospace',
            fontSize: '12px',
            background: 'var(--color-bg-dark)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-border-glass)',
            borderRadius: '4px',
            padding: '1rem'
          }}
          value={editData}
          onChange={(e) => setEditData(e.target.value)}
        />
      </div>
    );
  }

  return (
    <div className="glass-panel" style={{ padding: '2rem', background: '#fff', color: '#111', fontFamily: '"Times New Roman", Times, serif' }}>
      
      {/* Editor Controls Overlay */}
      <div style={{ position: 'absolute', top: '1rem', right: '1rem', display: 'flex', gap: '0.5rem' }}>
        <button 
          className="btn-secondary" 
          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', background: 'var(--color-bg-dark)', color: 'var(--color-text-primary)' }}
          onClick={handleEditClick}
        >
          ✏️ Edit JSON
        </button>
        {resumeId && (
          <button 
            className="btn-gradient" 
            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
            onClick={handleRecompile}
            disabled={recompiling}
          >
            {recompiling ? 'Compiling...' : '🔄 Re-compile PDF'}
          </button>
        )}
      </div>

      <div style={{ textAlign: 'center', marginBottom: '1.5rem', marginTop: '1rem' }}>
        <h1 style={{ margin: '0 0 0.5rem', fontSize: '1.8rem', color: '#000' }}>{data.name}</h1>
        <div style={{ fontSize: '0.9rem', display: 'flex', justifyContent: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span>{data.email}</span>
          {data.phone && <span>| {data.phone}</span>}
          {data.github && <span>| {data.github}</span>}
          {data.linkedin && <span>| {data.linkedin}</span>}
          {data.location && <span>| {data.location}</span>}
        </div>
      </div>

      {data.education && data.education.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.1rem', margin: '0 0 0.5rem', borderBottom: '1px solid #000', textTransform: 'uppercase' }}>
            Education
          </h2>
          {data.education.map((edu, idx) => (
            <div key={idx} style={{ marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 'bold' }}>{edu.institution}</span>
                <span>{edu.year}</span>
              </div>
              <div>{edu.degree}</div>
              {edu.coursework && <div style={{ fontSize: '0.9rem', fontStyle: 'italic', marginTop: '0.25rem' }}>Coursework: {edu.coursework}</div>}
            </div>
          ))}
        </div>
      )}

      {data.skills && Object.keys(data.skills).length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.1rem', margin: '0 0 0.5rem', borderBottom: '1px solid #000', textTransform: 'uppercase' }}>
            Technical Skills
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '0.25rem 0.5rem' }}>
            {Object.entries(data.skills).map(([category, items]) => {
              if (!items || items.length === 0) return null;
              return (
                <div key={category} style={{ display: 'contents' }}>
                  <span style={{ fontWeight: 'bold', textTransform: 'capitalize' }}>{category.replace('_', ' ')}:</span>
                  <span>{items.join(', ')}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {data.experience && data.experience.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.1rem', margin: '0 0 0.5rem', borderBottom: '1px solid #000', textTransform: 'uppercase' }}>
            Experience
          </h2>
          {data.experience.map((exp, idx) => (
            <div key={idx} style={{ marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>
                  <span style={{ fontWeight: 'bold' }}>{exp.title}</span> — {exp.company}
                </span>
                <span style={{ fontStyle: 'italic' }}>{exp.date_range}</span>
              </div>
              {exp.subtitle && <div style={{ fontStyle: 'italic', fontSize: '0.9rem' }}>{exp.subtitle}</div>}
              <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.5rem' }}>
                {exp.bullets?.map((b, i) => (
                  <li key={i} style={{ marginBottom: '0.25rem' }} dangerouslySetInnerHTML={{
                    __html: b.replace(/\\textbf{([^}]+)}/g, '<strong>$1</strong>')
                             .replace(/\\href{([^}]+)}{([^}]+)}/g, '<a href="$1" target="_blank">$2</a>')
                             .replace(/\\([#$%\&_])/g, '$1')
                  }} />
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {data.open_source && data.open_source.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.1rem', margin: '0 0 0.5rem', borderBottom: '1px solid #000', textTransform: 'uppercase' }}>
            Open Source
          </h2>
          {data.open_source.map((oss, idx) => (
            <div key={idx} style={{ marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>
                  <span style={{ fontWeight: 'bold' }}>{oss.role}</span> — {oss.org_display}
                </span>
                <span style={{ fontStyle: 'italic' }}>{oss.duration}</span>
              </div>
              <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.5rem' }}>
                {oss.contributions?.map((c, i) => (
                  <li key={i} style={{ marginBottom: '0.25rem' }} dangerouslySetInnerHTML={{
                    __html: c.replace(/\\textbf{([^}]+)}/g, '<strong>$1</strong>')
                             .replace(/\\href{([^}]+)}{([^}]+)}/g, '<a href="$1" target="_blank">$2</a>')
                             .replace(/\\([#$%\&_])/g, '$1')
                  }} />
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {data.projects && data.projects.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.1rem', margin: '0 0 0.5rem', borderBottom: '1px solid #000', textTransform: 'uppercase' }}>
            Projects
          </h2>
          {data.projects.map((proj, idx) => (
            <div key={idx} style={{ marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 'bold' }}>{proj.title}</span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {proj.github_url && <a href={proj.github_url} style={{ color: '#000' }}>GitHub</a>}
                </div>
              </div>
              {proj.technologies && (
                <div style={{ fontStyle: 'italic', fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                  {proj.technologies}
                </div>
              )}
              <ul style={{ margin: '0', paddingLeft: '1.5rem' }}>
                {proj.bullets?.map((b, i) => (
                  <li key={i} style={{ marginBottom: '0.25rem' }} dangerouslySetInnerHTML={{
                    __html: b.replace(/\\textbf{([^}]+)}/g, '<strong>$1</strong>')
                             .replace(/\\href{([^}]+)}{([^}]+)}/g, '<a href="$1" target="_blank">$2</a>')
                             .replace(/\\([#$%\&_])/g, '$1')
                  }} />
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
      
      {/* ATS Details Section - ONLY visible in UI, not in PDF */}
      {(data.ats_matched || data.ats_missing) && (
        <div style={{ marginTop: '3rem', paddingTop: '1rem', borderTop: '1px dashed #ccc', color: '#666', fontFamily: 'system-ui' }}>
          <h3 style={{ fontSize: '1rem', marginTop: 0, color: '#333' }}>ATS Keyword Analysis</h3>
          
          {data.ats_matched && data.ats_matched.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>✅ Matched Keywords</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                {data.ats_matched.map((kw, i) => (
                  <span key={i} style={{ background: '#ecfdf5', color: '#065f46', padding: '2px 6px', borderRadius: '4px', fontSize: '0.75rem', border: '1px solid #a7f3d0' }}>
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {data.ats_missing && data.ats_missing.length > 0 && (
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>❌ Missing High-Priority Keywords</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                {data.ats_missing.map((kw, i) => (
                  <span key={i} style={{ background: '#fef2f2', color: '#991b1b', padding: '2px 6px', borderRadius: '4px', fontSize: '0.75rem', border: '1px solid #fecaca' }}>
                    {kw}
                  </span>
                ))}
              </div>
              <div style={{ fontSize: '0.75rem', marginTop: '0.5rem', fontStyle: 'italic' }}>
                Consider using the "Edit JSON" button to naturally incorporate these keywords into your bullets or skills.
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
