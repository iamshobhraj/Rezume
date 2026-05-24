import { useState, useEffect } from 'react';
import api from '../api/client';
import ResumePreview from '../components/ResumePreview';

export default function GenerateResume() {
  const [jd, setJd] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get('/resumes').then((res) => setHistory(res.data)).catch(() => {});
  }, []);

  const handleGenerate = async () => {
    if (jd.trim().length < 10) {
      setError('Please enter a job description (at least 10 characters)');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.post('/resumes/generate', { job_description: jd });
      setResult(res.data);
      // Refresh history
      const histRes = await api.get('/resumes');
      setHistory(histRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Generation failed. Make sure you have an active chat and embedding provider.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in-up">
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
          <span className="gradient-text">Generate Resume</span>
        </h1>
        <p style={{ margin: '0.375rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9375rem' }}>
          Paste a job description and generate a tailored, ATS-optimized resume
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
        {/* Left: Input */}
        <div>
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '0.9375rem', fontWeight: 700 }}>Job Description</h3>
            <textarea
              className="input-field"
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the full job description here..."
              style={{ minHeight: '300px', marginBottom: '1rem' }}
            />
            <button
              className="btn-gradient"
              onClick={handleGenerate}
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              {loading ? (
                <>
                  <span className="spinner" />
                  Generating... This may take a moment
                </>
              ) : (
                '✦ Generate Resume'
              )}
            </button>
          </div>

          {/* History */}
          {history.length > 0 && (
            <div style={{ marginTop: '1.5rem' }}>
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, marginBottom: '0.75rem' }}>Recent Generations</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {history.slice(0, 5).map((r) => (
                  <div key={r.id} className="glass-panel" style={{ padding: '0.875rem', cursor: 'pointer' }} onClick={async () => {
                    const res = await api.get(`/resumes/${r.id}`);
                    setResult(res.data);
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                        {r.job_description_preview.substring(0, 80)}...
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        {r.score && <span className="badge badge-violet">ATS: {r.score}</span>}
                        {r.has_pdf && <span className="badge badge-emerald">PDF</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Preview */}
        <div>
          {error && (
            <div className="alert-banner alert-error" style={{ marginBottom: '1rem' }}>
              <span>✕</span>
              <span>{error}</span>
            </div>
          )}
          {loading && (
            <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
              <span className="spinner" style={{ width: '40px', height: '40px', margin: '0 auto 1rem' }} />
              <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.9375rem' }}>
                Analyzing JD, retrieving relevant experience, generating resume...
              </div>
            </div>
          )}
          {result && !loading && (
            <>
              <ResumePreview content={result.generated_content} />
              {result.pdf_path && (
                <div style={{ marginTop: '1rem' }}>
                  <a href={`/api/resumes/${result.id}/pdf`} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>
                    <button className="btn-gradient" style={{ width: '100%', justifyContent: 'center' }}>
                      📄 Download PDF
                    </button>
                  </a>
                </div>
              )}
            </>
          )}
          {!result && !loading && !error && (
            <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem', opacity: 0.3 }}>✦</div>
              <div style={{ color: 'var(--color-text-muted)', fontSize: '0.9375rem' }}>
                Enter a job description and click Generate to create a tailored resume
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
