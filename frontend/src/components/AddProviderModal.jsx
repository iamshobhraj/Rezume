import { useState } from 'react';
import api from '../api/client';

const PROVIDER_DEFAULTS = {
  google: {
    base_url: '',
    chat_model: 'gemma-4-31b-it',
    embedding_model: 'gemini-embedding-2',
    embedding_dim: 768,
  },
  openai: {
    base_url: '',
    chat_model: 'gpt-4o',
    embedding_model: 'text-embedding-3-small',
    embedding_dim: 1536,
  },
  anthropic: {
    base_url: '',
    chat_model: 'claude-sonnet-4-20250514',
    embedding_model: '',
    embedding_dim: 0,
  },
  custom: {
    base_url: 'http://localhost:11434/v1',
    chat_model: '',
    embedding_model: '',
    embedding_dim: 768,
  },
};

const INITIAL_FORM = {
  name: '',
  provider_type: 'google',
  base_url: '',
  api_key: '',
  chat_model: 'gemma-4-31b-it',
  embedding_model: 'gemini-embedding-2',
  embedding_dim: 768,
};

export default function AddProviderModal({ onClose, onCreated, editProvider }) {
  const isEdit = !!editProvider;
  const [form, setForm] = useState(
    isEdit
      ? {
          name: editProvider.name,
          provider_type: editProvider.provider_type,
          base_url: editProvider.base_url || '',
          api_key: '',
          chat_model: editProvider.chat_model,
          embedding_model: editProvider.embedding_model,
          embedding_dim: editProvider.embedding_dim,
        }
      : { ...INITIAL_FORM }
  );
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [error, setError] = useState(null);

  const handleTypeChange = (type) => {
    const defaults = PROVIDER_DEFAULTS[type];
    setForm((prev) => ({
      ...prev,
      provider_type: type,
      ...defaults,
    }));
    setTestResult(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = { ...form, embedding_dim: parseInt(form.embedding_dim) };
      if (isEdit) {
        // For edit, only send changed fields; skip empty api_key
        const updatePayload = { ...payload };
        if (!updatePayload.api_key) delete updatePayload.api_key;
        await api.put(`/providers/${editProvider.id}`, updatePayload);
      } else {
        await api.post('/providers', payload);
      }
      onCreated();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save provider');
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    if (isEdit) {
      setTesting(true);
      setTestResult(null);
      try {
        const res = await api.post(`/providers/${editProvider.id}/test`);
        setTestResult(res.data);
      } catch (err) {
        setTestResult({ ok: false, message: err.response?.data?.detail || 'Test failed' });
      } finally {
        setTesting(false);
      }
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2 style={{ margin: '0 0 1.5rem', fontSize: '1.25rem', fontWeight: 700 }}>
          {isEdit ? 'Edit Provider' : 'Add Provider'}
        </h2>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Provider Type */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
              Provider Type
            </label>
            <select
              className="input-field"
              value={form.provider_type}
              onChange={(e) => handleTypeChange(e.target.value)}
              disabled={isEdit}
            >
              <option value="google">Google AI Studio</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="custom">Custom (OpenAI-compatible)</option>
            </select>
          </div>

          {/* Name */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
              Name
            </label>
            <input
              className="input-field"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g., My OpenAI Key"
              required
            />
          </div>

          {/* API Key */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
              API Key {isEdit && '(leave empty to keep current)'}
            </label>
            <input
              className="input-field"
              type="password"
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              placeholder="sk-..."
              required={!isEdit}
            />
          </div>

          {/* Base URL – show for custom and openai */}
          {(form.provider_type === 'custom' || form.provider_type === 'openai') && (
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Base URL {form.provider_type === 'openai' && '(leave empty for default)'}
              </label>
              <input
                className="input-field"
                value={form.base_url}
                onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                placeholder="http://localhost:11434/v1"
              />
            </div>
          )}

          {/* Chat Model */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
              Chat Model
            </label>
            <input
              className="input-field"
              value={form.chat_model}
              onChange={(e) => setForm({ ...form, chat_model: e.target.value })}
              placeholder="gpt-4o"
              required
            />
          </div>

          {/* Embedding Model */}
          <div>
            <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
              Embedding Model
              {form.provider_type === 'anthropic' && (
                <span style={{ color: 'var(--color-accent-rose)', marginLeft: '0.5rem' }}>
                  (Anthropic has no embeddings)
                </span>
              )}
            </label>
            <input
              className="input-field"
              value={form.embedding_model}
              onChange={(e) => setForm({ ...form, embedding_model: e.target.value })}
              placeholder="text-embedding-3-small"
              disabled={form.provider_type === 'anthropic'}
            />
          </div>

          {/* Embedding Dimension */}
          {form.provider_type !== 'anthropic' && (
            <div>
              <label style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                Embedding Dimension
              </label>
              <input
                className="input-field"
                type="number"
                value={form.embedding_dim}
                onChange={(e) => setForm({ ...form, embedding_dim: e.target.value })}
                min={1}
                max={10000}
              />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="alert-banner alert-error">
              <span>✕</span>
              <span>{error}</span>
            </div>
          )}

          {/* Test Result */}
          {testResult && (
            <div className={`alert-banner ${testResult.ok ? 'alert-success' : 'alert-error'}`}>
              <span>{testResult.ok ? '✓' : '✕'}</span>
              <span>{testResult.message}</span>
            </div>
          )}

          {/* Actions */}
          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem', justifyContent: 'flex-end' }}>
            {isEdit && (
              <button type="button" className="btn-secondary" onClick={handleTest} disabled={testing}>
                {testing ? <><span className="spinner" /> Testing...</> : '🔌 Test Connection'}
              </button>
            )}
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-gradient" disabled={loading}>
              {loading ? <><span className="spinner" /> Saving...</> : isEdit ? 'Update' : 'Add Provider'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
