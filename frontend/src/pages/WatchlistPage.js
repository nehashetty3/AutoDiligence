import React, { useState } from 'react';
import axios from 'axios';

export default function WatchlistPage() {
  const [email, setEmail] = useState('');
  const [list, setList] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    if (!email.trim()) return;
    setLoading(true);
    try { const r = await axios.get(`/api/watchlist/${email}`); setList(r.data); }
    catch { setList([]); }
    setSearched(true); setLoading(false);
  };

  const remove = async (company_id) => {
    try { await axios.delete(`/api/watchlist/remove?company_id=${company_id}&user_email=${email}`); setList(l => l.filter(x => x.company_id !== company_id)); }
    catch {}
  };

  const rColor = s => !s ? 'var(--text-3)' : s > 65 ? 'var(--red)' : s > 35 ? 'var(--amber)' : 'var(--green)';

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <div style={S.header}>
        <div style={S.headerInner}>
          <h1 style={S.h1}>Watchlist</h1>
          <p style={S.sub}>Monitor companies and receive alerts when risk signals change</p>
        </div>
      </div>
      <div style={S.body}>
        <div style={S.card}>
          <div style={S.label}>Your email address</div>
          <div style={S.row}>
            <input value={email} onChange={e => setEmail(e.target.value)} onKeyDown={e => e.key === 'Enter' && fetch()}
              placeholder="Enter the email you used when adding companies" style={S.input} />
            <button onClick={fetch} style={S.btn} disabled={loading}>{loading ? 'Loading...' : 'View Watchlist'}</button>
          </div>
        </div>

        {searched && (
          list.length === 0 ? (
            <div style={S.empty}>
              <div style={S.emptyIcon}>○</div>
              <div style={S.emptyTitle}>No companies on watchlist</div>
              <div style={S.emptySub}>Analyze a company and add it from the results page</div>
            </div>
          ) : (
            <div>
              <div style={S.listMeta}>{list.length} {list.length === 1 ? 'company' : 'companies'} monitored</div>
              {list.map(e => (
                <div key={e.watchlist_id} style={S.entry}>
                  <div style={S.entryLeft}>
                    <div style={S.entryName}>{e.company_name}</div>
                    <div style={S.entryTicker}>{e.ticker}</div>
                  </div>
                  <div style={S.entryMid}>
                    {[['Last Risk Score', e.last_risk_score ? `${e.last_risk_score.toFixed(1)}/100` : '—', rColor(e.last_risk_score)],
                      ['Alert Threshold', `±${e.alert_threshold} pts`, 'var(--text-1)'],
                      ['Added', e.created_at?.slice(0, 10), 'var(--text-1)']].map(([l, v, c]) => (
                      <div key={l}>
                        <div style={S.mLabel}>{l}</div>
                        <div style={{ ...S.mVal, color: c }}>{v}</div>
                      </div>
                    ))}
                  </div>
                  <button onClick={() => remove(e.company_id)} style={S.removeBtn}>Remove</button>
                </div>
              ))}
            </div>
          )
        )}

        <div style={S.info}>
          <div style={S.infoTitle}>How alerts work</div>
          <p style={S.infoText}>AutoDiligence re-analyzes watchlisted companies daily via Apache Airflow. When the risk score changes by more than your threshold or sentiment shifts significantly, you receive an email with the updated analysis.</p>
        </div>
      </div>
    </div>
  );
}

const S = {
  header: { background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '36px 0 28px' },
  headerInner: { maxWidth: 800, margin: '0 auto', padding: '0 40px' },
  h1: { fontFamily: "'Playfair Display', serif", fontSize: 28, fontWeight: 600, color: 'var(--text-1)', letterSpacing: '-0.3px', marginBottom: 6 },
  sub: { fontSize: 14, color: 'var(--text-2)' },
  body: { maxWidth: 800, margin: '0 auto', padding: '28px 40px 80px' },
  card: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '24px', marginBottom: 20 },
  label: { fontSize: 11, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 },
  row: { display: 'flex', gap: 8 },
  input: { flex: 1, padding: '10px 14px', border: '1.5px solid var(--border-strong)', borderRadius: 6, fontSize: 14, fontFamily: 'inherit', outline: 'none', background: 'var(--bg)', color: 'var(--text-1)' },
  btn: { background: 'var(--accent)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' },
  empty: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '48px 20px', textAlign: 'center', marginBottom: 20 },
  emptyIcon: { fontSize: 28, color: 'var(--text-3)', marginBottom: 10 },
  emptyTitle: { fontSize: 14, fontWeight: 600, color: 'var(--text-1)', marginBottom: 4 },
  emptySub: { fontSize: 13, color: 'var(--text-3)' },
  listMeta: { fontSize: 11, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 },
  entry: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '16px 20px', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 32 },
  entryLeft: { flex: '0 0 160px' },
  entryName: { fontSize: 15, fontWeight: 700, color: 'var(--text-1)' },
  entryTicker: { fontSize: 12, color: 'var(--accent-2)', fontWeight: 600, marginTop: 2 },
  entryMid: { display: 'flex', gap: 32, flex: 1 },
  mLabel: { fontSize: 10, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 3 },
  mVal: { fontSize: 14, fontWeight: 700 },
  removeBtn: { background: 'none', border: '1px solid var(--border)', color: 'var(--text-3)', padding: '6px 12px', borderRadius: 5, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' },
  info: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 24px', marginTop: 24 },
  infoTitle: { fontSize: 13, fontWeight: 700, color: 'var(--text-1)', marginBottom: 8 },
  infoText: { fontSize: 13, color: 'var(--text-2)', lineHeight: 1.7 },
};
