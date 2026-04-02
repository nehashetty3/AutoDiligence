from statistics import mean, median

from backend.database.schema import SessionLocal, RiskAssessment, Company


INDUSTRY_PRIORS = {
    "technology": {"avg": 39, "label": "Technology"},
    "finance": {"avg": 50, "label": "Financial Services"},
    "healthcare": {"avg": 43, "label": "Healthcare & Pharma"},
    "energy": {"avg": 56, "label": "Energy & Resources"},
    "retail": {"avg": 48, "label": "Retail & Consumer"},
    "automotive": {"avg": 54, "label": "Automotive"},
    "telecom": {"avg": 49, "label": "Telecommunications"},
    "industrial": {"avg": 51, "label": "Industrial & Manufacturing"},
    "default": {"avg": 47, "label": "Cross-sector"},
}


def detect_industry(company_name: str, ticker: str) -> str:
    name = (company_name or "").lower()
    ticker = (ticker or "").upper()

    if any(w in name for w in [
        "bank", "finance", "financial", "invest", "capital", "insurance", "payments",
        "goldman", "jpmorgan", "morgan stanley", "blackrock", "hdfc", "icici", "fifth third",
        "state street", "bancshares", "mellon", "pnc"
    ]) or ticker in {"GS", "JPM", "MS", "BK", "PNC", "STT", "FITB", "HBAN", "HDB", "IBN", "BLK"}:
        return "finance"

    if any(w in name for w in [
        "software", "cloud", "data", "digital", "technology", "technologies", "semiconductor",
        "ai", "cyber", "internet", "meta", "microsoft", "apple", "amazon", "nvidia",
        "infosys", "wipro", "consultancy", "hcl"
    ]) or ticker in {"MSFT", "AAPL", "AMZN", "META", "NVDA", "INFY", "WIT", "TCS", "TCS.NS", "HCLTECH.NS", "BTCS"}:
        return "technology"

    if any(w in name for w in [
        "pharma", "health", "medical", "bio", "biotech", "hospital", "therapeutics"
    ]):
        return "healthcare"

    if any(w in name for w in [
        "oil", "gas", "energy", "petro", "power", "solar", "renewable"
    ]):
        return "energy"

    if any(w in name for w in [
        "retail", "consumer", "store", "mart", "ecommerce", "shop"
    ]):
        return "retail"

    if any(w in name for w in [
        "auto", "motor", "vehicle", "car", "automotive", "tesla", "toyota", "volkswagen"
    ]) or ticker in {"TSLA", "TM", "VOW.PR"}:
        return "automotive"

    if any(w in name for w in [
        "telecom", "wireless", "network", "mobile"
    ]):
        return "telecom"

    if any(w in name for w in [
        "industrial", "manufacturing", "steel", "mining", "cement", "infrastructure", "port"
    ]):
        return "industrial"

    return "default"


def _latest_scores_by_company():
    db = SessionLocal()
    try:
        latest = {}
        for ra in db.query(RiskAssessment).order_by(RiskAssessment.created_at).all():
            latest[ra.company_id] = ra

        rows = []
        for company in db.query(Company).all():
            ra = latest.get(company.id)
            if not ra:
                continue
            rows.append({
                "company_id": company.id,
                "name": company.name,
                "ticker": company.ticker,
                "industry": detect_industry(company.name, company.ticker),
                "risk_score": float(ra.risk_score),
            })
        return rows
    finally:
        db.close()


def get_industry_benchmark(company_name: str, ticker: str, risk_score: float) -> dict:
    industry_key = detect_industry(company_name, ticker)
    prior = INDUSTRY_PRIORS.get(industry_key, INDUSTRY_PRIORS["default"])

    latest_scores = _latest_scores_by_company()
    peers = [row for row in latest_scores if row["industry"] == industry_key]
    peer_scores = [row["risk_score"] for row in peers]

    if len(peer_scores) >= 3:
        industry_avg = round(mean(peer_scores), 1)
        industry_median = round(median(peer_scores), 1)
        percentile = round((sum(1 for s in peer_scores if s < risk_score) / len(peer_scores)) * 100)
        source = "live_peer_set"
        benchmark_size = len(peer_scores)
    else:
        industry_avg = prior["avg"]
        industry_median = prior["avg"]
        percentile = round(max(0, min(100, 50 + ((risk_score - prior["avg"]) * 2.2))))
        source = "sector_prior"
        benchmark_size = len(peer_scores)

    diff = round(risk_score - industry_avg, 1)

    if diff <= -12:
        comparison = "materially lower risk than industry peers"
        color = "green"
    elif diff < -4:
        comparison = "moderately lower risk than industry peers"
        color = "green"
    elif diff < 5:
        comparison = "broadly in line with industry peers"
        color = "amber"
    elif diff < 12:
        comparison = "moderately higher risk than industry peers"
        color = "red"
    else:
        comparison = "materially higher risk than industry peers"
        color = "red"

    if percentile < 25:
        percentile_label = f"Lower risk than roughly {100 - percentile}% of comparable companies"
    elif percentile < 50:
        percentile_label = f"Slightly lower risk than comparable companies"
    elif percentile < 75:
        percentile_label = f"Slightly higher risk than comparable companies"
    else:
        percentile_label = f"Higher risk than roughly {percentile}% of comparable companies"

    return {
        "industry": prior["label"],
        "industry_avg_score": industry_avg,
        "industry_median_score": industry_median,
        "company_score": round(risk_score, 1),
        "difference": diff,
        "comparison": comparison,
        "color": color,
        "percentile": percentile,
        "percentile_label": percentile_label,
        "companies_in_benchmark": benchmark_size,
        "benchmark_source": source,
    }
