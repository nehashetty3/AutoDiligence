import pandas as pd
import numpy as np
from sqlalchemy import text
from backend.database.schema import SessionLocal, JobPosting, engine

def analyze_hiring_patterns(company_id: int) -> dict:
    db = SessionLocal()
    try:
        postings = db.query(JobPosting).filter(JobPosting.company_id == company_id).all()
        if not postings:
            return {"error": "No job posting data", "hiring_health_score": 50,
                    "overall_hiring_trend": "unknown", "department_trends": [], "red_flags": []}
        data = [{"department": p.department, "seniority_level": p.seniority_level,
                 "posted_date": p.posted_date, "location": p.location} for p in postings]
        df = pd.DataFrame(data)
        df['posted_date'] = pd.to_datetime(df['posted_date'])
        midpoint = df['posted_date'].min() + (df['posted_date'].max() - df['posted_date'].min()) / 2
        dept_trends = []
        for dept in df['department'].unique():
            ddf = df[df['department'] == dept]
            total = len(ddf)
            first = len(ddf[ddf['posted_date'] <= midpoint])
            second = len(ddf[ddf['posted_date'] > midpoint])
            change = ((second - first) / max(first, 1)) * 100
            trend = "accelerating" if change > 20 else "decelerating" if change < -20 else "stable"
            senior_count = len(ddf[ddf['seniority_level'].isin(['Senior', 'Director', 'VP'])])
            dept_trends.append({
                "department": dept,
                "total_postings": total,
                "velocity_change_pct": round(change, 1),
                "trend": trend,
                "senior_ratio": round(senior_count / max(total, 1), 2)
            })
        dept_trends.sort(key=lambda x: x['total_postings'], reverse=True)
        x = np.arange(len(df.groupby(df['posted_date'].dt.to_period('M')).size()))
        monthly_counts = df.groupby(df['posted_date'].dt.to_period('M')).size().values
        slope = np.polyfit(np.arange(len(monthly_counts)), monthly_counts, 1)[0] if len(monthly_counts) > 1 else 0
        overall_trend = "growing" if slope > 0.5 else "shrinking" if slope < -0.5 else "stable"
        red_flags = []
        for d in dept_trends:
            if d['velocity_change_pct'] < -40:
                red_flags.append({"type": "hiring_freeze", "department": d['department'],
                                  "description": f"{d['department']} hiring dropped {abs(d['velocity_change_pct']):.0f}%"})
            if d['department'] == 'Legal' and d['trend'] == 'accelerating':
                red_flags.append({"type": "legal_expansion", "department": "Legal",
                                  "description": "Significant increase in legal hiring"})
        score = 50
        if overall_trend == "growing": score += 20
        elif overall_trend == "shrinking": score -= 20
        score -= len([d for d in dept_trends if d['velocity_change_pct'] < -40]) * 10
        eng = next((d for d in dept_trends if d['department'] == 'Engineering'), None)
        if eng and eng['trend'] == 'accelerating': score += 10
        df['month'] = df['posted_date'].dt.to_period('M')
        monthly = df.groupby('month').size().reset_index(name='count')
        monthly['month'] = monthly['month'].astype(str)
        return {
            "total_postings_analyzed": len(df),
            "overall_hiring_trend": overall_trend,
            "hiring_health_score": max(0, min(100, score)),
            "department_trends": dept_trends,
            "monthly_hiring_volume": monthly.to_dict('records'),
            "red_flags": red_flags,
            "geographic_distribution": df['location'].value_counts().head(5).to_dict()
        }
    finally:
        db.close()
