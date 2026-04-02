import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')
from sqlalchemy.orm import Session
from backend.database.schema import SessionLocal, NewsArticle

_sentiment_model = None
_SENTIMENT_UNAVAILABLE = False

POSITIVE_HINTS = {
    "beats", "growth", "surge", "record", "profit", "strong", "upside", "upgrade",
    "expands", "wins", "improves", "outperform", "bullish", "rebound", "innovation"
}
NEGATIVE_HINTS = {
    "miss", "drop", "decline", "loss", "lawsuit", "probe", "risk", "cuts", "warning",
    "downgrade", "weak", "fraud", "bankruptcy", "layoffs", "fall", "slump", "crisis"
}

def get_sentiment_model():
    global _sentiment_model, _SENTIMENT_UNAVAILABLE
    if _SENTIMENT_UNAVAILABLE:
        return None
    if _sentiment_model is None:
        try:
            from transformers import pipeline
            print("[Sentiment] Loading FinBERT model...")
            _sentiment_model = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
                max_length=512,
                truncation=True
            )
            print("[Sentiment] FinBERT loaded")
        except Exception as e:
            _SENTIMENT_UNAVAILABLE = True
            print(f"[Sentiment] FinBERT unavailable, using lexical fallback: {e}")
            return None
    return _sentiment_model

def lexical_sentiment(text: str) -> dict:
    lower = text.lower()
    pos_hits = sum(1 for word in POSITIVE_HINTS if word in lower)
    neg_hits = sum(1 for word in NEGATIVE_HINTS if word in lower)
    if pos_hits == 0 and neg_hits == 0:
        return {"label": "neutral", "score": 0.5}
    total = pos_hits + neg_hits
    balance = (pos_hits - neg_hits) / total
    score = float(np.clip(0.5 + (balance * 0.25), 0.05, 0.95))
    label = "positive" if score > 0.55 else "negative" if score < 0.45 else "neutral"
    return {"label": label, "score": round(score, 3)}

def analyze_single_article(text: str) -> dict:
    if not text or len(text.strip()) < 10:
        return {"label": "neutral", "score": 0.5}
    try:
        model = get_sentiment_model()
        if model is None:
            return lexical_sentiment(text)
        result = model(text[:1000])[0]
        label = result['label'].lower()
        conf = result['score']
        if label == 'positive':
            score = 0.5 + (conf * 0.5)
        elif label == 'negative':
            score = 0.5 - (conf * 0.5)
        else:
            score = 0.5
        return {"label": label, "score": score}
    except Exception:
        return lexical_sentiment(text)

def analyze_company_sentiment(company_id: int) -> dict:
    db = SessionLocal()
    try:
        articles = db.query(NewsArticle).filter(
            NewsArticle.company_id == company_id
        ).order_by(NewsArticle.published_date).all()
        if not articles:
            return {"overall_score": 0.5, "sentiment_trend": "unknown", "overall_sentiment": "neutral",
                    "recent_score_90d": 0.5, "total_articles_analyzed": 0,
                    "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
                    "monthly_timeline": []}
        print(f"[Sentiment] Analyzing {len(articles)} articles...")
        results = []
        for i, article in enumerate(articles):
            text = f"{article.headline}. {article.full_text or ''}"
            sentiment = analyze_single_article(text)
            article.sentiment_score = sentiment["score"]
            article.sentiment_label = sentiment["label"]
            results.append({
                "date": article.published_date,
                "sentiment_score": sentiment["score"],
                "sentiment_label": sentiment["label"]
            })
            if (i + 1) % 20 == 0:
                print(f"[Sentiment] {i+1}/{len(articles)} analyzed...")
        db.commit()
        df = pd.DataFrame(results)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        overall_avg = float(df['sentiment_score'].mean())
        cutoff = df['date'].max() - timedelta(days=90)
        recent_df = df[df['date'] >= cutoff]
        recent_avg = float(recent_df['sentiment_score'].mean()) if len(recent_df) > 0 else overall_avg
        if len(df) >= 5:
            x = np.arange(len(df))
            slope = np.polyfit(x, df['sentiment_score'].values, 1)[0]
            trend = "improving" if slope > 0.0003 else "declining" if slope < -0.0003 else "stable"
        else:
            trend = "stable"
        df['month'] = df['date'].dt.to_period('M')
        monthly = df.groupby('month')['sentiment_score'].mean().reset_index()
        monthly.columns = ['month', 'avg_sentiment']
        monthly['month'] = monthly['month'].astype(str)
        dist = df['sentiment_label'].value_counts().to_dict()
        return {
            "overall_score": round(overall_avg, 3),
            "overall_sentiment": "positive" if overall_avg >= 0.65 else "negative" if overall_avg <= 0.35 else "neutral",
            "recent_score_90d": round(recent_avg, 3),
            "sentiment_trend": trend,
            "total_articles_analyzed": len(articles),
            "sentiment_distribution": {"positive": dist.get("positive", 0), "neutral": dist.get("neutral", 0), "negative": dist.get("negative", 0)},
            "monthly_timeline": monthly.to_dict('records')
        }
    finally:
        db.close()
