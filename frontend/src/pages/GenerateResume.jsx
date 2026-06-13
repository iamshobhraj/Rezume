import { useState, useEffect } from 'react';
import api from '../api/client';
import ResumePreview from '../components/ResumePreview';

export default function GenerateResume() {
  const [jd, setJd] = useState('');
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState('');
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
    setStage('parsing_jd');
    setError(null);
    setResult(null);

    // Simulate progress stages since the backend is synchronous
    // In a real implementation with SSE, the backend would stream these updates
    const stages = [
      { id: 'parsing_jd', text: 'Parsing JD & Extracting Keywords...', time: 0 },
      { id: 'skill_bridge', text: 'Analyzing Skill Gaps...', time: 3000 },
      { id: 'retrieval', text: 'Retrieving Relevant Experience...', time: 6000 },
      { id: 'bullet_gen', text: 'Generating Tailored Bullets...', time: 9000 },
      { id: 'ats_verify', text: 'Verifying ATS Compatibility...', time: 20000 },
      { id: 'pdf_render', text: 'Compiling LaTeX PDF...', time: 23000 },
    ];
    
    const timers = stages.map(s => setTimeout(() => setStage(s.id), s.time));

    try {
      const res = await api.post('/resumes/generate', { job_description: jd });
      
      // Clear timers since we finished
      timers.forEach(clearTimeout);
      setStage('complete');
      
      setResult(res.data);
      // Refresh history
      const histRes = await api.get('/resumes');
      setHistory(histRes.data);
    } catch (err) {
      timers.forEach(clearTimeout);
      setError(err.response?.data?.detail || 'Generation failed. Make sure you have an active chat and embedding provider.');
    } finally {
      setLoading(false);
    }
  };

  const currentStageText = (() => {
    switch (stage) {
      case 'parsing_jd': return 'Parsing job description and extracting keywords...';
      case 'skill_bridge': return 'Analyzing skill gaps and framing...';
      case 'retrieval': return 'Retrieving typed experience (Work/Project/OSS)...';
      case 'bullet_gen': return 'Generating tailored achievement bullets...';
      case 'ats_verify': return 'Scoring against ATS keywords...';
      case 'pdf_render': return 'Compiling LaTeX into PDF...';
      default: return 'Generating resume...';
    }
  })();

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
                  Generating...
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
                        {r.score && <span className={`badge ${r.score >= 80 ? 'badge-emerald' : r.score >= 60 ? 'badge-yellow' : 'badge-red'}`}>
                          ATS: {r.score}%
                        </span>}
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
              <div style={{ color: 'var(--color-text-primary)', fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                Pipeline Active
              </div>
              <div style={{ color: 'var(--color-accent-violet)', fontSize: '0.9375rem', fontFamily: 'monospace' }}>
                > {currentStageText}
              </div>
            </div>
          )}
          {result && !loading && (
            <>
              {/* ATS Score Banner */}
              <div className="glass-panel" style={{ padding: '1rem', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>
                    ATS Match Score
                  </div>
                  <div style={{ 
                    fontSize: '1.5rem', 
                    fontWeight: 800,
                    color: result.score >= 80 ? 'var(--color-success)' : result.score >= 60 ? 'var(--color-warning)' : 'var(--color-danger)'
                  }}>
                    {result.score}%
                  </div>
                </div>
                
                {result.generated_content && (
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <span className="badge badge-emerald">
                      {JSON.parse(result.generated_content).ats_matched?.length || 0} Matched
                    </span>
                    <span className="badge badge-red">
                      {JSON.parse(result.generated_content).ats_missing?.length || 0} Missing
                    </span>
                  </div>
                )}
              </div>
              
              <ResumePreview content={result.generated_content} resumeId={result.id} />
              
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
                Enter a job description and click Generate to run the multi-stage pipeline
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
