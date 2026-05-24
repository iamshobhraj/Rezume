import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';

export default function Dashboard() {
  const [stats, setStats] = useState({
    entries: 0,
    chunks: 0,
    providers: 0,
    resumes: 0,
    activeChat: null,
    activeEmbed: null,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [projects, providers, resumes] = await Promise.all([
          api.get('/projects'),
          api.get('/providers'),
          api.get('/resumes'),
        ]);

        const totalChunks = projects.data.reduce((acc, p) => acc + (p.chunk_count || 0), 0);
        const activeChat = providers.data.find((p) => p.is_active_chat);
        const activeEmbed = providers.data.find((p) => p.is_active_embedding);

        setStats({
          projects: projects.data.length,
          chunks: totalChunks,
          providers: providers.data.length,
          resumes: resumes.data.length,
          activeChat,
          activeEmbed,
        });
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  const statCards = [
    { label: 'Projects & OSS', value: stats.projects || 0, icon: '◉', color: 'var(--color-accent-violet)' },
    { label: 'Chunks Indexed', value: stats.chunks, icon: '⬢', color: 'var(--color-accent-cyan)' },
    { label: 'AI Providers', value: stats.providers, icon: '⬡', color: 'var(--color-accent-emerald)' },
    { label: 'Resumes Generated', value: stats.resumes, icon: '✦', color: 'var(--color-accent-rose)' },
  ];

  return (
    <div className="animate-fade-in-up">
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
          <span className="gradient-text">Dashboard</span>
        </h1>
        <p style={{ margin: '0.375rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9375rem' }}>
          Resume Intelligence Engine overview
        </p>
      </div>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        {statCards.map((card) => (
          <div key={card.label} className="stat-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {card.label}
                </div>
                <div style={{ fontSize: '2rem', fontWeight: 800, marginTop: '0.375rem', letterSpacing: '-0.02em' }}>
                  {loading ? <span className="spinner" /> : card.value}
                </div>
              </div>
              <span style={{ fontSize: '1.5rem', opacity: 0.4 }}>{card.icon}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Active Providers */}
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '0.9375rem', fontWeight: 700 }}>Active Providers</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div style={{ padding: '1rem', background: 'var(--color-bg-secondary)', borderRadius: '12px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 600, marginBottom: '0.375rem' }}>CHAT</div>
            {stats.activeChat ? (
              <>
                <div style={{ fontWeight: 600, fontSize: '0.9375rem' }}>{stats.activeChat.name}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', fontFamily: 'monospace' }}>
                  {stats.activeChat.chat_model}
                </div>
              </>
            ) : (
              <div style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>Not configured</div>
            )}
          </div>
          <div style={{ padding: '1rem', background: 'var(--color-bg-secondary)', borderRadius: '12px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 600, marginBottom: '0.375rem' }}>EMBEDDING</div>
            {stats.activeEmbed ? (
              <>
                <div style={{ fontWeight: 600, fontSize: '0.9375rem' }}>{stats.activeEmbed.name}</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', fontFamily: 'monospace' }}>
                  {stats.activeEmbed.embedding_model} ({stats.activeEmbed.embedding_dim}d)
                </div>
              </>
            ) : (
              <div style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>Not configured</div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <Link to="/projects" style={{ textDecoration: 'none' }}>
          <button className="btn-gradient">◉ Add Project</button>
        </Link>
        <Link to="/generate" style={{ textDecoration: 'none' }}>
          <button className="btn-secondary">✦ Generate Resume</button>
        </Link>
        <Link to="/providers" style={{ textDecoration: 'none' }}>
          <button className="btn-secondary">⬡ Manage Providers</button>
        </Link>
      </div>
    </div>
  );
}
