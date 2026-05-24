import { useState } from 'react';

const INITIAL_FORM = {
  title: '',
  company: '',
  role: '',
  date_range: '',
  raw_text: '',
  project_type: 'personal',
  priority: 3,
  github_url: '',
};

export default function ProjectForm({ onSubmit, onCancel, editEntry }) {
  const isEdit = !!editEntry;
  const [form, setForm] = useState(
    isEdit
      ? {
          title: editEntry.title,
          company: editEntry.company || '',
          role: editEntry.role || '',
          date_range: editEntry.date_range || '',
          raw_text: editEntry.raw_text,
          project_type: editEntry.project_type || 'personal',
          priority: editEntry.priority || 3,
          github_url: editEntry.github_url || '',
        }
      : { ...INITIAL_FORM }
  );
  const [loading, setLoading] = useState(false);
  const [digestLoading, setDigestLoading] = useState(false);
  const [digestError, setDigestError] = useState('');

  const handleAutoDigest = async () => {
    if (!form.github_url.trim()) return;
    setDigestLoading(true);
    setDigestError('');
    try {
      const response = await fetch('/api/projects/digest-repo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ github_url: form.github_url }),
      });
      
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to digest repository');
      }
      
      const data = await response.json();
      if (data.success) {
        setForm(prev => ({
          ...prev,
          raw_text: data.full_text,
          title: prev.title ? prev.title : `Repo: ${data.repo_name}`,
          company: prev.company ? prev.company : data.repo_name,
        }));
      }
    } catch (err) {
      setDigestError(err.message || 'Failed to digest repository');
    } finally {
      setDigestLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSubmit(form, editEntry?.id);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '640px' }}>
        <h2 style={{ margin: '0 0 1.5rem', fontSize: '1.25rem', fontWeight: 700 }}>
          {isEdit ? 'Edit Project' : 'Add Project'}
        </h2>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Title *
              </label>
              <input
                className="input-field"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="e.g., Payment Service Migration"
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Company / Context
              </label>
              <input
                className="input-field"
                value={form.company}
                onChange={(e) => setForm({ ...form, company: e.target.value })}
                placeholder="e.g., Stripe, Personal, Open Source"
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Role
              </label>
              <input
                className="input-field"
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                placeholder="e.g., Senior Backend Engineer"
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Date Range
              </label>
              <input
                className="input-field"
                value={form.date_range}
                onChange={(e) => setForm({ ...form, date_range: e.target.value })}
                placeholder="e.g., Jan 2023 - Mar 2024"
              />
            </div>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Project Type
              </label>
              <select
                className="input-field"
                value={form.project_type}
                onChange={(e) => setForm({ ...form, project_type: e.target.value })}
              >
                <option value="personal">Personal / Work</option>
                <option value="oss">Open Source</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Priority (1-5)
              </label>
              <input
                type="number"
                min="1"
                max="5"
                className="input-field"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value) || 3 })}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
              GitHub URL
            </label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                className="input-field"
                value={form.github_url}
                onChange={(e) => setForm({ ...form, github_url: e.target.value })}
                placeholder="https://github.com/username/repo"
                style={{ flex: 1 }}
              />
              <button
                type="button"
                className="btn-secondary"
                onClick={handleAutoDigest}
                disabled={digestLoading || !form.github_url.trim()}
                style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', whiteSpace: 'nowrap', padding: '0.5rem 1rem' }}
              >
                {digestLoading ? '⚡ Digesting...' : '⚡ Auto-Digest'}
              </button>
            </div>
            {digestError && (
              <p style={{ color: 'var(--color-danger, #ef4444)', fontSize: '0.75rem', margin: '0.25rem 0 0' }}>
                {digestError}
              </p>
            )}
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.375rem' }}>
              <label style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Description / Gitingest File *
              </label>
              <div>
                <input
                  type="file"
                  id="gitingest-upload"
                  accept=".txt"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const file = e.target.files[0];
                    if (!file) return;
                    const reader = new FileReader();
                    reader.onload = (event) => {
                      setForm(prev => ({ 
                        ...prev, 
                        raw_text: prev.raw_text ? prev.raw_text + '\n\n' + event.target.result : event.target.result 
                      }));
                    };
                    reader.readAsText(file);
                    e.target.value = ''; // Reset input
                  }}
                />
                <button 
                  type="button" 
                  className="btn-secondary" 
                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                  onClick={() => document.getElementById('gitingest-upload').click()}
                >
                  📄 Upload .txt
                </button>
              </div>
            </div>
            <textarea
              className="input-field"
              value={form.raw_text}
              onChange={(e) => setForm({ ...form, raw_text: e.target.value })}
              placeholder="Describe the work you did, OR upload a gitingest .txt file of your codebase..."
              style={{ minHeight: '200px' }}
              required
            />
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button type="button" className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn-gradient" disabled={loading}>
              {loading ? <><span className="spinner" /> Saving...</> : isEdit ? 'Update Project' : 'Add Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
