import { useState } from 'react';
import api from '../api/client';

export default function OssFetcher({ onFetched }) {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleFetch = async (e) => {
    e.preventDefault();
    if (!username.trim()) return;
    
    setLoading(true);
    setResult(null);
    try {
      const res = await api.post('/github/fetch-oss', { username: username.trim() });
      setResult({ type: 'success', message: res.data.message });
      if (res.data.created_count > 0 && onFetched) {
        onFetched();
      }
    } catch (err) {
      console.error(err);
      setResult({ type: 'error', message: err.response?.data?.error || 'Failed to fetch GitHub PRs' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1.5rem', borderLeft: '4px solid var(--color-accent-violet)' }}>
      <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem', fontWeight: 600 }}>Sync Open Source Contributions</h3>
      <p style={{ margin: '0 0 1rem', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
        Automatically fetch your merged public Pull Requests from GitHub and ingest them as OSS Projects.
      </p>
      
      <form onSubmit={handleFetch} style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <input
          className="input-field"
          placeholder="GitHub Username (e.g. torvalds)"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{ maxWidth: '300px', margin: 0 }}
          required
        />
        <button type="submit" className="btn-gradient" disabled={loading || !username.trim()}>
          {loading ? <><span className="spinner" /> Syncing...</> : 'Fetch PRs'}
        </button>
      </form>
      
      {result && (
        <div style={{ 
          marginTop: '0.75rem', 
          padding: '0.5rem 0.75rem', 
          borderRadius: '6px', 
          fontSize: '0.875rem',
          background: result.type === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          color: result.type === 'success' ? '#34d399' : '#f87171'
        }}>
          {result.message}
        </div>
      )}
    </div>
  );
}
