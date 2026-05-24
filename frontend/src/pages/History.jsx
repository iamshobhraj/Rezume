import { useState, useEffect } from 'react';
import api from '../api/client';

export default function History() {
  const [historyList, setHistoryList] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [selected1, setSelected1] = useState('');
  const [selected2, setSelected2] = useState('');
  const [diffResult, setDiffResult] = useState(null);
  const [diffLoading, setDiffLoading] = useState(false);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await api.get('/history');
      setHistoryList(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!selected1 || !selected2) return;
    setDiffLoading(true);
    try {
      const res = await api.get(`/history/diff/${selected1}/${selected2}`);
      setDiffResult(res.data);
    } catch (err) {
      console.error(err);
      alert('Failed to compute diff');
    } finally {
      setDiffLoading(false);
    }
  };

  return (
    <div className="animate-fade-in-up">
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
          <span className="gradient-text">Resume History & Diff</span>
        </h1>
        <p style={{ margin: '0.375rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9375rem' }}>
          Compare previously generated resumes side-by-side
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '1rem', alignItems: 'end' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Older Resume (Left)</label>
            <select className="input-field" value={selected1} onChange={e => setSelected1(e.target.value)}>
              <option value="">Select a resume...</option>
              {historyList.map(h => (
                <option key={h.id} value={h.id}>
                  {new Date(h.created_at).toLocaleString()} - {h.tags} ({h.generated_resume_id.substring(0, 8)})
                </option>
              ))}
            </select>
          </div>
          
          <button 
            className="btn-gradient" 
            onClick={handleCompare} 
            disabled={!selected1 || !selected2 || selected1 === selected2 || diffLoading}
            style={{ marginBottom: '2px' }}
          >
            {diffLoading ? 'Computing...' : 'Compare'}
          </button>
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Newer Resume (Right)</label>
            <select className="input-field" value={selected2} onChange={e => setSelected2(e.target.value)}>
              <option value="">Select a resume...</option>
              {historyList.map(h => (
                <option key={h.id} value={h.id}>
                  {new Date(h.created_at).toLocaleString()} - {h.tags} ({h.generated_resume_id.substring(0, 8)})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {diffResult && (
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>JSON Difference (DeepDiff)</h3>
          <pre style={{ 
            background: 'rgba(0,0,0,0.3)', 
            padding: '1rem', 
            borderRadius: '8px', 
            overflowX: 'auto',
            fontSize: '0.8125rem',
            color: 'var(--color-text-secondary)'
          }}>
            {JSON.stringify(diffResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
