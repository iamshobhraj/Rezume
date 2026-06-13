import { useState, useEffect } from 'react';
import api from '../api/client';
import StatusBanner from '../components/StatusBanner';

export default function Profile() {
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    phone: '',
    github: '',
    linkedin: '',
    portfolio: '',
    location: '',
    college: '',
    college_start_year: '',
    degree: '',
    graduation_year: '',
    coursework: '',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    api.get('/profile')
      .then((res) => setProfile(res.data))
      .catch((err) => console.error('Failed to load profile:', err))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const res = await api.put('/profile', profile);
      setProfile(res.data);
      setMessage({ type: 'success', text: 'Profile saved successfully' });
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to save profile' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem' }}>
        <span className="spinner" style={{ width: '32px', height: '32px' }} />
      </div>
    );
  }

  return (
    <div className="animate-fade-in-up" style={{ maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
          <span className="gradient-text">Candidate Profile</span>
        </h1>
        <p style={{ margin: '0.375rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9375rem' }}>
          Configure your personal info and education. These details are injected directly into your generated resume and LaTeX header.
        </p>
      </div>

      {message && (
        <StatusBanner
          type={message.type}
          message={message.text}
          onDismiss={() => setMessage(null)}
        />
      )}

      <form onSubmit={handleSave}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Personal Information */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1.25rem', fontSize: '0.9375rem', fontWeight: 700, color: 'var(--color-accent-violet)' }}>
              👤 Personal Contact Info
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  Full Name *
                </label>
                <input
                  className="input-field"
                  value={profile.name}
                  onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                  placeholder="e.g., John Doe"
                  required
                />
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  Email Address *
                </label>
                <input
                  className="input-field"
                  type="email"
                  value={profile.email}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                  placeholder="e.g., john.doe@example.com"
                  required
                />
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  Phone Number
                </label>
                <input
                  className="input-field"
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  placeholder="e.g., (555) 123-4567"
                />
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  Location
                </label>
                <input
                  className="input-field"
                  value={profile.location}
                  onChange={(e) => setProfile({ ...profile, location: e.target.value })}
                  placeholder="e.g., San Francisco, CA"
                />
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  GitHub Username / URL
                </label>
                <input
                  className="input-field"
                  value={profile.github}
                  onChange={(e) => setProfile({ ...profile, github: e.target.value })}
                  placeholder="e.g., github.com/johndoe"
                />
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  LinkedIn URL
                </label>
                <input
                  className="input-field"
                  value={profile.linkedin}
                  onChange={(e) => setProfile({ ...profile, linkedin: e.target.value })}
                  placeholder="e.g., linkedin.com/in/johndoe"
                />
              </div>

              <div style={{ gridColumn: '1 / -1' }}>
                <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  Portfolio Website
                </label>
                <input
                  className="input-field"
                  value={profile.portfolio}
                  onChange={(e) => setProfile({ ...profile, portfolio: e.target.value })}
                  placeholder="e.g., johndoe.dev"
                />
              </div>
            </div>
          </div>

          {/* Education Details */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1.25rem', fontSize: '0.9375rem', fontWeight: 700, color: 'var(--color-accent-violet)' }}>
              🎓 Education Details
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '1rem' }}>
                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                    University / College
                  </label>
                  <input
                    className="input-field"
                    value={profile.college}
                    onChange={(e) => setProfile({ ...profile, college: e.target.value })}
                    placeholder="e.g., Stanford University"
                  />
                </div>

                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                    Start Year
                  </label>
                  <input
                    className="input-field"
                    value={profile.college_start_year}
                    onChange={(e) => setProfile({ ...profile, college_start_year: e.target.value })}
                    placeholder="e.g., 2021"
                  />
                </div>

                <div>
                  <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                    Graduation Year
                  </label>
                  <input
                    className="input-field"
                    value={profile.graduation_year}
                    onChange={(e) => setProfile({ ...profile, graduation_year: e.target.value })}
                    placeholder="e.g., 2025"
                  />
                </div>
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  Degree and Major
                </label>
                <input
                  className="input-field"
                  value={profile.degree}
                  onChange={(e) => setProfile({ ...profile, degree: e.target.value })}
                  placeholder="e.g., B.S. in Computer Science"
                />
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', marginBottom: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  Relevant Coursework
                </label>
                <textarea
                  className="input-field"
                  value={profile.coursework}
                  onChange={(e) => setProfile({ ...profile, coursework: e.target.value })}
                  placeholder="e.g., Data Structures, Operating Systems, Machine Learning"
                  style={{ minHeight: '80px', fontFamily: 'inherit' }}
                />
              </div>
            </div>
          </div>

          {/* Action Button */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button type="submit" className="btn-gradient" disabled={saving}>
              {saving ? <><span className="spinner" /> Saving...</> : 'Save Profile'}
            </button>
          </div>

        </div>
      </form>
    </div>
  );
}
