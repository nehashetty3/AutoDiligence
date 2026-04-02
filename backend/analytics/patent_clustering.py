import pandas as pd
import numpy as np
import re
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from sqlalchemy.orm import Session
from backend.database.schema import SessionLocal, Patent
from datetime import datetime

DOMAIN_MAP = {
    "Artificial Intelligence & ML": ["neural", "learning", "model", "training", "algorithm", "prediction", "data"],
    "Mobile & Devices": ["mobile", "device", "display", "touch", "screen", "interface", "sensor"],
    "Cloud & Infrastructure": ["cloud", "server", "network", "distributed", "computing", "storage"],
    "Security & Privacy": ["security", "encryption", "authentication", "privacy", "access", "protection"],
    "Healthcare": ["medical", "health", "treatment", "patient", "biological", "therapeutic"],
    "Energy": ["energy", "power", "battery", "solar", "electric", "emission"],
    "Communication": ["wireless", "signal", "communication", "frequency", "antenna", "protocol"]
}

def preprocess(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'[^a-zA-Z\s]', ' ', text).lower()
    return ' '.join(w for w in text.split() if len(w) > 3)

def get_domain_label(keywords: list) -> str:
    kw_str = ' '.join(keywords).lower()
    for domain, domain_kws in DOMAIN_MAP.items():
        if any(k in kw_str for k in domain_kws):
            return domain
    return f"Technology: {keywords[0].title()}"

def analyze_patent_clusters(company_id: int) -> dict:
    db = SessionLocal()
    try:
        patents = db.query(Patent).filter(Patent.company_id == company_id).all()
        if not patents or len(patents) < 5:
            return {"clusters": [], "velocity": {"trend": "insufficient_data"},
                    "total_patents_analyzed": len(patents) if patents else 0,
                    "dominant_innovation_area": "Unknown", "innovation_diversity_score": 0}
        data = [{"title": p.patent_title or "", "abstract": p.abstract or "", "filing_date": p.filing_date}
                for p in patents]
        df = pd.DataFrame(data)
        df['text'] = (df['title'] + " " + df['abstract']).apply(preprocess)
        df = df[df['text'].str.len() > 20]
        n_topics = min(5, len(df) // 2)
        vectorizer = CountVectorizer(max_features=200, stop_words='english', min_df=2)
        dtm = vectorizer.fit_transform(df['text'])
        lda = LatentDirichletAllocation(n_components=n_topics, random_state=42, max_iter=20)
        doc_topics = lda.fit_transform(dtm)
        feature_names = vectorizer.get_feature_names_out()
        df['dominant_topic'] = doc_topics.argmax(axis=1)
        topic_counts = df['dominant_topic'].value_counts().to_dict()
        clusters = []
        for i, topic in enumerate(lda.components_):
            top_words = [feature_names[j] for j in topic.argsort()[:-9:-1]]
            clusters.append({
                "cluster_id": i,
                "label": get_domain_label(top_words),
                "keywords": top_words,
                "patent_count": topic_counts.get(i, 0),
                "percentage": round(topic_counts.get(i, 0) / len(df) * 100, 1)
            })
        clusters.sort(key=lambda x: x['patent_count'], reverse=True)
        df['filing_date'] = pd.to_datetime(df['filing_date'], errors='coerce')
        df_valid = df.dropna(subset=['filing_date'])
        velocity = {"trend": "stable", "velocity_change_pct": 0}
        if len(df_valid) >= 6:
            midpoint = df_valid['filing_date'].median()
            first_half = len(df_valid[df_valid['filing_date'] <= midpoint])
            second_half = len(df_valid[df_valid['filing_date'] > midpoint])
            if first_half > 0:
                change = ((second_half - first_half) / first_half) * 100
                velocity = {
                    "trend": "accelerating" if change > 20 else "decelerating" if change < -20 else "stable",
                    "velocity_change_pct": round(change, 1)
                }
        diversity = round(1 - max(c['percentage'] for c in clusters) / 100, 2) if clusters else 0
        return {
            "total_patents_analyzed": len(patents),
            "clusters": clusters,
            "dominant_innovation_area": clusters[0]['label'] if clusters else "Unknown",
            "velocity": velocity,
            "innovation_diversity_score": diversity
        }
    finally:
        db.close()
