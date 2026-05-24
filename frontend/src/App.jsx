import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Profile from './pages/Profile';
import Projects from './pages/Projects';
import GenerateResume from './pages/GenerateResume';
import History from './pages/History';
import ResumeConfig from './pages/ResumeConfig';
import ProvidersSettings from './pages/ProvidersSettings';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/entries" element={<Navigate to="/projects" replace />} />
          <Route path="/generate" element={<GenerateResume />} />
          <Route path="/history" element={<History />} />
          <Route path="/config" element={<ResumeConfig />} />
          <Route path="/providers" element={<ProvidersSettings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
