import { useState } from 'react';
import api from '../api/client';

export default function ProviderTable({ providers, onRefresh, onEdit }) {
  const [testingId, setTestingId] = useState(null);
  const [testResult, setTestResult] = useState({});
  const [deletingId, setDeletingId] = useState(null);

  const handleTest = async (id) => {
    setTestingId(id);
    try {
      const res = await api.post(`/providers/${id}/test`);
      setTestResult((prev) => ({ ...prev, [id]: res.data }));
    } catch (err) {
      setTestResult((prev) => ({
        ...prev,
        [id]: { ok: false, message: err.response?.data?.detail || 'Test failed' },
      }));
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (id, name) => {
    if (!confirm(`Delete provider "${name}"?`)) return;
    setDeletingId(id);
    try {
      await api.delete(`/providers/${id}`);
      onRefresh();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete');
    } finally {
      setDeletingId(null);
    }
  };

  const handleActivate = async (id, type) => {
    try {
      await api.put(`/providers/${id}/activate`, {
        set_active_chat: type === 'chat' || type === 'both',
        set_active_embedding: type === 'embedding' || type === 'both',
      });
      onRefresh();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to activate');
    }
  };

  if (providers.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '3rem',
        color: 'var(--color-text-muted)',
      }}>
        <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>⬡</div>
        <div style={{ fontSize: '0.9375rem' }}>No providers configured yet</div>
        <div style={{ fontSize: '0.8125rem', marginTop: '0.375rem' }}>
          Add your first AI provider to get started
        </div>
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Chat Model</th>
            <th>Embedding Model</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {providers.map((p) => (
            <tr key={p.id}>
              <td style={{ fontWeight: 600 }}>{p.name}</td>
              <td>
                <span className="badge badge-violet">{p.provider_type}</span>
              </td>
              <td style={{ fontFamily: 'monospace', fontSize: '0.8125rem' }}>{p.chat_model}</td>
              <td style={{ fontFamily: 'monospace', fontSize: '0.8125rem' }}>
                {p.embedding_model || <span style={{ color: 'var(--color-text-muted)' }}>—</span>}
              </td>
              <td>
                <div style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap' }}>
                  {p.is_active_chat && <span className="badge badge-cyan">Chat ✓</span>}
                  {p.is_active_embedding && <span className="badge badge-emerald">Embedding ✓</span>}
                  {!p.is_active_chat && !p.is_active_embedding && (
                    <span className="badge" style={{ opacity: 0.5 }}>Inactive</span>
                  )}
                </div>
              </td>
              <td>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button
                    className="btn-secondary"
                    style={{ padding: '0.375rem 0.625rem', fontSize: '0.75rem' }}
                    onClick={() => handleTest(p.id)}
                    disabled={testingId === p.id}
                  >
                    {testingId === p.id ? <span className="spinner" /> : '🔌 Test'}
                  </button>
                  {!p.is_active_chat && (
                    <button
                      className="btn-secondary"
                      style={{ padding: '0.375rem 0.625rem', fontSize: '0.75rem' }}
                      onClick={() => handleActivate(p.id, 'chat')}
                    >
                      Set Chat
                    </button>
                  )}
                  {!p.is_active_embedding && p.provider_type !== 'anthropic' && (
                    <button
                      className="btn-secondary"
                      style={{ padding: '0.375rem 0.625rem', fontSize: '0.75rem' }}
                      onClick={() => handleActivate(p.id, 'embedding')}
                    >
                      Set Embed
                    </button>
                  )}
                  <button
                    className="btn-secondary"
                    style={{ padding: '0.375rem 0.625rem', fontSize: '0.75rem' }}
                    onClick={() => onEdit(p)}
                  >
                    ✎ Edit
                  </button>
                  <button
                    className="btn-danger"
                    style={{ padding: '0.375rem 0.625rem', fontSize: '0.75rem' }}
                    onClick={() => handleDelete(p.id, p.name)}
                    disabled={deletingId === p.id}
                  >
                    ✕
                  </button>
                </div>

                {/* Test result inline */}
                {testResult[p.id] && (
                  <div
                    style={{
                      marginTop: '0.5rem',
                      fontSize: '0.75rem',
                      color: testResult[p.id].ok ? 'var(--color-accent-emerald)' : 'var(--color-accent-rose)',
                    }}
                  >
                    {testResult[p.id].ok ? '✓ ' : '✕ '}
                    {testResult[p.id].message}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
