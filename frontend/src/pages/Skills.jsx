import { useState, useEffect } from 'react';
import api from '../api/client';

const CATEGORIES = [
  { value: 'language', label: 'Language', color: '#818cf8' },
  { value: 'framework', label: 'Framework', color: '#34d399' },
  { value: 'tool', label: 'Tool', color: '#fbbf24' },
  { value: 'infra', label: 'Infrastructure', color: '#f87171' },
  { value: 'concept', label: 'Concept', color: '#a78bfa' },
];

const PROFICIENCY_LEVELS = [
  { value: 'familiar', label: 'Familiar', icon: '○' },
  { value: 'proficient', label: 'Proficient', icon: '◐' },
  { value: 'expert', label: 'Expert', icon: '●' },
];

const CATEGORY_MAP = Object.fromEntries(CATEGORIES.map(c => [c.value, c]));

export default function Skills() {
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editSkill, setEditSkill] = useState(null);
  const [bulkText, setBulkText] = useState('');
  const [bulkCategory, setBulkCategory] = useState('language');
  const [showBulk, setShowBulk] = useState(false);
  const [form, setForm] = useState({ skill_name: '', category: 'language', proficiency: 'proficient' });

  const fetchSkills = async () => {
    try {
      const res = await api.get('/skills');
      setSkills(res.data);
    } catch (err) {
      console.error('Failed to fetch skills:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSkills(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editSkill) {
        await api.put(`/skills/${editSkill.id}`, form);
      } else {
        await api.post('/skills', form);
      }
      setShowForm(false);
      setEditSkill(null);
      setForm({ skill_name: '', category: 'language', proficiency: 'proficient' });
      fetchSkills();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to save skill');
    }
  };

  const handleDelete = async (id, name) => {
    if (!confirm(`Remove "${name}" from your skills?`)) return;
    try {
      await api.delete(`/skills/${id}`);
      fetchSkills();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete');
    }
  };

  const handleBulkAdd = async () => {
    const names = bulkText.split(',').map(s => s.trim()).filter(Boolean);
    if (names.length === 0) return;
    try {
      await api.post('/skills/bulk', names.map(name => ({
        skill_name: name,
        category: bulkCategory,
        proficiency: 'proficient',
      })));
      setBulkText('');
      setShowBulk(false);
      fetchSkills();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to bulk add skills');
    }
  };

  // Group skills by category
  const grouped = {};
  CATEGORIES.forEach(c => { grouped[c.value] = []; });
  skills.forEach(s => {
    if (grouped[s.category]) {
      grouped[s.category].push(s);
    } else {
      grouped[s.category] = [s];
    }
  });

  return (
    <div className="animate-fade-in-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
            <span className="gradient-text">Skills Inventory</span>
          </h1>
          <p style={{ margin: '0.375rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9375rem' }}>
            Your authoritative skill list — feeds directly into resume generation and ATS optimization
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn-secondary" onClick={() => setShowBulk(!showBulk)}>
            ⚡ Bulk Add
          </button>
          <button className="btn-gradient" onClick={() => { setEditSkill(null); setForm({ skill_name: '', category: 'language', proficiency: 'proficient' }); setShowForm(true); }}>
            + Add Skill
          </button>
        </div>
      </div>

      {/* Bulk Add */}
      {showBulk && (
        <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
          <h3 style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', fontWeight: 700 }}>Bulk Add Skills</h3>
          <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', margin: '0 0 0.75rem' }}>
            Enter comma-separated skill names. All will be added to the selected category.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <input
                className="input-field"
                value={bulkText}
                onChange={(e) => setBulkText(e.target.value)}
                placeholder="Python, JavaScript, TypeScript, Go, Rust"
              />
            </div>
            <select
              className="input-field"
              value={bulkCategory}
              onChange={(e) => setBulkCategory(e.target.value)}
              style={{ width: '160px' }}
            >
              {CATEGORIES.map(c => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
            <button className="btn-gradient" onClick={handleBulkAdd} disabled={!bulkText.trim()}>
              Add All
            </button>
          </div>
        </div>
      )}

      {/* Skills Grid by Category */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <span className="spinner" style={{ width: '32px', height: '32px' }} />
        </div>
      ) : skills.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>⚡</div>
          <div style={{ fontSize: '0.9375rem', color: 'var(--color-text-muted)' }}>
            No skills yet. Add your technical skills to improve resume generation.
          </div>
          <button className="btn-gradient" style={{ marginTop: '1rem' }} onClick={() => setShowForm(true)}>
            + Add Your First Skill
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {CATEGORIES.map(cat => {
            const catSkills = grouped[cat.value] || [];
            if (catSkills.length === 0) return null;
            return (
              <div key={cat.value} className="glass-panel" style={{ padding: '1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                  <div style={{
                    width: '8px', height: '8px', borderRadius: '50%',
                    background: cat.color,
                  }} />
                  <span style={{ fontSize: '0.875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {cat.label}s
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>({catSkills.length})</span>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {catSkills.map(skill => {
                    const prof = PROFICIENCY_LEVELS.find(p => p.value === skill.proficiency) || PROFICIENCY_LEVELS[1];
                    return (
                      <div
                        key={skill.id}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '0.375rem',
                          padding: '0.375rem 0.75rem', borderRadius: '8px',
                          background: `${cat.color}15`, border: `1px solid ${cat.color}30`,
                          fontSize: '0.8125rem', cursor: 'pointer', transition: 'all 0.2s',
                        }}
                        onClick={() => { setEditSkill(skill); setForm({ skill_name: skill.skill_name, category: skill.category, proficiency: skill.proficiency }); setShowForm(true); }}
                        title={`${prof.label} – click to edit`}
                      >
                        <span style={{ fontSize: '0.625rem', opacity: 0.7 }}>{prof.icon}</span>
                        <span>{skill.skill_name}</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(skill.id, skill.skill_name); }}
                          style={{
                            background: 'none', border: 'none', color: 'var(--color-text-muted)',
                            cursor: 'pointer', padding: '0 0.125rem', fontSize: '0.75rem',
                            opacity: 0.5, transition: 'opacity 0.2s',
                          }}
                          onMouseEnter={(e) => e.target.style.opacity = 1}
                          onMouseLeave={(e) => e.target.style.opacity = 0.5}
                        >
                          ✕
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Stats */}
      {skills.length > 0 && (
        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
          <div className="glass-panel" style={{ padding: '1rem', flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{skills.length}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Total Skills</div>
          </div>
          {CATEGORIES.map(cat => {
            const count = (grouped[cat.value] || []).length;
            if (count === 0) return null;
            return (
              <div key={cat.value} className="glass-panel" style={{ padding: '1rem', flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: cat.color }}>{count}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{cat.label}s</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add/Edit Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => { setShowForm(false); setEditSkill(null); }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '440px' }}>
            <h2 style={{ margin: '0 0 1.25rem', fontSize: '1.125rem', fontWeight: 700 }}>
              {editSkill ? 'Edit Skill' : 'Add Skill'}
            </h2>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  Skill Name *
                </label>
                <input
                  className="input-field"
                  value={form.skill_name}
                  onChange={(e) => setForm({ ...form, skill_name: e.target.value })}
                  placeholder="e.g., Python, Docker, System Design"
                  required
                  autoFocus
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                    Category
                  </label>
                  <select
                    className="input-field"
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                  >
                    {CATEGORIES.map(c => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                    Proficiency
                  </label>
                  <select
                    className="input-field"
                    value={form.proficiency}
                    onChange={(e) => setForm({ ...form, proficiency: e.target.value })}
                  >
                    {PROFICIENCY_LEVELS.map(p => (
                      <option key={p.value} value={p.value}>{p.icon} {p.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button type="button" className="btn-secondary" onClick={() => { setShowForm(false); setEditSkill(null); }}>
                  Cancel
                </button>
                <button type="submit" className="btn-gradient">
                  {editSkill ? 'Update Skill' : 'Add Skill'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
