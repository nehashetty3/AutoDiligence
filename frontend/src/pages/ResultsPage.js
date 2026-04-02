import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, AreaChart, Area, ComposedChart, CartesianGrid, Legend
} from 'recharts';
import axios from 'axios';

const rColor = s => s > 65 ? 'var(--red)' : s > 35 ? 'var(--amber)' : 'var(--green)';
const rBg = s => s > 65 ? 'var(--red-bg)' : s > 35 ? 'var(--amber-bg)' : 'var(--green-bg)';
const rLabel = s => s > 65 ? 'HIGH RISK' : s > 35 ? 'MEDIUM RISK' : 'LOW RISK';
const rHex = s => s > 65 ? '#B91C1C' : s > 35 ? '#B45309' : '#15803D';
const normalizeCategory = (category, score) => {
  if (category === 'high' || category === 'medium' || category === 'low') return category;
  if (typeof score === 'number') return score > 65 ? 'high' : score > 35 ? 'medium' : 'low';
  return 'pending';
};
const categoryLabel = (category, score) => {
  const normalized = normalizeCategory(category, score);
  if (normalized === 'pending') return 'PENDING';
  return normalized.toUpperCase() + ' RISK';
};
const categoryColor = (category, score) => {
  const normalized = normalizeCategory(category, score);
  if (normalized === 'high') return 'var(--red)';
  if (normalized === 'medium') return 'var(--amber)';
  if (normalized === 'low') return 'var(--green)';
  return 'var(--text-3)';
};
const categoryBg = (category, score) => {
  const normalized = normalizeCategory(category, score);
  if (normalized === 'high') return 'var(--red-bg)';
  if (normalized === 'medium') return 'var(--amber-bg)';
  if (normalized === 'low') return 'var(--green-bg)';
  return 'var(--surface-2)';
};

const formatApiError = (error, fallback) => {
  const detail = error?.response?.data?.detail;
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
};

const Chip = ({ children, color, bg }) => (
  <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.8px', textTransform: 'uppercase', color, background: bg, padding: '3px 8px', borderRadius: 3, display: 'inline-block' }}>
    {children}
  </span>
);

const Card = ({ children, style }) => (
  <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '24px', marginBottom: 16, ...style }}>
    {children}
  </div>
);

const CardTitle = ({ children, sub }) => (
  <div style={{ marginBottom: sub ? 4 : 20 }}>
    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)' }}>{children}</div>
    {sub && <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 3, marginBottom: 16 }}>{sub}</div>}
  </div>
);

export default function ResultsPage({ result }) {
  const navigate = useNavigate();
  const [tab, setTab] = useState('overview');
  const [wEmail, setWEmail] = useState('');
  const [wMsg, setWMsg] = useState('');
  const [benchmark, setBenchmark] = useState(null);
  const [premium, setPremium] = useState(null);
  const [newsData, setNewsData] = useState(null);
  const [financials, setFinancials] = useState(null);
  const [history, setHistory] = useState(null);
  const [overviewLoaded, setOverviewLoaded] = useState(false);
  const [newsLoaded, setNewsLoaded] = useState(false);
  const [financialsLoaded, setFinancialsLoaded] = useState(false);

  if (!result) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <p style={{ color: 'var(--text-2)', marginBottom: 16 }}>No analysis to display.</p>
      <button onClick={() => navigate('/')} style={S.btnPrimary}>← Back</button>
    </div>
  );

  const { risk_assessment: ra, analytics_details: ad, analytics_summary: as_,
          report, competitors, company_name, company_id, ticker, ingestion_stats } = result;
  const score = ra.risk_score;

  useEffect(() => {
    setBenchmark(null);
    setPremium(null);
    setNewsData(null);
    setFinancials(null);
    setHistory(null);
    setOverviewLoaded(false);
    setNewsLoaded(false);
    setFinancialsLoaded(false);
    setTab('overview');
    setWMsg('');
  }, [company_id]);

  // Load additional data when tab changes
  useEffect(() => {
    if (tab === 'overview' && !overviewLoaded) {
      Promise.allSettled([
        axios.get(`/api/company/${company_id}/benchmark`),
        axios.get(`/api/company/${company_id}/history`),
        axios.get(`/api/company/${company_id}/premium`)
      ]).then(([benchmarkRes, historyRes, premiumRes]) => {
        if (benchmarkRes.status === 'fulfilled') {
          setBenchmark(benchmarkRes.value.data);
        } else {
          setBenchmark({ error: formatApiError(benchmarkRes.reason, 'Benchmark data unavailable for this company.') });
        }

        if (historyRes.status === 'fulfilled') {
          setHistory(historyRes.value.data);
        } else {
          setHistory([]);
        }

        if (premiumRes.status === 'fulfilled') {
          setPremium(premiumRes.value.data);
        } else {
          setPremium({ error: formatApiError(premiumRes.reason, 'Premium estimate unavailable.') });
        }

        setOverviewLoaded(true);
      });
    }
    if (tab === 'sentiment' && !newsLoaded) {
      axios.get(`/api/company/${company_id}/news`)
        .then(r => setNewsData(r.data))
        .catch((e) => setNewsData({
          positive: [],
          negative: [],
          recent: [],
          error: formatApiError(e, 'News data unavailable for this company.')
        }))
        .finally(() => setNewsLoaded(true));
    }
    if (tab === 'financials' && !financialsLoaded) {
      axios.get(`/api/company/${company_id}/financials`)
        .then(r => setFinancials(r.data))
        .catch((e) => setFinancials({
          years: [],
          revenue: [],
          net_income: [],
          debt: [],
          cash: [],
          currency: 'USD Billions',
          error: formatApiError(e, 'Financial data unavailable for this company.')
        }))
        .finally(() => setFinancialsLoaded(true));
    }
  }, [tab, company_id, overviewLoaded, newsLoaded, financialsLoaded]);

  const addWatch = async () => {
    if (!wEmail) return;
    try {
      const r = await axios.post('/api/watchlist/add', { company_id, user_email: wEmail, alert_threshold: 10 });
      setWMsg(r.data.message || 'Added to watchlist.');
    } catch (e) {
      setWMsg(formatApiError(e, 'Error — please try again.'));
    }
  };

  const timeline = ad?.sentiment?.monthly_timeline || [];
  const depts = ad?.hiring?.department_trends?.slice(0, 7) || [];

  const TABS = [
    ['overview', 'Overview'],
    ['financials', 'Financials'],
    ['sentiment', 'Sentiment & News'],
    ['hiring', 'Hiring'],
    ['report', 'Report'],
    ['competitors', 'Competitors'],
  ];

  // Build history chart data
  const historyData = Array.isArray(history)
    ? history.map((h, index) => ({
        label: h.label || h.timestamp || h.date || `Run ${index + 1}`,
        score: h.risk_score,
        category: h.risk_category,
      }))
    : [];

  // Build financial chart data
  const finYears = Array.isArray(financials?.years) ? financials.years : [];
  const finRevenue = Array.isArray(financials?.revenue) ? financials.revenue : [];
  const finNetIncome = Array.isArray(financials?.net_income) ? financials.net_income : [];
  const finDebt = Array.isArray(financials?.debt) ? financials.debt : [];
  const finCash = Array.isArray(financials?.cash) ? financials.cash : [];
  const finChartData = finYears.map((y, i) => ({
    year: y,
    Revenue: finRevenue[i] ?? null,
    'Net Income': finNetIncome[i] ?? null,
    Debt: finDebt[i] ?? null,
    Cash: finCash[i] ?? null,
  }));
  const hasRevenue = finChartData.some((row) => row.Revenue !== null);
  const hasNetIncome = finChartData.some((row) => row['Net Income'] !== null);
  const hasDebt = finChartData.some((row) => row.Debt !== null);
  const hasCash = finChartData.some((row) => row.Cash !== null);
  const historyCount = historyData.length;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      {/* Header */}
      <div style={S.header}>
        <div style={S.headerInner}>
          <button onClick={() => navigate('/')} style={S.backBtn}>← New analysis</button>
          <div style={S.compRow}>
            <div>
              <h1 style={S.compName}>{company_name}</h1>
              {ticker && <Chip color="var(--accent-2)" bg="#EFF6FF">{ticker}</Chip>}
            </div>
            <button onClick={() => window.open(`/api/report/${company_id}/pdf`, '_blank')} style={S.exportBtn}>
              Export PDF Report
            </button>
          </div>
        </div>
      </div>

      <div style={S.body}>
        {/* Risk Panel */}
        <div style={S.riskPanel}>
          <div style={{ ...S.scoreBox, borderColor: rColor(score) + '40', background: rBg(score) }}>
            <Chip color={categoryColor(ra.risk_category, score)} bg={categoryBg(ra.risk_category, score)}>{categoryLabel(ra.risk_category, score)}</Chip>
            <div style={{ ...S.scoreNum, color: rColor(score) }}>{score.toFixed(1)}</div>
            <div style={S.scoreOf}>/ 100</div>
            <div style={S.scoreRec}>{ra.recommendation}</div>
          </div>
          <div style={S.signals}>
            {[
              { label: 'Financial Anomalies', val: as_.financial_anomaly_count, unit: 'detected', alert: as_.financial_anomaly_count > 1 },
              { label: 'News Sentiment', val: as_.overall_sentiment?.toUpperCase(), unit: `${as_.sentiment_score?.toFixed(2)} / 1.0`, alert: as_.sentiment_score < 0.4 },
              { label: 'Sentiment Trend', val: as_.sentiment_trend?.toUpperCase(), unit: '', alert: as_.sentiment_trend === 'declining' },
              { label: 'Patent Velocity', val: as_.patent_velocity?.toUpperCase(), unit: '', alert: as_.patent_velocity === 'decelerating' },
              { label: 'Hiring Health', val: as_.hiring_health_score, unit: '/ 100', alert: as_.hiring_health_score < 40 },
              { label: 'Hiring Trend', val: as_.hiring_trend?.toUpperCase(), unit: '', alert: as_.hiring_trend === 'shrinking' },
            ].map(sig => (
              <div key={sig.label} style={{ ...S.sig, ...(sig.alert ? S.sigAlert : {}) }}>
                <div style={S.sigLabel}>{sig.label}</div>
                <div style={{ ...S.sigVal, color: sig.alert ? 'var(--red)' : 'var(--text-1)' }}>{sig.val}</div>
                {sig.unit && <div style={S.sigUnit}>{sig.unit}</div>}
              </div>
            ))}
          </div>
        </div>

        {/* Summary */}
        <div style={S.summary}>{ra.executive_summary}</div>

        {/* Tabs */}
        <div style={S.tabBar}>
          {TABS.map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)}
              style={{ ...S.tabBtn, ...(tab === key ? S.tabBtnActive : {}) }}>
              {label}
            </button>
          ))}
        </div>

        {/* ─── OVERVIEW ─── */}
        {tab === 'overview' && (
          <div>
            {/* Industry Benchmark + Historical Tracking */}
            <div style={S.two}>
              <Card>
                <CardTitle sub="Where this company sits relative to industry peers">Industry Benchmarking</CardTitle>
                {benchmark && !benchmark.error ? (
                  <div>
                    <div style={{ display: 'flex', gap: 24, marginBottom: 16, alignItems: 'flex-end' }}>
                      <div>
                        <div style={S.metricL}>This Company</div>
                        <div style={{ fontSize: 36, fontWeight: 800, color: rColor(score) }}>{score.toFixed(1)}</div>
                      </div>
                      <div style={{ fontSize: 24, color: 'var(--text-3)', paddingBottom: 4 }}>vs</div>
                      <div>
                        <div style={S.metricL}>{benchmark.industry} Average</div>
                        <div style={{ fontSize: 36, fontWeight: 800, color: 'var(--text-2)' }}>{benchmark.industry_avg_score}</div>
                      </div>
                    </div>
                    <div style={{ ...S.benchBar, background: 'var(--surface-2)', borderRadius: 6, height: 8, marginBottom: 12, position: 'relative' }}>
                      <div style={{ position: 'absolute', left: `${benchmark.industry_avg_score}%`, top: -3, width: 2, height: 14, background: 'var(--text-3)', borderRadius: 1 }} />
                      <div style={{ width: `${score}%`, height: '100%', background: rHex(score), borderRadius: 6 }} />
                    </div>
                    <div style={{ ...S.benchTag, color: benchmark.color === 'green' ? 'var(--green)' : benchmark.color === 'red' ? 'var(--red)' : 'var(--amber)' }}>
                      {benchmark.percentile_label}
                    </div>
                    <div style={S.benchContext}>{benchmark.comparison} — {benchmark.industry} sector ({benchmark.companies_in_benchmark} companies)</div>
                  </div>
                ) : overviewLoaded ? <div style={S.noData}>{benchmark?.error || 'Benchmark data unavailable for this company.'}</div> : <div style={S.loading}>Loading benchmark data...</div>}
              </Card>

              <Card>
                <CardTitle sub="Risk score trajectory across analyses">Historical Risk Tracking</CardTitle>
                {historyData.length > 1 ? (
                  <>
                  <ResponsiveContainer width="100%" height={160}>
                    <AreaChart data={historyData}>
                      <XAxis dataKey="label" stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
                      <YAxis domain={[0, 100]} stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
                      <Tooltip contentStyle={{ background: 'white', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                      <Area type="monotone" dataKey="score" stroke="var(--accent-2)" fill="#EFF6FF" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                  <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 8 }}>
                    {`${historyCount} analyses captured for this company.`}
                  </div>
                  </>
                ) : historyCount === 1 ? (
                  <div style={S.noData}>
                    <div style={{ fontSize: 13, color: 'var(--text-2)', marginBottom: 6 }}>
                      Latest risk score: {historyData[0].score?.toFixed ? historyData[0].score.toFixed(1) : historyData[0].score}/100
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
                      Only one completed analysis exists. Re-run analysis to build a risk trend over time.
                    </div>
                  </div>
                ) : (
                  <div style={S.noData}>
                    <div style={{ fontSize: 13, color: 'var(--text-2)', marginBottom: 6 }}>No historical analyses found.</div>
                    <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Run an analysis to start tracking risk changes over time.</div>
                  </div>
                )}
              </Card>
            </div>

            {/* Acquisition Premium */}
            {premium && !premium.error && (
              <Card style={{ borderLeft: '4px solid var(--accent)' }}>
                <CardTitle sub="ML-estimated acquisition premium based on risk profile and comparable deals">Acquisition Premium Estimate</CardTitle>
                <div style={{ display: 'flex', gap: 40, alignItems: 'center' }}>
                  <div style={{ textAlign: 'center', flexShrink: 0 }}>
                    <div style={S.metricL}>Estimated Premium</div>
                    <div style={{ fontSize: 40, fontWeight: 800, color: 'var(--accent)', letterSpacing: '-1px' }}>
                      {premium.estimated_premium_pct}%
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Range: {premium.premium_range_low}% – {premium.premium_range_high}%</div>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                      <Chip color="var(--accent)" bg="#EFF6FF">{premium.deal_type}</Chip>
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6, marginBottom: 8 }}>{premium.context}</p>
                    <p style={{ fontSize: 11, color: 'var(--text-3)', fontStyle: 'italic' }}>{premium.methodology}</p>
                  </div>
                </div>
              </Card>
            )}

            {/* SHAP + Data Sources */}
            <div style={S.two}>
              <Card>
                <CardTitle sub="SHAP attribution — contribution of each signal to the risk score">Risk Factor Breakdown</CardTitle>
                {ra.shap_explanation?.slice(0, 8).map(s => (
                  <div key={s.feature} style={S.shap}>
                    <div style={S.shapLabel}>{s.description}</div>
                    <div style={S.shapBar}>
                      <div style={{ ...S.shapFill, width: `${Math.min(Math.abs(s.shap_value) * 12, 100)}%`, background: s.shap_value > 0 ? 'var(--red)' : 'var(--green)' }} />
                    </div>
                    <div style={{ ...S.shapNum, color: s.shap_value > 0 ? 'var(--red)' : 'var(--green)' }}>
                      {s.shap_value > 0 ? '+' : ''}{s.shap_value.toFixed(2)}
                    </div>
                  </div>
                ))}
              </Card>
              <div>
                <Card>
                  <CardTitle sub="Sources ingested for this analysis">Data Sources</CardTitle>
                  {[['SEC Financial Filings', 'Analyzed'], ['News Articles', ingestion_stats?.news_articles || 0],
                    ['Patent Filings', ingestion_stats?.patents || 0], ['Job Postings', ingestion_stats?.job_postings || 0]
                  ].map(([label, val]) => (
                    <div key={label} style={S.dataRow}>
                      <span style={S.dataLabel}>{label}</span>
                      <span style={{ ...S.dataVal, color: 'var(--green)' }}>{val}</span>
                    </div>
                  ))}
                </Card>
                <Card style={{ borderColor: as_.hiring_red_flags?.length > 0 ? '#FECACA' : 'var(--border)' }}>
                  <CardTitle sub="Concerns identified across all signals">Risk Indicators</CardTitle>
                  {as_.hiring_red_flags?.length > 0 ? (
                    as_.hiring_red_flags.map((f, i) => (
                      <div key={i} style={S.flagRow}>
                        <Chip color="var(--red)" bg="var(--red-bg)">{f.type?.replace(/_/g, ' ')}</Chip>
                        <span style={S.flagText}>{f.description}</span>
                      </div>
                    ))
                  ) : (
                    <div style={{ fontSize: 13, color: 'var(--green)', padding: '4px 0' }}>
                      ✓ No significant risk indicators detected.
                    </div>
                  )}
                </Card>
              </div>
            </div>
          </div>
        )}

        {/* ─── FINANCIALS ─── */}
        {tab === 'financials' && (
          <div>
            <Card>
              <CardTitle sub={`Revenue and net income over 5+ years (${financials?.currency || "USD Billions"})`}>Revenue & Profit Trend</CardTitle>
              {finChartData.length > 0 ? (
                <>
                <ResponsiveContainer width="100%" height={260}>
                  <ComposedChart data={finChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="year" stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
                    <YAxis stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} unit="B" />
                    <Tooltip contentStyle={{ background: 'white', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
                      formatter={(v, n) => [v ? `$${v.toFixed(1)}B` : 'N/A', n]} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    {hasRevenue && <Bar dataKey="Revenue" fill="#3B82F6" radius={[2, 2, 0, 0]} opacity={0.85} />}
                    {hasNetIncome && <Line type="monotone" dataKey="Net Income" stroke="#15803D" strokeWidth={2} dot={{ r: 4 }} connectNulls />}
                  </ComposedChart>
                </ResponsiveContainer>
                {(!hasRevenue || !hasNetIncome) && (
                  <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 8 }}>
                    Missing series:
                    {!hasRevenue ? ' Revenue' : ''}
                    {!hasRevenue && !hasNetIncome ? ' and' : ''}
                    {!hasNetIncome ? ' Net income' : ''}.
                  </div>
                )}
                </>
              ) : financials?.error ? <div style={S.noData}>{financials.error}</div> : <div style={S.loading}>Loading financial data...</div>}
            </Card>
            <div style={S.two}>
              <Card>
                <CardTitle sub={`Total debt vs cash reserves (${financials?.currency || "USD Billions"})`}>Debt & Cash Position</CardTitle>
                {finChartData.length > 0 ? (
                  <>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={finChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="year" stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
                      <YAxis stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} unit="B" />
                      <Tooltip contentStyle={{ background: 'white', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
                        formatter={(v, n) => [v ? `$${v.toFixed(1)}B` : 'N/A', n]} />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      {hasDebt && <Bar dataKey="Debt" fill="#B91C1C" radius={[2, 2, 0, 0]} opacity={0.8} />}
                      {hasCash && <Bar dataKey="Cash" fill="#15803D" radius={[2, 2, 0, 0]} opacity={0.8} />}
                    </BarChart>
                  </ResponsiveContainer>
                  {(!hasDebt || !hasCash) && (
                    <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 8 }}>
                      Missing series:
                      {!hasDebt ? ' Debt' : ''}
                      {!hasDebt && !hasCash ? ' and' : ''}
                      {!hasCash ? ' Cash' : ''}.
                    </div>
                  )}
                  </>
                ) : financials?.error ? <div style={S.noData}>{financials.error}</div> : <div style={S.loading}>Loading...</div>}
              </Card>
              <Card>
                <CardTitle sub="Detected statistical outliers in financial patterns">Financial Anomalies</CardTitle>
                {ad?.anomalies?.anomalies?.length > 0 ? (
                  ad.anomalies.anomalies.map((a, i) => (
                    <div key={i} style={{ padding: '10px 0', borderBottom: '1px solid var(--bg)' }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                        <Chip color={a.severity === 'high' ? 'var(--red)' : 'var(--amber)'}
                          bg={a.severity === 'high' ? 'var(--red-bg)' : 'var(--amber-bg)'}>
                          {a.severity}
                        </Chip>
                        <span style={{ fontSize: 11, color: 'var(--text-3)' }}>{a.date}</span>
                      </div>
                      <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.5 }}>{a.explanation}</p>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: 13, color: 'var(--green)', padding: '8px 0' }}>
                    ✓ No financial anomalies detected across {ad?.anomalies?.total_periods_analyzed || 0} periods analyzed.
                  </div>
                )}
              </Card>
            </div>
          </div>
        )}

        {/* ─── SENTIMENT & NEWS ─── */}
        {tab === 'sentiment' && (
          <div>
            <Card>
              <CardTitle sub="Monthly average sentiment — FinBERT financial NLP model">24-Month Sentiment Timeline</CardTitle>
              {timeline.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={timeline}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="month" stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} interval={2} />
                    <YAxis domain={[0, 1]} stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
                    <Tooltip contentStyle={{ background: 'white', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                    <Area type="monotone" dataKey="avg_sentiment" stroke="var(--accent-2)" fill="#EFF6FF" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <div style={S.noData}>Sentiment timeline not available</div>}
            </Card>

            <div style={S.metricRow}>
              {[['Overall Score', ad?.sentiment?.overall_score?.toFixed(3)],
                ['Recent 90D Score', ad?.sentiment?.recent_score_90d?.toFixed(3)],
                ['Articles Analyzed', ad?.sentiment?.total_articles_analyzed],
                ['Trend Direction', ad?.sentiment?.sentiment_trend?.toUpperCase()]
              ].map(([l, v]) => (
                <Card key={l} style={{ flex: 1, marginBottom: 0 }}>
                  <div style={S.metricL}>{l}</div>
                  <div style={S.metricV}>{v || '—'}</div>
                </Card>
              ))}
            </div>

            {/* Top news articles */}
            {newsData && (
              <div style={S.two}>
                <Card>
                  <CardTitle sub="Most positive news coverage">Top Positive Headlines</CardTitle>
                  {newsData.positive?.length > 0 ? newsData.positive.map((a, i) => (
                    <div key={i} style={S.newsRow}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                        <span style={{ fontSize: 10, color: 'var(--text-3)' }}>{a.source} · {a.date}</span>
                        <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--green)' }}>{a.sentiment_score}</span>
                      </div>
                      <p style={S.newsHeadline}>{a.headline}</p>
                    </div>
                  )) : <div style={S.noData}>No positive articles found</div>}
                </Card>
                <Card>
                  <CardTitle sub="Most negative news coverage">Top Negative Headlines</CardTitle>
                  {newsData.negative?.length > 0 ? newsData.negative.map((a, i) => (
                    <div key={i} style={S.newsRow}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                        <span style={{ fontSize: 10, color: 'var(--text-3)' }}>{a.source} · {a.date}</span>
                        <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--red)' }}>{a.sentiment_score}</span>
                      </div>
                      <p style={S.newsHeadline}>{a.headline}</p>
                    </div>
                  )) : <div style={S.noData}>No negative articles found</div>}
                </Card>
              </div>
            )}

            {/* Recent news */}
            {newsData?.recent?.length > 0 && (
              <Card>
                <CardTitle sub="Latest 10 articles analyzed">Recent News Coverage</CardTitle>
                {newsData.recent.map((a, i) => (
                  <div key={i} style={S.newsRow}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                      <span style={{ fontSize: 10, color: 'var(--text-3)' }}>{a.source} · {a.date}</span>
                      <span style={{ fontSize: 10, fontWeight: 700, color: a.sentiment_score > 0.6 ? 'var(--green)' : a.sentiment_score < 0.4 ? 'var(--red)' : 'var(--text-3)' }}>
                        {a.sentiment_score > 0.6 ? '▲' : a.sentiment_score < 0.4 ? '▼' : '—'} {a.sentiment_score}
                      </span>
                    </div>
                    <p style={S.newsHeadline}>{a.headline}</p>
                  </div>
                ))}
              </Card>
            )}
          </div>
        )}

        {/* ─── HIRING ─── */}
        {tab === 'hiring' && (
          <div>
            <Card>
              <CardTitle sub="% change in hiring rate by department">Hiring Velocity by Department</CardTitle>
              {depts.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={depts} margin={{ bottom: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="department" stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
                    <YAxis stroke="var(--border-strong)" tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
                    <Tooltip contentStyle={{ background: 'white', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }} />
                    <Bar dataKey="velocity_change_pct" radius={[3, 3, 0, 0]}>
                      {depts.map((d, i) => <Cell key={i} fill={d.velocity_change_pct > 0 ? '#15803D' : '#B91C1C'} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : <div style={S.noData}>Hiring data not available</div>}
            </Card>
            <Card>
              <CardTitle>Department Detail</CardTitle>
              <table style={S.table}>
                <thead>
                  <tr>{['Department', 'Postings', 'Trend', 'Change', 'Senior Ratio'].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {depts.map(d => (
                    <tr key={d.department} style={S.tr}>
                      <td style={{ ...S.td, fontWeight: 600 }}>{d.department}</td>
                      <td style={S.td}>{d.total_postings}</td>
                      <td style={S.td}>
                        <Chip color={d.trend === 'accelerating' ? 'var(--green)' : d.trend === 'decelerating' ? 'var(--red)' : 'var(--text-2)'}
                          bg={d.trend === 'accelerating' ? 'var(--green-bg)' : d.trend === 'decelerating' ? 'var(--red-bg)' : 'var(--surface-2)'}>
                          {d.trend}
                        </Chip>
                      </td>
                      <td style={{ ...S.td, fontWeight: 600, color: d.velocity_change_pct > 0 ? 'var(--green)' : 'var(--red)' }}>
                        {d.velocity_change_pct > 0 ? '+' : ''}{d.velocity_change_pct?.toFixed(1)}%
                      </td>
                      <td style={S.td}>{d.senior_ratio ? `${(d.senior_ratio * 100).toFixed(0)}%` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        )}

        {/* ─── REPORT ─── */}
        {tab === 'report' && (
          <div>
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>Due Diligence Report</div>
                  <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>AI-generated · {company_name}</div>
                </div>
                <button onClick={() => window.open(`/api/report/${company_id}/pdf`, '_blank')} style={S.exportBtn}>
                  Export PDF
                </button>
              </div>
              <div style={S.reportBody}>
                {report?.split('\n').map((line, i) => {
                  if (line.startsWith('## ')) return <h3 key={i} style={S.rH2}>{line.slice(3)}</h3>;
                  if (line.startsWith('# ')) return <h2 key={i} style={S.rH1}>{line.slice(2)}</h2>;
                  if (line.startsWith('- ') || line.startsWith('• ')) return <li key={i} style={S.rLi}>{line.slice(2)}</li>;
                  if (!line.trim()) return <div key={i} style={{ height: 10 }} />;
                  return <p key={i} style={S.rP}>{line}</p>;
                })}
              </div>
            </Card>
            <Card>
              <CardTitle sub="Receive email alerts when the risk score changes significantly">Add to Watchlist</CardTitle>
              <div style={{ display: 'flex', gap: 8 }}>
                <input value={wEmail} onChange={e => setWEmail(e.target.value)}
                  placeholder="your@email.com"
                  style={{ flex: 1, padding: '10px 14px', border: '1.5px solid var(--border-strong)', borderRadius: 6, fontSize: 14, fontFamily: 'inherit', outline: 'none', background: 'var(--bg)', color: 'var(--text-1)' }} />
                <button onClick={addWatch} style={S.btnPrimary}>Monitor {company_name}</button>
              </div>
              {wMsg && <p style={{ fontSize: 12, color: wMsg.includes('Error') ? 'var(--red)' : 'var(--green)', marginTop: 8 }}>{wMsg}</p>}
            </Card>
          </div>
        )}

        {/* ─── COMPETITORS ─── */}
        {tab === 'competitors' && (
          <Card>
            <CardTitle sub="Risk profiles of top industry peers vs target company">Competitor Benchmarking</CardTitle>
            {!competitors?.length ? <div style={S.noData}>Competitor data not available.</div> : (
              <table style={S.table}>
                <thead>
                  <tr>{['Company', 'Risk Score', 'Category', 'Sentiment', 'Hiring Health'].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  <tr style={{ ...S.tr, background: 'var(--green-bg)' }}>
                    <td style={{ ...S.td, fontWeight: 700 }}>
                      {company_name} <Chip color="var(--green)" bg="var(--green-bg)">TARGET</Chip>
                    </td>
                    <td style={{ ...S.td, fontWeight: 800, fontSize: 18, color: rColor(score) }}>{score.toFixed(1)}</td>
                    <td style={S.td}><Chip color={categoryColor(ra.risk_category, score)} bg={categoryBg(ra.risk_category, score)}>{categoryLabel(ra.risk_category, score)}</Chip></td>
                    <td style={S.td}>{as_.sentiment_score?.toFixed(2)}</td>
                    <td style={S.td}>{as_.hiring_health_score}/100</td>
                  </tr>
                  {competitors.map((c, i) => (
                    <tr key={i} style={S.tr}>
                      <td style={{ ...S.td, fontWeight: 600 }}>{c.company_name}</td>
                      <td style={{ ...S.td, fontWeight: 800, fontSize: 18, color: typeof c.risk_score === 'number' ? rColor(c.risk_score) : 'var(--text-3)' }}>{typeof c.risk_score === 'number' ? c.risk_score.toFixed(1) : '—'}</td>
                      <td style={S.td}><Chip color={categoryColor(c.risk_category, c.risk_score)} bg={categoryBg(c.risk_category, c.risk_score)}>{categoryLabel(c.risk_category, c.risk_score)}</Chip></td>
                      <td style={S.td}>{typeof c.sentiment_score === 'number' ? c.sentiment_score.toFixed(2) : '—'}</td>
                      <td style={S.td}>{typeof c.hiring_health === 'number' ? `${c.hiring_health}/100` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}

const S = {
  header: { background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '14px 0' },
  headerInner: { maxWidth: 1100, margin: '0 auto', padding: '0 40px' },
  backBtn: { background: 'none', border: 'none', color: 'var(--text-3)', fontSize: 13, cursor: 'pointer', padding: '0 0 10px', fontFamily: 'inherit', display: 'block' },
  compRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  compName: { fontFamily: "'Playfair Display', serif", fontSize: 28, fontWeight: 600, color: 'var(--text-1)', letterSpacing: '-0.3px', marginBottom: 4 },
  exportBtn: { background: 'var(--surface)', border: '1px solid var(--border-strong)', color: 'var(--text-1)', padding: '8px 16px', borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' },
  body: { maxWidth: 1100, margin: '0 auto', padding: '28px 40px 80px' },
  riskPanel: { display: 'grid', gridTemplateColumns: '220px 1fr', gap: 16, marginBottom: 16 },
  scoreBox: { border: '1px solid', borderRadius: 8, padding: '22px 20px', textAlign: 'center' },
  scoreNum: { fontFamily: "'Playfair Display', serif", fontSize: 56, fontWeight: 600, lineHeight: 1, marginTop: 12, letterSpacing: '-2px' },
  scoreOf: { fontSize: 12, color: 'var(--text-3)', marginTop: 2 },
  scoreRec: { fontSize: 12, color: 'var(--text-2)', marginTop: 12, lineHeight: 1.5, fontStyle: 'italic' },
  signals: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 },
  sig: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 7, padding: '14px 16px' },
  sigAlert: { borderColor: '#FECACA', background: 'var(--red-bg)' },
  sigLabel: { fontSize: 10, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 },
  sigVal: { fontSize: 20, fontWeight: 800, letterSpacing: '-0.3px' },
  sigUnit: { fontSize: 11, color: 'var(--text-3)', marginTop: 2 },
  summary: { background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 7, padding: '14px 18px', fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6, marginBottom: 20 },
  tabBar: { display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 20 },
  tabBtn: { padding: '9px 16px', background: 'none', border: 'none', color: 'var(--text-3)', fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', borderBottom: '2px solid transparent', marginBottom: -1 },
  tabBtnActive: { color: 'var(--text-1)', borderBottomColor: 'var(--accent)', fontWeight: 600 },
  two: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  shap: { display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: '1px solid var(--bg)' },
  shapLabel: { flex: '0 0 190px', fontSize: 12, color: 'var(--text-2)' },
  shapBar: { flex: 1, height: 5, background: 'var(--surface-2)', borderRadius: 2, overflow: 'hidden' },
  shapFill: { height: '100%', borderRadius: 2, minWidth: 2 },
  shapNum: { flex: '0 0 48px', fontSize: 12, fontWeight: 700, textAlign: 'right' },
  dataRow: { display: 'flex', justifyContent: 'space-between', padding: '9px 0', borderBottom: '1px solid var(--bg)', fontSize: 13 },
  dataLabel: { color: 'var(--text-2)' },
  dataVal: { fontWeight: 700 },
  flagRow: { display: 'flex', gap: 10, alignItems: 'flex-start', padding: '8px 0', borderBottom: '1px solid #FEE2E2' },
  flagText: { fontSize: 12, color: 'var(--text-2)', lineHeight: 1.5 },
  metricRow: { display: 'flex', gap: 12, marginBottom: 16 },
  metricL: { fontSize: 10, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 },
  metricV: { fontSize: 18, fontWeight: 700, color: 'var(--text-1)' },
  benchBar: {},
  benchTag: { fontSize: 13, fontWeight: 600, marginBottom: 4 },
  benchContext: { fontSize: 12, color: 'var(--text-3)' },
  loading: { color: 'var(--text-3)', fontSize: 13, padding: '24px 0', textAlign: 'center' },
  noData: { color: 'var(--text-3)', fontSize: 13, padding: '24px 0', textAlign: 'center' },
  newsRow: { padding: '10px 0', borderBottom: '1px solid var(--bg)' },
  newsHeadline: { fontSize: 13, color: 'var(--text-1)', lineHeight: 1.5, fontWeight: 500 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { fontSize: 10, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '8px 12px', textAlign: 'left', borderBottom: '1px solid var(--border)' },
  tr: { borderBottom: '1px solid var(--bg)' },
  td: { fontSize: 13, color: 'var(--text-2)', padding: '12px' },
  reportBody: { fontSize: 14, color: 'var(--text-2)', lineHeight: 1.8 },
  rH1: { fontFamily: "'Playfair Display', serif", fontSize: 20, fontWeight: 600, color: 'var(--text-1)', margin: '24px 0 10px', borderTop: '1px solid var(--border)', paddingTop: 16 },
  rH2: { fontSize: 14, fontWeight: 700, color: 'var(--text-1)', margin: '18px 0 8px' },
  rP: { marginBottom: 8 },
  rLi: { marginLeft: 16, marginBottom: 4 },
  btnPrimary: { background: 'var(--accent)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' },
};
