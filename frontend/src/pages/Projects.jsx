import { useState, useEffect } from 'react';
import api from '../api/client';
import ProjectForm from '../components/ProjectForm';
import OssFetcher from '../components/OssFetcher';

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editProject, setEditProject] = useState(null);
  const [search, setSearch] = useState('');

  const fetchProjects = async () => {
    try {
      const res = await api.get('/projects');
      setProjects(res.data);
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleSubmit = async (formData, projectId) => {
    if (projectId) {
      await api.put(`/projects/${projectId}`, formData);
    } else {
      await api.post('/projects', formData);
    }
    setShowForm(false);
    setEditProject(null);
    fetchProjects();
  };

  const handleDelete = async (id, title) => {
    if (!confirm(`Delete "${title}"? This will also remove all indexed chunks.`)) return;
    try {
      await api.delete(`/projects/${id}`);
      fetchProjects();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete');
    }
  };

  const filtered = projects.filter(
    (p) =>
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      (p.company || '').toLowerCase().includes(search.toLowerCase()) ||
      (p.role || '').toLowerCase().includes(search.toLowerCase()) ||
      (p.entry_type || p.project_type || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="animate-fade-in-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
            <span className="gradient-text">Projects & OSS</span>
          </h1>
          <p style={{ margin: '0.375rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9375rem' }}>
            Manage your personal projects, work history, and open-source contributions
          </p>
        </div>
        <button className="btn-gradient" onClick={() => { setEditProject(null); setShowForm(true); }}>
          + Add Project
        </button>
      </div>

      <OssFetcher onFetched={fetchProjects} />

      {/* Search */}
      <div style={{ marginBottom: '1.5rem', marginTop: '1.5rem' }}>
        <input
          className="input-field"
          placeholder="Search projects by title, context, or type..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: '400px' }}
        />
      </div>

      {/* Projects Grid */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <span className="spinner" style={{ width: '32px', height: '32px' }} />
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>◉</div>
          <div style={{ fontSize: '0.9375rem', color: 'var(--color-text-muted)' }}>
            {search ? 'No projects match your search' : 'No projects yet'}
          </div>
          {!search && (
            <button className="btn-gradient" style={{ marginTop: '1rem' }} onClick={() => setShowForm(true)}>
              + Add Your First Project
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          {filtered.map((project) => (
            <div key={project.id} className="glass-panel" style={{ padding: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.375rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '1rem' }}>{project.title}</span>
                  <span className={
                    (project.entry_type || project.project_type) === 'oss' ? 'badge badge-green' :
                    (project.entry_type || project.project_type) === 'work_experience' ? 'badge badge-emerald' :
                    'badge badge-violet'
                  }>
                    {(project.entry_type || project.project_type) === 'work_experience' ? 'WORK EXP' :
                     (project.entry_type || project.project_type) === 'oss' ? 'OSS' : 'PROJECT'}
                  </span>
                  <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.05)' }}>
                    {'⭐'.repeat(project.priority)}
                  </span>
                  <span className="badge badge-violet" style={{ opacity: 0.7 }}>
                    {project.chunk_count} chunk{project.chunk_count !== 1 ? 's' : ''}
                  </span>
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', display: 'flex', gap: '1rem' }}>
                  {project.company && <span>{project.company}</span>}
                  {project.role && <span>· {project.role}</span>}
                  {(project.date_range || (project.start_date && `${project.start_date} – ${project.end_date || 'Present'}`)) && (
                    <span>· {project.date_range || `${project.start_date} – ${project.end_date || 'Present'}`}</span>
                  )}
                  {project.github_url && <a href={project.github_url} target="_blank" rel="noreferrer" style={{ color: 'var(--color-accent-violet)' }}>· GitHub</a>}
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginTop: '0.375rem' }}>
                  {project.raw_text.substring(0, 150)}...
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginLeft: '1rem' }}>
                <button
                  className="btn-secondary"
                  style={{ padding: '0.375rem 0.625rem', fontSize: '0.75rem' }}
                  onClick={() => { setEditProject(project); setShowForm(true); }}
                >
                  ✎ Edit
                </button>
                <button
                  className="btn-danger"
                  style={{ padding: '0.375rem 0.625rem', fontSize: '0.75rem' }}
                  onClick={() => handleDelete(project.id, project.title)}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <ProjectForm
          editEntry={editProject}
          onSubmit={handleSubmit}
          onCancel={() => { setShowForm(false); setEditProject(null); }}
        />
      )}
    </div>
  );
}
