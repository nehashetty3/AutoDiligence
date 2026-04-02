import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
import joblib
import os
import json
from backend.models.feature_engineering import get_feature_names

def create_training_data(n_samples: int = 800) -> pd.DataFrame:
    """
    Create diverse training data with wide variation in risk scores.
    Ensures model produces varied scores across the full 0-100 range.
    """
    np.random.seed(42)
    data = []

    # More balanced distribution with extreme cases
    for i in range(n_samples):
        risk_category = np.random.choice(
            ['low', 'medium', 'high'],
            p=[0.40, 0.35, 0.25]  # More balanced than before
        )

        if risk_category == 'low':
            row = {
                'revenue_growth': np.random.normal(0.15, 0.10),
                'profit_margin': np.random.normal(0.18, 0.07),
                'debt_to_cash': np.random.normal(1.2, 0.4),
                'cash_change': np.random.normal(0.08, 0.12),
                'financial_anomaly_count': np.random.choice([0, 1], p=[0.90, 0.10]),
                'financial_risk_encoded': 0,
                'sentiment_score': np.random.normal(0.72, 0.08),
                'recent_sentiment_score': np.random.normal(0.74, 0.08),
                'sentiment_momentum': np.random.normal(0.03, 0.04),
                'sentiment_trend_encoded': np.random.choice([0, 1], p=[0.25, 0.75]),
                'negative_article_ratio': np.random.normal(0.12, 0.07),
                'patent_velocity_encoded': np.random.choice([0, 1], p=[0.3, 0.7]),
                'patent_velocity_change_pct': np.random.normal(0.20, 0.12),
                'innovation_diversity_score': np.random.normal(0.65, 0.12),
                'total_patents_normalized': np.random.uniform(0.3, 1.0),
                'hiring_health_score': np.random.normal(0.75, 0.10),
                'hiring_red_flag_count': 0,
                'hiring_trend_encoded': np.random.choice([0, 1], p=[0.3, 0.7]),
                'executive_mention_count': np.random.randint(4, 12),
                'competitor_mention_count': np.random.randint(5, 15),
                'risk_statement_count': np.random.normal(0.20, 0.10),
                'risk_score': np.random.uniform(5, 32)
            }
        elif risk_category == 'medium':
            row = {
                'revenue_growth': np.random.normal(0.04, 0.12),
                'profit_margin': np.random.normal(0.06, 0.09),
                'debt_to_cash': np.random.normal(4.0, 1.5),
                'cash_change': np.random.normal(-0.03, 0.15),
                'financial_anomaly_count': np.random.choice([0, 1, 2], p=[0.45, 0.40, 0.15]),
                'financial_risk_encoded': np.random.choice([0, 1, 2], p=[0.15, 0.65, 0.20]),
                'sentiment_score': np.random.normal(0.50, 0.10),
                'recent_sentiment_score': np.random.normal(0.48, 0.10),
                'sentiment_momentum': np.random.normal(-0.02, 0.06),
                'sentiment_trend_encoded': np.random.choice([-1, 0, 1], p=[0.35, 0.35, 0.30]),
                'negative_article_ratio': np.random.normal(0.32, 0.12),
                'patent_velocity_encoded': np.random.choice([-1, 0, 1], p=[0.3, 0.4, 0.3]),
                'patent_velocity_change_pct': np.random.normal(0.0, 0.18),
                'innovation_diversity_score': np.random.normal(0.42, 0.15),
                'total_patents_normalized': np.random.uniform(0.1, 0.6),
                'hiring_health_score': np.random.normal(0.48, 0.15),
                'hiring_red_flag_count': np.random.choice([0, 1, 2], p=[0.55, 0.35, 0.10]),
                'hiring_trend_encoded': np.random.choice([-1, 0, 1], p=[0.25, 0.45, 0.30]),
                'executive_mention_count': np.random.randint(2, 8),
                'competitor_mention_count': np.random.randint(3, 12),
                'risk_statement_count': np.random.normal(0.52, 0.18),
                'risk_score': np.random.uniform(33, 67)
            }
        else:  # high
            row = {
                'revenue_growth': np.random.normal(-0.10, 0.18),
                'profit_margin': np.random.normal(-0.05, 0.15),
                'debt_to_cash': np.random.normal(8.5, 3.0),
                'cash_change': np.random.normal(-0.20, 0.20),
                'financial_anomaly_count': np.random.choice([1, 2, 3, 4], p=[0.25, 0.40, 0.25, 0.10]),
                'financial_risk_encoded': np.random.choice([1, 2], p=[0.15, 0.85]),
                'sentiment_score': np.random.normal(0.32, 0.10),
                'recent_sentiment_score': np.random.normal(0.28, 0.10),
                'sentiment_momentum': np.random.normal(-0.07, 0.05),
                'sentiment_trend_encoded': np.random.choice([-1, 0], p=[0.85, 0.15]),
                'negative_article_ratio': np.random.normal(0.60, 0.12),
                'patent_velocity_encoded': np.random.choice([-1, 0], p=[0.75, 0.25]),
                'patent_velocity_change_pct': np.random.normal(-0.28, 0.15),
                'innovation_diversity_score': np.random.normal(0.22, 0.12),
                'total_patents_normalized': np.random.uniform(0.0, 0.3),
                'hiring_health_score': np.random.normal(0.25, 0.12),
                'hiring_red_flag_count': np.random.choice([1, 2, 3, 4], p=[0.35, 0.40, 0.18, 0.07]),
                'hiring_trend_encoded': np.random.choice([-1, 0], p=[0.75, 0.25]),
                'executive_mention_count': np.random.randint(1, 6),
                'competitor_mention_count': np.random.randint(2, 8),
                'risk_statement_count': np.random.normal(0.80, 0.15),
                'risk_score': np.random.uniform(68, 97)
            }

        row['risk_category'] = risk_category
        data.append(row)

    df = pd.DataFrame(data)
    feature_cols = get_feature_names()
    for col in feature_cols:
        if col in df.columns:
            df[col] = df[col].clip(-10, 20)

    os.makedirs('backend/models/saved_models', exist_ok=True)
    df.to_csv('backend/models/saved_models/training_data.csv', index=False)
    print(f"Training data: {len(df)} samples | {df['risk_category'].value_counts().to_dict()}")
    print(f"Risk score range: {df['risk_score'].min():.1f} - {df['risk_score'].max():.1f} | Mean: {df['risk_score'].mean():.1f}")
    return df

def train_all_models():
    print("=" * 50)
    print("TRAINING RISK MODELS")
    print("=" * 50)
    df = create_training_data(800)
    feature_cols = get_feature_names()
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0.0
    X = df[feature_cols]
    os.makedirs('backend/models/saved_models', exist_ok=True)

    # Classifier
    le = LabelEncoder()
    le.fit(['low', 'medium', 'high'])
    y_cls = le.transform(df['risk_category'])
    X_train, X_test, y_train, y_test = train_test_split(X, y_cls, test_size=0.2, random_state=42, stratify=y_cls)
    classifier = xgb.XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.08,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=2,
        gamma=0.05, random_state=42, eval_metric='mlogloss', use_label_encoder=False
    )
    classifier.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    acc = accuracy_score(y_test, classifier.predict(X_test))
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(classifier, X, y_cls, cv=cv, scoring='accuracy')
    print(f"Classifier: {acc:.3f} accuracy | CV: {cv_scores.mean():.3f}")
    joblib.dump(classifier, 'backend/models/saved_models/risk_classifier.pkl')
    joblib.dump(le, 'backend/models/saved_models/label_encoder.pkl')

    # Regressor
    y_reg = df['risk_score']
    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X, y_reg, test_size=0.2, random_state=42)
    regressor = xgb.XGBRegressor(
        n_estimators=300, max_depth=5, learning_rate=0.08,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=2,
        gamma=0.05, random_state=42
    )
    regressor.fit(X_train_r, y_train_r, eval_set=[(X_test_r, y_test_r)], verbose=False)
    mae = mean_absolute_error(y_test_r, regressor.predict(X_test_r))
    r2 = r2_score(y_test_r, regressor.predict(X_test_r))
    print(f"Regressor: MAE={mae:.2f} | R2={r2:.3f}")
    joblib.dump(regressor, 'backend/models/saved_models/risk_regressor.pkl')

    metrics = {"classifier_accuracy": acc, "cv_accuracy": cv_scores.mean(), "regressor_mae": mae, "r2_score": r2}
    with open('backend/models/saved_models/model_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    print("All models saved")
    return metrics

if __name__ == "__main__":
    train_all_models()
