import numpy as np
import pandas as pd
import joblib
import os
import shap
import plotly.graph_objects as go
from backend.models.feature_engineering import (
    extract_features_from_analytics, features_to_dataframe,
    get_feature_names, get_feature_descriptions
)

_classifier = None
_regressor = None
_label_encoder = None
_explainer_cls = None
_explainer_reg = None


def _clip(value: float, low: float, high: float) -> float:
    return float(np.clip(value, low, high))


def _expert_risk_score(features: dict) -> float:
    """Rule-based calibration layer to widen score spread using live analytics."""
    score = 50.0

    score += min(features.get("financial_anomaly_count", 0) * 7.5, 22.0)
    score += features.get("financial_risk_encoded", 1) * 8.0
    score += _clip(-features.get("revenue_growth", 0.0) * 60.0, -14.0, 18.0)
    score += _clip(-features.get("profit_margin", 0.0) * 75.0, -15.0, 18.0)
    score += _clip((features.get("debt_to_cash", 2.0) - 1.5) * 4.0, -8.0, 18.0)
    score += _clip(-features.get("cash_change", 0.0) * 30.0, -8.0, 12.0)

    score += _clip((0.5 - features.get("sentiment_score", 0.5)) * 34.0, -12.0, 12.0)
    score += _clip((0.5 - features.get("recent_sentiment_score", 0.5)) * 20.0, -8.0, 8.0)
    score += _clip(-features.get("sentiment_momentum", 0.0) * 30.0, -8.0, 8.0)
    score += _clip(features.get("negative_article_ratio", 0.0) * 18.0, 0.0, 14.0)

    score += -features.get("patent_velocity_encoded", 0) * 4.0
    score += _clip(-features.get("patent_velocity_change_pct", 0.0) * 16.0, -6.0, 8.0)
    score += _clip((0.45 - features.get("innovation_diversity_score", 0.5)) * 18.0, -6.0, 8.0)
    score += _clip((0.55 - features.get("total_patents_normalized", 0.0)) * 10.0, -4.0, 6.0)

    score += _clip((0.5 - features.get("hiring_health_score", 0.5)) * 28.0, -10.0, 12.0)
    score += min(features.get("hiring_red_flag_count", 0) * 4.5, 14.0)
    score += -features.get("hiring_trend_encoded", 0) * 4.0

    score += _clip((0.25 - features.get("risk_statement_count", 0.0)) * -40.0, -4.0, 12.0)
    score += _clip((5.0 - features.get("executive_mention_count", 0)) * 0.8, -4.0, 6.0)

    return _clip(score, 5.0, 95.0)


def _score_to_category(score: float) -> str:
    if score < 38:
        return "low"
    if score < 67:
        return "medium"
    return "high"


def _score_based_probabilities(score: float) -> dict:
    low = _clip((45.0 - score) / 22.0, 0.0, 1.0)
    high = _clip((score - 58.0) / 22.0, 0.0, 1.0)
    medium = max(0.0, 1.0 - max(low, high))
    total = low + medium + high
    if total == 0:
        return {"low": 0.0, "medium": 1.0, "high": 0.0}
    return {
        "low": round(low / total, 3),
        "medium": round(medium / total, 3),
        "high": round(high / total, 3),
    }

def load_models():
    global _classifier, _regressor, _label_encoder, _explainer_cls, _explainer_reg
    model_path = 'backend/models/saved_models'
    if not os.path.exists(f'{model_path}/risk_classifier.pkl'):
        print("Models not found — training now...")
        from backend.models.model_trainer import train_all_models
        train_all_models()
    if _classifier is None:
        _classifier = joblib.load(f'{model_path}/risk_classifier.pkl')
        _regressor = joblib.load(f'{model_path}/risk_regressor.pkl')
        _label_encoder = joblib.load(f'{model_path}/label_encoder.pkl')
        _explainer_cls = shap.TreeExplainer(_classifier)
        _explainer_reg = shap.TreeExplainer(_regressor)
        print("[Models] Loaded successfully")

def generate_shap_waterfall_html(features_df: pd.DataFrame, company_name: str) -> str:
    load_models()
    feature_names = get_feature_names()
    feature_descriptions = get_feature_descriptions()
    features_df = features_df[feature_names]
    shap_vals = _explainer_reg.shap_values(features_df)[0]
    base_value = float(_explainer_reg.expected_value)
    sorted_idx = np.argsort(np.abs(shap_vals))[::-1][:10]
    labels = [feature_descriptions.get(feature_names[i], feature_names[i]) for i in sorted_idx]
    values = [float(shap_vals[i]) for i in sorted_idx]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"] * len(labels) + ["total"],
        x=labels + ["Final Score"],
        y=values + [sum(values)],
        text=[f"+{v:.1f}" if v > 0 else f"{v:.1f}" for v in values] + [""],
        textposition="outside",
        connector={"line": {"color": "rgb(63,63,63)"}},
        increasing={"marker": {"color": "#EF4444"}},
        decreasing={"marker": {"color": "#22C55E"}},
        totals={"marker": {"color": "#3B82F6"}}
    ))
    fig.update_layout(
        title=f"Risk Score Drivers — {company_name}",
        height=480, plot_bgcolor='white', paper_bgcolor='white',
        font=dict(size=10), showlegend=False,
        margin=dict(l=20, r=20, t=60, b=120)
    )
    fig.update_xaxes(tickangle=-35)
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

def score_company(analytics_results: dict, company_name: str = "Company") -> dict:
    load_models()
    features = extract_features_from_analytics(analytics_results)
    features_df = features_to_dataframe(features)
    feature_names = get_feature_names()
    for col in feature_names:
        if col not in features_df.columns:
            features_df[col] = 0.0
    features_df = features_df[feature_names]

    raw_model_score = float(np.clip(_regressor.predict(features_df)[0], 0, 100))
    expert_score = _expert_risk_score(features)
    blended_score = (raw_model_score * 0.45) + (expert_score * 0.55)
    risk_score = _clip(50.0 + ((blended_score - 50.0) * 1.18), 5.0, 95.0)

    model_probabilities = dict(zip(_label_encoder.classes_, _classifier.predict_proba(features_df)[0].tolist()))
    score_probabilities = _score_based_probabilities(risk_score)
    probabilities = {
        key: round((model_probabilities.get(key, 0.0) * 0.35) + (score_probabilities.get(key, 0.0) * 0.65), 3)
        for key in ["low", "medium", "high"]
    }
    prob_total = sum(probabilities.values()) or 1.0
    probabilities = {k: round(v / prob_total, 3) for k, v in probabilities.items()}
    risk_category = _score_to_category(risk_score)

    shap_vals = _explainer_reg.shap_values(features_df)[0]
    feature_descriptions = get_feature_descriptions()
    shap_explanation = []
    for i, (feat, val) in enumerate(zip(feature_names, shap_vals)):
        shap_explanation.append({
            "feature": feat,
            "description": feature_descriptions.get(feat, feat),
            "feature_value": float(features_df[feat].iloc[0]),
            "shap_value": float(val)
        })
    shap_explanation.sort(key=lambda x: abs(x['shap_value']), reverse=True)

    top_drivers = [s for s in shap_explanation if s['shap_value'] > 0][:5]
    top_reducers = [s for s in shap_explanation if s['shap_value'] < 0][:3]

    narrative_parts = [
        f"Model baseline for comparable companies: {float(_explainer_reg.expected_value):.0f}/100.",
        f"Final score calibrated using live operating signals: model {raw_model_score:.1f}, expert overlay {expert_score:.1f}, final {risk_score:.1f}."
    ]
    for d in top_drivers:
        narrative_parts.append(f"• {d['description']} contributed +{d['shap_value']:.1f} points")
    if top_reducers:
        narrative_parts.append("Positive offsetting factors:")
        for r in top_reducers:
            narrative_parts.append(f"• {r['description']} reduced risk by {abs(r['shap_value']):.1f} points")
    narrative = "\n".join(narrative_parts)

    waterfall_html = generate_shap_waterfall_html(features_df, company_name)

    recommendations = {
        'low': "Proceed with standard due diligence. No critical blockers identified.",
        'medium': "Proceed with enhanced due diligence. Address identified risk factors before closing.",
        'high': "Exercise significant caution. Deep-dive investigation required before proceeding."
    }
    summaries = {
        'low': f"LOW risk profile (score: {risk_score:.0f}/100). Relatively healthy acquisition target.",
        'medium': f"MEDIUM risk profile (score: {risk_score:.0f}/100). Several factors warrant attention.",
        'high': f"HIGH risk profile (score: {risk_score:.0f}/100). Significant concerns identified across multiple dimensions."
    }

    return {
        "company_name": company_name,
        "risk_score": round(risk_score, 1),
        "risk_category": risk_category,
        "risk_probabilities": probabilities,
        "risk_level_color": {"low": "#22C55E", "medium": "#F59E0B", "high": "#EF4444"}.get(risk_category, "#F59E0B"),
        "shap_explanation": shap_explanation,
        "waterfall_html": waterfall_html,
        "narrative": narrative,
        "executive_summary": summaries.get(risk_category, ""),
        "recommendation": recommendations.get(risk_category, ""),
        "features_used": features,
        "raw_model_score": round(raw_model_score, 1),
        "expert_overlay_score": round(expert_score, 1),
    }
