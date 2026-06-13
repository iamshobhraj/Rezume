import { useState } from 'react';

const ENTRY_TYPES = [
  { value: 'work_experience', label: 'Work Experience' },
  { value: 'project', label: 'Personal Project' },
  { value: 'oss', label: 'Open Source' },
];

const INITIAL_FORM = {
  title: '',
  company: '',
  role: '',
  entry_type: 'project',
  start_date: '',
  end_date: '',
  raw_text: '',
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
          entry_type: editEntry.entry_type || editEntry.project_type || 'project',
          start_date: editEntry.start_date || '',
          end_date: editEntry.end_date || '',
          raw_text: editEntry.raw_text,
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
          {isEdit ? 'Edit Entry' : 'Add Work Entry'}
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
                placeholder="e.g., Stripe, Personal, Learning Equality"
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
                Entry Type
              </label>
              <select
                className="input-field"
                value={form.entry_type}
                onChange={(e) => setForm({ ...form, entry_type: e.target.value })}
              >
                {ENTRY_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Start Date
              </label>
              <input
                type="month"
                className="input-field"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                End Date
              </label>
              <input
                type="month"
                className="input-field"
                value={form.end_date === 'present' ? '' : form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value || '' })}
                disabled={form.end_date === 'present'}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: '0.25rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={form.end_date === 'present'}
                  onChange={(e) => setForm({ ...form, end_date: e.target.checked ? 'present' : '' })}
                  style={{ accentColor: 'var(--color-accent-violet)' }}
                />
                Current / Present
              </label>
            </div>
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
              style={{ maxWidth: '100px' }}
            />
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
              {loading ? <><span className="spinner" /> Saving...</> : isEdit ? 'Update Entry' : 'Add Entry'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
