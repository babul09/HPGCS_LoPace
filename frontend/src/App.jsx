import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layers, Activity, PlayCircle, Code } from 'lucide-react';
import './App.css';

import Hero from './pages/Hero';
import Architecture from './pages/Architecture';
import Benchmarks from './pages/Benchmarks';
import Demo from './pages/Demo';

function NavBar() {
  const location = useLocation();
  const getNavClass = (path) => {
    return `nav-link ${location.pathname === path ? 'active' : ''}`;
  };

  return (
    <nav className="material-app-bar">
      <div className="nav-container">
        <Link to="/" className="nav-logo">
          <Layers className="logo-icon" size={28} />
          <span>HPGCS</span>
        </Link>
        
        <div className="nav-links">
          <Link to="/" className={getNavClass('/')}>Home</Link>
          <Link to="/architecture" className={getNavClass('/architecture')}>Architecture</Link>
          <Link to="/benchmarks" className={getNavClass('/benchmarks')}>Benchmarks</Link>
          <Link to="/demo" className={getNavClass('/demo')}>Demo</Link>
        </div>

        <a href="https://github.com/babul09/HPGCS_LoPace" target="_blank" rel="noreferrer" className="github-btn">
          <Code size={20} />
          <span>GitHub</span>
        </a>
      </div>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div className="app-root">
        <NavBar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Hero />} />
            <Route path="/architecture" element={<Architecture />} />
            <Route path="/benchmarks" element={<Benchmarks />} />
            <Route path="/demo" element={<Demo />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
