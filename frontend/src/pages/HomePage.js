import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const STEPS = [
  'Fetching SEC financial filings',
  'Pulling news articles via RSS & NewsAPI',
  'Retrieving patent data from USPTO',
  'Processing hiring signals',
  'Running FinBERT sentiment analysis',
  'Scoring risk with XGBoost + SHAP',
  'Generating due diligence report',
];

function formatApiError(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item?.msg) return item.msg;
        try { return JSON.stringify(item); } catch { return String(item); }
      })
      .join(' | ');
  }
  if (detail && typeof detail === 'object') {
    if (detail.msg) return detail.msg;
    try { return JSON.stringify(detail); } catch { return fallback; }
  }
  return fallback;
}

export default function HomePage({ setResult }) {
  const [company, setCompany] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const run = async (e) => {
    e.preventDefault();
    if (!company.trim()) return;
    setLoading(true); setError(''); setStep(1);
    let s = 1;
    const iv = setInterval(() => { s++; setStep(s); if (s >= STEPS.length) clearInterval(iv); }, 4500);
    try {
      const res = await axios.post('/api/analyze', { company_name: company });
      clearInterval(iv); setStep(STEPS.length);
      setResult(res.data);
      setTimeout(() => navigate('/results'), 300);
    } catch (err) {
      clearInterval(iv);
      setError(formatApiError(err, 'Could not find this company. Try the full legal name or stock ticker.'));
      setLoading(false); setStep(0);
    }
  };

  return (
    <div>
      {/* Hero */}
      <div style={S.hero}>
        <div style={S.heroInner}>
          <div style={S.kicker}>Due Diligence Automation</div>
          <h1 style={S.h1}>
            Institutional-grade M&A analysis.<br />
            <em style={S.h1em}>Delivered in minutes.</em>
          </h1>
          <p style={S.lead}>
            Six analytical layers. One risk score. Complete transparency. AutoDiligence processes SEC filings, global news, patent data, and hiring signals — delivering institutional-grade M&A intelligence automatically.
          </p>
          <form onSubmit={run} style={S.form}>
            <div style={S.inputRow}>
              <input
                value={company} onChange={e => setCompany(e.target.value)}
                placeholder="Company name or ticker — e.g. Apple, Infosys, TITAN.NS"
                style={S.input} disabled={loading}
              />
              <button type="submit" style={{ ...S.btn, ...(loading ? S.btnDis : {}) }} disabled={loading}>
                {loading ? 'Running analysis...' : 'Run Analysis'}
              </button>
            </div>
            <div style={S.chips}>
              <span style={S.chipsLabel}>Try:</span>
              {['Apple', 'Infosys', 'Tesla', 'HDFC Bank', 'Goldman Sachs'].map(n => (
                <button key={n} type="button" onClick={() => setCompany(n)} style={S.chip}>{n}</button>
              ))}
            </div>
          </form>
          {error && <div style={S.err}><strong>Not found —</strong> {error}</div>}
          {loading && (
            <div style={S.progress}>
              <div style={S.progressHead}>
                <div style={S.dot} />
                <span style={S.progressLabel}>Analysis running</span>
              </div>
              {STEPS.map((label, i) => (
                <div key={i} style={S.stepRow}>
                  <div style={{ ...S.stepDot, ...(step > i + 1 ? S.stepDone : step === i + 1 ? S.stepCur : {}) }} />
                  <span style={{ ...S.stepTxt, ...(step > i + 1 ? S.stepTxtDone : step === i + 1 ? S.stepTxtCur : {}) }}>
                    {label}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div style={S.statsBar}>
          {[['4', 'Data sources'], ['5', 'Analytics modules'], ['21', 'ML features'], ['0–100', 'Risk score range']].map(([v, l]) => (
            <div key={l} style={S.stat}>
              <div style={S.statV}>{v}</div>
              <div style={S.statL}>{l}</div>
            </div>
          ))}
        </div>
      </div>

      {/* What gets analyzed */}
      <div style={S.section}>
        <div style={S.sectionInner}>
          <h2 style={S.sectionH}>What gets analyzed</h2>
          <p style={S.sectionSub}>Six analytical layers run in parallel on every company</p>
          <div style={S.grid}>
            {[
              ['01', 'Financial Anomaly Detection', 'IsolationForest algorithm flags statistical outliers across revenue growth, margins, debt ratios, and cash burn using 6 years of real financial data.'],
              ['02', 'News Sentiment Analysis', 'FinBERT transformer model — trained specifically on financial text — scores 24 months of news coverage and calculates sentiment trajectory.'],
              ['03', 'Patent Innovation Clustering', 'LDA topic modeling groups patents into technology domains and measures filing velocity to detect R&D acceleration or retreat.'],
              ['04', 'Hiring Trend Intelligence', 'Department-level hiring velocity analysis using SQL window functions identifies organizational health signals and expansion patterns.'],
              ['05', 'XGBoost Risk Scoring', 'Gradient boosting model trained on M&A outcome data produces a 0–100 risk score with SHAP explainability showing factor contributions.'],
              ['06', 'Competitor Benchmarking', 'Automatic identification and parallel analysis of top 4 competitors for contextual risk comparison across all dimensions.'],
            ].map(([n, title, desc]) => (
              <div key={n} style={S.card}>
                <div style={S.cardNum}>{n}</div>
                <div style={S.cardTitle}>{title}</div>
                <div style={S.cardDesc}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const S = {
  hero: { background: 'var(--surface)', borderBottom: '1px solid var(--border)' },
  heroInner: { maxWidth: 720, margin: '0 auto', padding: '64px 40px 40px' },
  kicker: { display: 'inline-block', fontSize: 11, fontWeight: 600, letterSpacing: '1.2px', textTransform: 'uppercase', color: 'var(--accent-2)', background: '#EFF6FF', padding: '4px 10px', borderRadius: 3, marginBottom: 20 },
  h1: { fontFamily: "'Playfair Display', Georgia, serif", fontSize: 42, lineHeight: 1.2, color: 'var(--text-1)', marginBottom: 18, letterSpacing: '-0.5px', fontWeight: 600 },
  h1em: { fontStyle: 'italic', color: 'var(--text-2)' },
  lead: { fontSize: 15, color: 'var(--text-2)', lineHeight: 1.7, marginBottom: 36, maxWidth: 580 },
  form: {},
  inputRow: { display: 'flex', gap: 8, marginBottom: 12 },
  input: { flex: 1, padding: '11px 16px', fontSize: 14, border: '1.5px solid var(--border-strong)', borderRadius: 6, background: 'var(--bg)', color: 'var(--text-1)', outline: 'none', fontFamily: 'inherit', transition: 'border-color 0.15s' },
  btn: { padding: '11px 22px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap', transition: 'opacity 0.15s' },
  btnDis: { opacity: 0.55, cursor: 'not-allowed' },
  chips: { display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' },
  chipsLabel: { fontSize: 12, color: 'var(--text-3)', marginRight: 2 },
  chip: { background: 'none', border: '1px solid var(--border)', borderRadius: 3, padding: '3px 10px', fontSize: 12, color: 'var(--text-2)', cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.15s' },
  err: { marginTop: 16, padding: '11px 14px', background: 'var(--red-bg)', border: '1px solid #FECACA', borderRadius: 6, color: 'var(--red)', fontSize: 13, lineHeight: 1.5 },
  progress: { marginTop: 24, padding: '20px 24px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 8 },
  progressHead: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 },
  dot: { width: 7, height: 7, borderRadius: '50%', background: 'var(--accent-2)', animation: 'pulse 1.4s infinite' },
  progressLabel: { fontSize: 12, fontWeight: 600, color: 'var(--text-1)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  stepRow: { display: 'flex', alignItems: 'center', gap: 10, padding: '4px 0' },
  stepDot: { width: 5, height: 5, borderRadius: '50%', background: 'var(--border-strong)', flexShrink: 0 },
  stepDone: { background: 'var(--green)' },
  stepCur: { background: 'var(--accent-2)', boxShadow: '0 0 0 3px #DBEAFE' },
  stepTxt: { fontSize: 13, color: 'var(--text-3)' },
  stepTxtDone: { color: 'var(--text-2)' },
  stepTxtCur: { color: 'var(--text-1)', fontWeight: 500 },
  statsBar: { maxWidth: 720, margin: '0 auto', padding: '20px 40px', borderTop: '1px solid var(--border)', display: 'flex', gap: 48 },
  stat: {},
  statV: { fontSize: 20, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.5px' },
  statL: { fontSize: 11, color: 'var(--text-3)', marginTop: 1 },
  section: { padding: '56px 40px 72px', background: 'var(--bg)' },
  sectionInner: { maxWidth: 1100, margin: '0 auto' },
  sectionH: { fontFamily: "'Playfair Display', serif", fontSize: 26, color: 'var(--text-1)', marginBottom: 6, fontWeight: 600 },
  sectionSub: { fontSize: 14, color: 'var(--text-2)', marginBottom: 36 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1px', background: 'var(--border)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' },
  card: { background: 'var(--surface)', padding: '28px 24px' },
  cardNum: { fontSize: 11, fontWeight: 700, color: 'var(--text-3)', letterSpacing: '0.5px', marginBottom: 10 },
  cardTitle: { fontSize: 14, fontWeight: 600, color: 'var(--text-1)', marginBottom: 8 },
  cardDesc: { fontSize: 13, color: 'var(--text-2)', lineHeight: 1.65 },
};
