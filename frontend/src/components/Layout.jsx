import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <main className="animate-fade-in" style={{
        marginLeft: '240px',
        flex: 1,
        padding: '2rem 2.5rem',
        maxWidth: 'calc(100vw - 240px)',
      }}>
        <Outlet />
      </main>
    </div>
  );
}
