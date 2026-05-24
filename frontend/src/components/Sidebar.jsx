import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard', icon: '◈' },
  { to: '/profile', label: 'User Profile', icon: '👤' },
  { to: '/projects', label: 'Projects & OSS', icon: '◉' },
  { to: '/generate', label: 'Generate Resume', icon: '✦' },
  { to: '/history', label: 'Resume History', icon: '◷' },
  { to: '/config', label: 'Resume Config', icon: '⚙' },
  { to: '/providers', label: 'AI Providers', icon: '⬡' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="gradient-text" style={{ fontSize: '1.5rem', fontWeight: 800 }}>◆</span>
        <span className="sidebar-title">ResumeAI</span>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
            }
            end={to === '/'}
          >
            <span className="sidebar-icon">{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          Resume Intelligence Engine
        </div>
        <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', opacity: 0.6 }}>
          v0.1.0 · Multi-Provider
        </div>
      </div>

      <style>{`
        .sidebar {
          width: 240px;
          min-height: 100vh;
          background: var(--color-bg-secondary);
          border-right: 1px solid var(--color-border-glass);
          display: flex;
          flex-direction: column;
          padding: 1.5rem 0.75rem;
          position: fixed;
          left: 0;
          top: 0;
          z-index: 40;
        }

        .sidebar-brand {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0 0.75rem 1.5rem;
          border-bottom: 1px solid var(--color-border-glass);
          margin-bottom: 1.5rem;
        }

        .sidebar-title {
          font-size: 1.125rem;
          font-weight: 700;
          color: var(--color-text-primary);
          letter-spacing: -0.02em;
        }

        .sidebar-nav {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          flex: 1;
        }

        .sidebar-link {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.625rem 0.75rem;
          border-radius: 10px;
          color: var(--color-text-secondary);
          text-decoration: none;
          font-size: 0.875rem;
          font-weight: 500;
          transition: all 0.2s ease;
        }

        .sidebar-link:hover {
          background: rgba(255, 255, 255, 0.05);
          color: var(--color-text-primary);
        }

        .sidebar-link-active {
          background: rgba(139, 92, 246, 0.12);
          color: var(--color-accent-violet);
        }

        .sidebar-icon {
          font-size: 1rem;
          width: 1.25rem;
          text-align: center;
        }

        .sidebar-footer {
          padding: 1rem 0.75rem 0;
          border-top: 1px solid var(--color-border-glass);
          margin-top: auto;
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }
      `}</style>
    </aside>
  );
}
