import { useState } from 'react';
import { useProviders } from '../hooks/useProviders';
import ProviderTable from '../components/ProviderTable';
import AddProviderModal from '../components/AddProviderModal';

export default function ProvidersSettings() {
  const { providers, loading, refetch } = useProviders();
  const [showModal, setShowModal] = useState(false);
  const [editProvider, setEditProvider] = useState(null);

  const handleEdit = (provider) => {
    setEditProvider(provider);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditProvider(null);
  };

  return (
    <div className="animate-fade-in-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
            <span className="gradient-text">AI Providers</span>
          </h1>
          <p style={{ margin: '0.375rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9375rem' }}>
            Configure LLM and embedding providers (Google, OpenAI, Anthropic, Ollama, etc.)
          </p>
        </div>
        <button className="btn-gradient" onClick={() => { setEditProvider(null); setShowModal(true); }}>
          + Add Provider
        </button>
      </div>

      {/* Info banner */}
      <div className="alert-banner" style={{
        background: 'rgba(139, 92, 246, 0.06)',
        border: '1px solid rgba(139, 92, 246, 0.15)',
        color: 'var(--color-text-secondary)',
        marginBottom: '1.5rem',
      }}>
        <span style={{ fontSize: '1rem' }}>💡</span>
        <div style={{ fontSize: '0.8125rem' }}>
          Each provider can be set as the active <strong>chat</strong> (for resume generation) and/or <strong>embedding</strong> (for vector search) provider.
          Anthropic does not support embeddings — pair it with Google or OpenAI for embedding.
        </div>
      </div>

      {/* Provider Table */}
      <div className="glass-panel" style={{ padding: '0.5rem' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>
            <span className="spinner" style={{ width: '32px', height: '32px' }} />
          </div>
        ) : (
          <ProviderTable providers={providers} onRefresh={refetch} onEdit={handleEdit} />
        )}
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <AddProviderModal
          onClose={handleCloseModal}
          onCreated={refetch}
          editProvider={editProvider}
        />
      )}
    </div>
  );
}
