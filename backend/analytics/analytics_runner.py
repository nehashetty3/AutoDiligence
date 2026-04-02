import time
from backend.analytics.anomaly_detection import detect_anomalies
from backend.analytics.sentiment_analysis import analyze_company_sentiment
from backend.analytics.entity_extraction import analyze_company_entities
from backend.analytics.patent_clustering import analyze_patent_clusters
from backend.analytics.hiring_analysis import analyze_hiring_patterns

def run_full_analytics(company_id: int) -> dict:
    print(f"\n[Analytics] Starting full analytics for company {company_id}")
    results = {}
    steps = [
        ("anomalies", detect_anomalies, "Financial Anomaly Detection"),
        ("sentiment", analyze_company_sentiment, "News Sentiment Analysis"),
        ("entities", analyze_company_entities, "Entity Extraction"),
        ("patents", analyze_patent_clusters, "Patent Clustering"),
        ("hiring", analyze_hiring_patterns, "Hiring Analysis"),
    ]
    for key, func, name in steps:
        print(f"[Analytics] Running {name}...")
        try:
            results[key] = func(company_id)
        except Exception as e:
            print(f"[Analytics] Error in {name}: {e}")
            results[key] = {}
        time.sleep(0.2)
    results['summary'] = {
        "financial_risk_level": results.get('anomalies', {}).get('risk_level', 'unknown'),
        "financial_anomaly_count": results.get('anomalies', {}).get('anomaly_count', 0),
        "sentiment_trend": results.get('sentiment', {}).get('sentiment_trend', 'unknown'),
        "overall_sentiment": results.get('sentiment', {}).get('overall_sentiment', 'neutral'),
        "sentiment_score": results.get('sentiment', {}).get('overall_score', 0.5),
        "recent_sentiment_score": results.get('sentiment', {}).get('recent_score_90d', 0.5),
        "patent_velocity": results.get('patents', {}).get('velocity', {}).get('trend', 'unknown'),
        "dominant_innovation_area": results.get('patents', {}).get('dominant_innovation_area', 'unknown'),
        "total_patents": results.get('patents', {}).get('total_patents_analyzed', 0),
        "hiring_trend": results.get('hiring', {}).get('overall_hiring_trend', 'unknown'),
        "hiring_health_score": results.get('hiring', {}).get('hiring_health_score', 50),
        "hiring_red_flags": results.get('hiring', {}).get('red_flags', []),
        "key_risk_factors": results.get('entities', {}).get('top_risk_factors', [])[:5],
        "key_competitors": [o['name'] for o in results.get('entities', {}).get('key_organizations', [])[:5]]
    }
    print(f"[Analytics] Complete for company {company_id}")
    return results
