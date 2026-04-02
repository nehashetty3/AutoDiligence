import numpy as np
import pandas as pd

def get_feature_names() -> list:
    return [
        'financial_anomaly_count', 'financial_risk_encoded', 'revenue_growth',
        'profit_margin', 'debt_to_cash', 'cash_change', 'sentiment_score',
        'recent_sentiment_score', 'sentiment_momentum', 'sentiment_trend_encoded',
        'negative_article_ratio', 'patent_velocity_encoded', 'patent_velocity_change_pct',
        'innovation_diversity_score', 'total_patents_normalized', 'hiring_health_score',
        'hiring_red_flag_count', 'hiring_trend_encoded', 'executive_mention_count',
        'competitor_mention_count', 'risk_statement_count'
    ]

def get_feature_descriptions() -> dict:
    return {
        'financial_anomaly_count': 'Number of financial anomalies detected',
        'financial_risk_encoded': 'Overall financial risk level',
        'revenue_growth': 'Average revenue growth rate',
        'profit_margin': 'Latest profit margin',
        'debt_to_cash': 'Debt to cash ratio',
        'cash_change': 'Cash reserve change rate',
        'sentiment_score': 'Overall news sentiment score',
        'recent_sentiment_score': 'Recent 90-day sentiment score',
        'sentiment_momentum': 'Sentiment trend momentum',
        'sentiment_trend_encoded': 'Sentiment direction',
        'negative_article_ratio': 'Proportion of negative news',
        'patent_velocity_encoded': 'Patent filing trend direction',
        'patent_velocity_change_pct': 'Patent velocity change',
        'innovation_diversity_score': 'Innovation domain diversity',
        'total_patents_normalized': 'Normalized patent count',
        'hiring_health_score': 'Overall hiring health',
        'hiring_red_flag_count': 'Number of hiring red flags',
        'hiring_trend_encoded': 'Overall hiring trajectory',
        'executive_mention_count': 'Key executives mentioned',
        'competitor_mention_count': 'Competitors mentioned',
        'risk_statement_count': 'Risk statements in filings'
    }

def extract_features_from_analytics(analytics_results: dict) -> dict:
    features = {}
    anomaly_data = analytics_results.get('anomalies', {})
    fin_summary = anomaly_data.get('financial_summary', {})
    features['financial_anomaly_count'] = anomaly_data.get('anomaly_count', 0)
    risk_map = {'low': 0, 'medium': 1, 'high': 2, 'unknown': 1}
    features['financial_risk_encoded'] = risk_map.get(anomaly_data.get('risk_level', 'unknown'), 1)
    features['revenue_growth'] = float(fin_summary.get('avg_revenue_growth') or 0.0)
    features['profit_margin'] = float(fin_summary.get('latest_profit_margin') or 0.05)
    features['debt_to_cash'] = min(float(fin_summary.get('latest_debt_to_cash') or 2.0), 20.0)
    features['cash_change'] = 0.0
    sentiment_data = analytics_results.get('sentiment', {})
    features['sentiment_score'] = sentiment_data.get('overall_score', 0.5)
    features['recent_sentiment_score'] = sentiment_data.get('recent_score_90d') or features['sentiment_score']
    features['sentiment_momentum'] = features['recent_sentiment_score'] - features['sentiment_score']
    trend_map = {'improving': 1, 'stable': 0, 'declining': -1, 'unknown': 0}
    features['sentiment_trend_encoded'] = trend_map.get(sentiment_data.get('sentiment_trend', 'unknown'), 0)
    dist = sentiment_data.get('sentiment_distribution', {})
    total = sum(dist.values()) if dist else 1
    features['negative_article_ratio'] = dist.get('negative', 0) / max(total, 1)
    patent_data = analytics_results.get('patents', {})
    velocity_data = patent_data.get('velocity', {})
    vel_map = {'accelerating': 1, 'stable': 0, 'decelerating': -1, 'insufficient_data': 0}
    features['patent_velocity_encoded'] = vel_map.get(velocity_data.get('trend', 'unknown'), 0)
    features['patent_velocity_change_pct'] = np.clip(float(velocity_data.get('velocity_change_pct', 0) or 0) / 100, -1, 1)
    features['innovation_diversity_score'] = patent_data.get('innovation_diversity_score', 0.5)
    features['total_patents_normalized'] = min((patent_data.get('total_patents_analyzed', 0) or 0) / 100, 1.0)
    hiring_data = analytics_results.get('hiring', {})
    features['hiring_health_score'] = (hiring_data.get('hiring_health_score', 50) or 50) / 100
    features['hiring_red_flag_count'] = len(hiring_data.get('red_flags', []))
    hiring_trend_map = {'growing': 1, 'stable': 0, 'shrinking': -1, 'unknown': 0}
    features['hiring_trend_encoded'] = hiring_trend_map.get(hiring_data.get('overall_hiring_trend', 'unknown'), 0)
    entity_data = analytics_results.get('entities', {})
    entity_summary = entity_data.get('summary', {})
    features['executive_mention_count'] = min(entity_summary.get('unique_people_mentioned', 0), 50)
    features['competitor_mention_count'] = min(len(entity_data.get('key_organizations', [])), 30)
    features['risk_statement_count'] = min(entity_summary.get('risk_statements_identified', 0), 100) / 100
    return features

def features_to_dataframe(features: dict) -> pd.DataFrame:
    return pd.DataFrame([features])
