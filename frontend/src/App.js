import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ResultsPage from './pages/ResultsPage';
import WatchlistPage from './pages/WatchlistPage';
import ComparePage from './pages/ComparePage';
import './App.css';

function Nav() {
  const loc = useLocation();
  return (
    <nav style={N.nav}>
      <div style={N.inner}>
        <Link to="/" style={N.brand}>
          <span style={N.brandMark}>A</span>
          <span style={N.brandName}>AutoDiligence</span>
        </Link>
        <div style={N.links}>
          {[['/', 'Analyze'], ['/compare', 'Compare'], ['/watchlist', 'Watchlist']].map(([to, label]) => (
            <Link key={to} to={to} style={{ ...N.link, ...(loc.pathname === to ? N.linkActive : {}) }}>
              {label}
            </Link>
          ))}
        </div>
        <span style={N.tagline}>M&A Intelligence Platform</span>
      </div>
    </nav>
  );
}

const N = {
  nav: { background: 'var(--surface)', borderBottom: '1px solid var(--border)', height: 'var(--nav-h)', position: 'sticky', top: 0, zIndex: 50 },
  inner: { maxWidth: 1200, margin: '0 auto', padding: '0 40px', height: '100%', display: 'flex', alignItems: 'center', gap: 32 },
  brand: { display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 },
  brandMark: { width: 28, height: 28, background: 'var(--accent)', color: '#fff', fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 4 },
  brandName: { fontSize: 15, fontWeight: 600, color: 'var(--text-1)', letterSpacing: '-0.2px' },
  links: { display: 'flex', gap: 2, flex: 1 },
  link: { padding: '5px 12px', borderRadius: 5, fontSize: 13, fontWeight: 500, color: 'var(--text-2)', transition: 'all 0.15s' },
  linkActive: { color: 'var(--text-1)', background: 'var(--surface-2)', fontWeight: 600 },
  tagline: { fontSize: 11, color: 'var(--text-3)', letterSpacing: '0.8px', textTransform: 'uppercase', fontWeight: 500, flexShrink: 0 }
};

export default function App() {
  const [result, setResult] = useState(null);
  return (
    <Router>
      <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
        <Nav />
        <Routes>
          <Route path="/" element={<HomePage setResult={setResult} />} />
          <Route path="/results" element={<ResultsPage result={result} />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/compare" element={<ComparePage />} />
        </Routes>
      </div>
    </Router>
  );
}
