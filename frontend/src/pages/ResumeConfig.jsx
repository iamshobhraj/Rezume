import { useState, useEffect } from 'react';
import api from '../api/client';
import { useProviders } from '../hooks/useProviders';
import StatusBanner from '../components/StatusBanner';

export default function ResumeConfig() {
  const { providers } = useProviders();
  const [config, setConfig] = useState({
    target_role: '',
    years_experience: 5,
    skills_emphasis: [],
    tone: 'professional',
    active_chat_provider_id: '',
    active_embedding_provider_id: '',
  });
  const [skillInput, setSkillInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    api.get('/config')
      .then((res) => setConfig(res.data))
      .catch((err) => console.error('Failed to load config:', err))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await api.put('/config', config);
      setConfig(res.data);
      setMessage({ type: 'success', text: 'Configuration saved successfully' });
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to save' });
    } finally {
      setSaving(false);
    }
  };

  const addSkill = () => {
    const skill = skillInput.trim();
    if (skill && !config.skills_emphasis.includes(skill)) {
      setConfig({ ...config, skills_emphasis: [...config.skills_emphasis, skill] });
      setSkillInput('');
    }
  };

  const removeSkill = (skill) => {
    setConfig({ ...config, skills_emphasis: config.skills_emphasis.filter((s) => s !== skill) });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem' }}>
        <span className="spinner" style={{ width: '32px', height: '32px' }} />
      </div>
    );
  }

  const chatProviders = providers;
  const embeddingProviders = providers.filter((p) => p.provider_type !== 'anthropic');

  return (
    <div className="animate-fade-in-up">
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
          <span className="gradient-text">Resume Configuration</span>
        </h1>
        <p style={{ margin: '0.375rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9375rem' }}>
          Configure your resume generation preferences and active AI providers
        </p>
      </div>

      {message && (
        <StatusBanner
          type={message.type}
          message={message.text}
          onDismiss={() => setMessage(null)}
        />
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Resume Preferences */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1.25rem', fontSize: '0.9375rem', fontWeight: 700 }}>Resume Preferences</h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Target Role
              </label>
              <input
                className="input-field"
                value={config.target_role}
                onChange={(e) => setConfig({ ...config, target_role: e.target.value })}
                placeholder="e.g., Senior Software Engineer"
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Years of Experience
              </label>
              <input
                className="input-field"
                type="number"
                value={config.years_experience}
                onChange={(e) => setConfig({ ...config, years_experience: parseInt(e.target.value) || 0 })}
                min={0}
                max={50}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Tone
              </label>
              <select
                className="input-field"
                value={config.tone}
                onChange={(e) => setConfig({ ...config, tone: e.target.value })}
              >
                <option value="professional">Professional</option>
                <option value="concise">Concise</option>
                <option value="detailed">Detailed</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Skills Emphasis
              </label>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <input
                  className="input-field"
                  value={skillInput}
                  onChange={(e) => setSkillInput(e.target.value)}
                  placeholder="Add a skill..."
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSkill())}
                />
                <button className="btn-secondary" onClick={addSkill} type="button">+</button>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                {config.skills_emphasis.map((skill) => (
                  <span key={skill} className="badge badge-violet" style={{ cursor: 'pointer' }} onClick={() => removeSkill(skill)}>
                    {skill} ×
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Provider Selection */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1.25rem', fontSize: '0.9375rem', fontWeight: 700 }}>Active AI Providers</h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Chat Provider (for resume generation)
              </label>
              <select
                className="input-field"
                value={config.active_chat_provider_id || ''}
                onChange={(e) => setConfig({ ...config, active_chat_provider_id: e.target.value || null })}
              >
                <option value="">— Select —</option>
                {chatProviders.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.chat_model})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Embedding Provider (for vector search)
              </label>
              <select
                className="input-field"
                value={config.active_embedding_provider_id || ''}
                onChange={(e) => setConfig({ ...config, active_embedding_provider_id: e.target.value || null })}
              >
                <option value="">— Select —</option>
                {embeddingProviders.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.embedding_model}, {p.embedding_dim}d)
                  </option>
                ))}
              </select>
            </div>

            {providers.length === 0 && (
              <div className="alert-banner alert-warning">
                <span>⚠</span>
                <span>No providers configured. Go to AI Providers page to add one.</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Save */}
      <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
        <button className="btn-gradient" onClick={handleSave} disabled={saving}>
          {saving ? <><span className="spinner" /> Saving...</> : 'Save Configuration'}
        </button>
      </div>
    </div>
  );
}
