import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, AlertOctagon } from 'lucide-react';
import TaskRunner from './pages/TaskRunner';
import Escalations from './pages/Escalations';

function Navigation() {
  const location = useLocation();
  
  return (
    <nav className="navbar">
      <div className="container nav-content">
        <Link to="/" className="nav-brand">
          <div style={{ width: 28, height: 28, background: 'linear-gradient(135deg, var(--primary), var(--accent))', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold' }}>
            V
          </div>
          VadaChain
        </Link>
        <div className="nav-links">
          <Link to="/" className={`nav-link flex items-center gap-2 ${location.pathname === '/' ? 'active' : ''}`}>
            <LayoutDashboard size={18} />
            Task Runner
          </Link>
          <Link to="/escalations" className={`nav-link flex items-center gap-2 ${location.pathname === '/escalations' ? 'active' : ''}`}>
            <AlertOctagon size={18} />
            Escalations
          </Link>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <Navigation />
      <main className="container mt-8 mb-8">
        <Routes>
          <Route path="/" element={<TaskRunner />} />
          <Route path="/escalations" element={<Escalations />} />
        </Routes>
      </main>
    </Router>
  );
}

export default App;
