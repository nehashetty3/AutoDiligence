from backend.analytics.industry_benchmark import detect_industry, get_industry_benchmark


BASE_PREMIUM_BY_INDUSTRY = {
    "technology": 27.0,
    "finance": 16.0,
    "healthcare": 24.0,
    "energy": 14.0,
    "retail": 18.0,
    "automotive": 17.0,
    "telecom": 15.0,
    "industrial": 16.0,
    "default": 18.0,
}


def predict_acquisition_premium(
    risk_score: float,
    analytics_summary: dict,
    company_name: str = "",
    ticker: str = "",
) -> dict:
    """Sector-aware heuristic premium model grounded in risk and peer positioning."""
    industry_key = detect_industry(company_name, ticker)
    benchmark = get_industry_benchmark(company_name, ticker, risk_score)
    base = BASE_PREMIUM_BY_INDUSTRY.get(industry_key, BASE_PREMIUM_BY_INDUSTRY["default"])

    sentiment_score = float(analytics_summary.get("sentiment_score", 0.5) or 0.5)
    patent_velocity = analytics_summary.get("patent_velocity", "stable")
    hiring_health_score = float(analytics_summary.get("hiring_health_score", 50) or 50)
    anomaly_count = float(analytics_summary.get("financial_anomaly_count", 0) or 0)

    premium = base
    premium -= max(0.0, (risk_score - 35.0) * 0.34)
    premium += (sentiment_score - 0.5) * 16.0
    premium += (hiring_health_score - 50.0) * 0.07
    premium -= anomaly_count * 2.6
    premium += {
        "accelerating": 3.0,
        "stable": 0.0,
        "decelerating": -3.0,
    }.get(patent_velocity, 0.0)

    diff = benchmark.get("difference", 0.0)
    premium += max(-6.0, min(4.0, -diff * 0.28))

    if risk_score < 35:
        deal_type = "Strategic acquisition"
        floor, ceiling = 16.0, 42.0
    elif risk_score < 60:
        deal_type = "Conditional acquisition"
        floor, ceiling = 10.0, 28.0
    else:
        deal_type = "Structured / turnaround acquisition"
        floor, ceiling = 4.0, 18.0

    estimated = max(floor, min(ceiling, premium))
    uncertainty = 4.0 + min(4.0, anomaly_count) + (3.0 if benchmark.get("benchmark_source") != "live_peer_set" else 0.0)
    lower = max(floor, estimated - uncertainty)
    upper = min(ceiling, estimated + uncertainty)

    if diff <= -8:
        context = "Target screens safer than its peer set, supporting the upper half of the range if strategic fit is strong."
    elif diff >= 8:
        context = "Target screens riskier than its peer set, so buyers would usually demand structure, earnouts, or price protection."
    else:
        context = "Target screens broadly in line with peers, so premium should depend mainly on strategy, synergy, and execution confidence."

    return {
        "estimated_premium_pct": round(estimated, 1),
        "premium_range_low": round(lower, 1),
        "premium_range_high": round(upper, 1),
        "deal_type": deal_type,
        "context": context,
        "methodology": "Sector-aware heuristic calibrated from risk score, peer-relative benchmark position, sentiment, hiring health, innovation trend, and anomaly count.",
    }
