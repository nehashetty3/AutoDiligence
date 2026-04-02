import React, { useState } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const rColor = s => s > 65 ? 'var(--red)' : s > 35 ? 'var(--amber)' : 'var(--green)';
const rBg = s => s > 65 ? 'var(--red-bg)' : s > 35 ? 'var(--amber-bg)' : 'var(--green-bg)';
const rHex = s => s > 65 ? '#B91C1C' : s > 35 ? '#B45309' : '#15803D';

export default function ComparePage() {
  const [companies, setCompanies] = useState(['', '', '']);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const update = (i, v) => { const a = [...companies]; a[i] = v; setCompanies(a); };

  const run = async () => {
    const names = companies.filter(c => c.trim());
    if (names.length < 2) { setError('Enter at least 2 companies'); return; }
    setLoading(true); setError('');
    try { const r = await axios.post('/api/compare', { company_names: names }); setResults(r.data.companies); }
    catch { setError('Comparison failed. Please try again.'); }
    setLoading(false);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <div style={S.header}>
        <div style={S.headerInner}>
          <h1 style={S.h1}>Compare Companies</h1>
          <p style={S.sub}>Side-by-side risk benchmarking across multiple companies</p>
        </div>
      </div>
      <div style={S.body}>
        <div style={S.inputCard}>
          <div style={S.inputGrid}>
            {companies.map((c, i) => (
              <div key={i}>
                <div style={S.label}>Company {i + 1}</div>
                <input value={c} onChange={e => update(i, e.target.value)}
                  placeholder={['e.g. Apple', 'e.g. Infosys', 'e.g. Goldman Sachs'][i] || 'Company name'}
                  style={S.input} />
              </div>
            ))}
            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button onClick={() => setCompanies([...companies, ''])} style={S.addBtn}>+ Add</button>
            </div>
          </div>
          {error && <div style={S.err}>{error}</div>}
          <button onClick={run} style={S.compareBtn} disabled={loading}>
            {loading ? 'Running full analysis on each company...' : 'Run Comparison'}
          </button>
          {loading && <p style={S.loadNote}>This runs a full analysis on each company — may take a few minutes.</p>}
        </div>

        {results?.length > 0 && (
          <div>
            <div style={S.card}>
              <div style={S.cardTitle}>Risk Score Comparison</div>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={results} margin={{ top: 10, bottom: 20 }}>
                  <XAxis dataKey="company_name" stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
                  <YAxis domain={[0, 100]} stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
                  <Tooltip contentStyle={{ background: 'white', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} formatter={v => [`${v}/100`, 'Risk Score']} />
                  <Bar dataKey="risk_score" radius={[3, 3, 0, 0]}>
                    {results.map((r, i) => <Cell key={i} fill={rHex(r.risk_score)} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div style={S.card}>
              <div style={S.cardTitle}>Detailed Comparison</div>
              <table style={S.table}>
                <thead><tr>{['Company', 'Risk Score', 'Category', 'Sentiment', 'Hiring Health', 'Patent Velocity'].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={i} style={S.tr}>
                      <td style={{ ...S.td, fontWeight: 600, color: 'var(--text-1)' }}>
                        {r.company_name}
                        {r.ticker && <span style={{ fontSize: 10, color: 'var(--accent-2)', marginLeft: 6, background: '#EFF6FF', padding: '2px 6px', borderRadius: 3, fontWeight: 600 }}>{r.ticker}</span>}
                      </td>
                      <td style={{ ...S.td, fontWeight: 800, fontSize: 18, color: rColor(r.risk_score) }}>{r.risk_score?.toFixed(1)}</td>
                      <td style={S.td}>
                        <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 3, background: rBg(r.risk_score), color: rColor(r.risk_score) }}>
                          {r.risk_score > 65 ? 'HIGH' : r.risk_score > 35 ? 'MEDIUM' : 'LOW'}
                        </span>
                      </td>
                      <td style={S.td}>{r.sentiment_score?.toFixed(2)}</td>
                      <td style={S.td}>{r.hiring_health}/100</td>
                      <td style={S.td}>{r.patent_velocity || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const S = {
  header: { background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '36px 0 28px' },
  headerInner: { maxWidth: 1000, margin: '0 auto', padding: '0 40px' },
  h1: { fontFamily: "'Playfair Display', serif", fontSize: 28, fontWeight: 600, color: 'var(--text-1)', letterSpacing: '-0.3px', marginBottom: 6 },
  sub: { fontSize: 14, color: 'var(--text-2)' },
  body: { maxWidth: 1000, margin: '0 auto', padding: '28px 40px 80px' },
  inputCard: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '24px', marginBottom: 20 },
  inputGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 },
  label: { fontSize: 11, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 },
  input: { width: '100%', padding: '10px 14px', border: '1.5px solid var(--border-strong)', borderRadius: 6, fontSize: 14, fontFamily: 'inherit', outline: 'none', background: 'var(--bg)', color: 'var(--text-1)', boxSizing: 'border-box' },
  addBtn: { background: 'none', border: '1px dashed var(--border-strong)', color: 'var(--text-3)', padding: '10px', borderRadius: 6, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', width: '100%' },
  err: { color: 'var(--red)', fontSize: 13, marginBottom: 12, padding: '10px 14px', background: 'var(--red-bg)', borderRadius: 6 },
  compareBtn: { width: '100%', padding: '11px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' },
  loadNote: { fontSize: 12, color: 'var(--text-3)', textAlign: 'center', marginTop: 10 },
  card: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '24px', marginBottom: 16 },
  cardTitle: { fontSize: 14, fontWeight: 700, color: 'var(--text-1)', marginBottom: 20 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { fontSize: 10, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '8px 12px', textAlign: 'left', borderBottom: '1px solid var(--border)' },
  tr: { borderBottom: '1px solid var(--bg)' },
  td: { fontSize: 13, color: 'var(--text-2)', padding: '12px' },
};
