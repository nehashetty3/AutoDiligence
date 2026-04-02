import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy import or_

from backend.database.schema import init_db, SessionLocal, Company, RiskAssessment, WatchlistEntry

app = FastAPI(title="AutoDiligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _normalize_company_label(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"\b(limited|ltd|incorporated|inc|corp|corporation|company|co|plc|ag|group|holdings?)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _find_competitor_company(db, comp_name: str):
    normalized_target = _normalize_company_label(comp_name)
    exact = db.query(Company).filter(
        or_(
            Company.name.ilike(comp_name),
            Company.ticker.ilike(comp_name),
        )
    ).first()
    if exact:
        return exact

    candidates = db.query(Company).all()
    for candidate in candidates:
        normalized_candidate = _normalize_company_label(candidate.name)
        if normalized_candidate == normalized_target:
            return candidate

    return None

class AnalyzeRequest(BaseModel):
    company_name: str

class WatchlistRequest(BaseModel):
    company_id: int
    user_email: str
    alert_threshold: Optional[float] = 10.0

class CompareRequest(BaseModel):
    company_names: List[str]

@app.on_event("startup")
async def startup():
    init_db()
    os.makedirs('backend/models/saved_models', exist_ok=True)
    print("AutoDiligence API started")

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/favicon.ico")
def favicon():
    return Response(content=b"", media_type="image/x-icon")

@app.post("/api/analyze")
async def analyze_company(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    company_name = request.company_name.strip()
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    try:
        from backend.ingestion.master_pipeline import run_full_ingestion
        from backend.analytics.analytics_runner import run_full_analytics
        from backend.models.risk_scoring import score_company
        from backend.llm.report_generator import generate_report

        print(f"\n[API] Analyzing: {company_name}")
        ingestion_result = run_full_ingestion(company_name)
        if not ingestion_result or "error" in ingestion_result:
            raise HTTPException(status_code=404, detail=f"Could not find '{company_name}'. Try the full company name or stock ticker (e.g. AAPL, INFY, TITAN.NS)")

        company_id = ingestion_result["company_id"]

        try:
            from backend.llm.rag_pipeline import index_company_documents
            background_tasks.add_task(index_company_documents, company_id, company_name)
        except:
            pass

        analytics_results = run_full_analytics(company_id)
        risk_assessment = score_company(analytics_results, company_name)
        report_text = generate_report(company_name, company_id, analytics_results, risk_assessment)

        db = SessionLocal()
        try:
            ra = RiskAssessment(
                company_id=company_id,
                risk_score=risk_assessment['risk_score'],
                risk_category=risk_assessment['risk_category'],
                shap_values=risk_assessment['shap_explanation'][:10],
                report_text=report_text
            )
            db.add(ra)
            db.commit()
        finally:
            db.close()

        # Competitor analysis: prefer cached peer assessments, but fall back to
        # a fresh analysis when we do not already have a usable result.
        competitors_data = []
        db = SessionLocal()
        try:
            for comp_name in ingestion_result.get("competitors", [])[:3]:
                competitor = _find_competitor_company(db, comp_name)
                latest_ra = None
                if competitor:
                    latest_ra = db.query(RiskAssessment).filter(
                        RiskAssessment.company_id == competitor.id
                    ).order_by(RiskAssessment.created_at.desc()).first()

                if competitor and latest_ra:
                    competitors_data.append({
                        "company_name": competitor.name,
                        "ticker": competitor.ticker or "",
                        "risk_score": latest_ra.risk_score,
                        "risk_category": latest_ra.risk_category,
                        "risk_level_color": {"low": "#22C55E", "medium": "#F59E0B", "high": "#EF4444"}.get(latest_ra.risk_category, "#F59E0B"),
                        "sentiment_score": 0.5,
                        "hiring_health": 50,
                        "status": "cached"
                    })
                    continue

                try:
                    comp_ingestion = run_full_ingestion(comp_name)
                    if comp_ingestion and "company_id" in comp_ingestion:
                        comp_analytics = run_full_analytics(comp_ingestion["company_id"])
                        comp_risk = score_company(comp_analytics, comp_name)
                        competitors_data.append({
                            "company_name": comp_name,
                            "ticker": comp_ingestion.get("ticker", ""),
                            "risk_score": comp_risk["risk_score"],
                            "risk_category": comp_risk["risk_category"],
                            "risk_level_color": comp_risk["risk_level_color"],
                            "sentiment_score": comp_analytics.get('summary', {}).get('sentiment_score', 0.5),
                            "hiring_health": comp_analytics.get('summary', {}).get('hiring_health_score', 50),
                            "status": "fresh"
                        })
                        continue
                except Exception as e:
                    print(f"[API] Competitor {comp_name} error: {e}")

                competitors_data.append({
                    "company_name": comp_name,
                    "ticker": competitor.ticker if competitor else "",
                    "risk_score": latest_ra.risk_score if latest_ra else None,
                    "risk_category": latest_ra.risk_category if latest_ra else "pending",
                    "risk_level_color": {"low": "#22C55E", "medium": "#F59E0B", "high": "#EF4444"}.get(latest_ra.risk_category, "#94A3B8") if latest_ra else "#94A3B8",
                    "sentiment_score": None,
                    "hiring_health": None,
                    "status": "partial"
                })
        finally:
            db.close()

        return {
            "success": True,
            "company_name": company_name,
            "company_id": company_id,
            "ticker": ingestion_result.get("ticker", ""),
            "risk_assessment": risk_assessment,
            "analytics_summary": analytics_results.get('summary', {}),
            "analytics_details": {
                "anomalies": analytics_results.get('anomalies', {}),
                "sentiment": analytics_results.get('sentiment', {}),
                "patents": analytics_results.get('patents', {}),
                "hiring": analytics_results.get('hiring', {})
            },
            "report": report_text,
            "competitors": competitors_data,
            "ingestion_stats": {
                "news_articles": ingestion_result.get("news_count", 0),
                "patents": ingestion_result.get("patent_count", 0),
                "job_postings": ingestion_result.get("hiring_count", 0)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/report/{company_id}/pdf")
def export_pdf(company_id: int):
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        ra = db.query(RiskAssessment).filter(
            RiskAssessment.company_id == company_id
        ).order_by(RiskAssessment.created_at.desc()).first()

        if not ra:
            raise HTTPException(status_code=404, detail="Report not found. Please run analysis first.")

        from backend.llm.report_generator import export_report_pdf
        company_name = company.name if company else "Company"
        report_text = ra.report_text or "No report available."
        
        try:
            pdf_bytes = export_report_pdf(report_text, company_name)
            if isinstance(pdf_bytes, str):
                pdf_bytes = pdf_bytes.encode("utf-8")
        except Exception as pdf_error:
            print(f"[PDF] Generation error: {pdf_error}")
            pdf_bytes = report_text.encode("utf-8")

        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in company_name)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="due_diligence_{safe_name}.pdf"',
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Cache-Control": "no-cache"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[PDF] Endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/company/{company_id}")
def get_company(company_id: int):
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        assessments = db.query(RiskAssessment).filter(
            RiskAssessment.company_id == company_id
        ).order_by(RiskAssessment.created_at.desc()).limit(5).all()
        return {
            "company": {"id": company.id, "name": company.name, "ticker": company.ticker},
            "assessments": [{"id": a.id, "risk_score": a.risk_score,
                             "risk_category": a.risk_category, "created_at": str(a.created_at)} for a in assessments]
        }
    finally:
        db.close()

@app.get("/api/companies")
def get_all_companies():
    db = SessionLocal()
    try:
        companies = db.query(Company).all()
        result = []
        for c in companies:
            latest = db.query(RiskAssessment).filter(
                RiskAssessment.company_id == c.id
            ).order_by(RiskAssessment.created_at.desc()).first()
            result.append({
                "id": c.id, "name": c.name, "ticker": c.ticker,
                "latest_risk_score": latest.risk_score if latest else None,
                "latest_risk_category": latest.risk_category if latest else None,
                "last_analyzed": str(latest.created_at) if latest else None
            })
        return result
    finally:
        db.close()

@app.post("/api/watchlist/add")
def add_watchlist(request: WatchlistRequest):
    db = SessionLocal()
    try:
        # Check company exists
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Check if already exists
        existing = db.query(WatchlistEntry).filter(
            WatchlistEntry.company_id == request.company_id,
            WatchlistEntry.user_email == request.user_email
        ).first()
        if existing:
            return {"status": "already_exists", "message": f"{company.name} is already on your watchlist"}

        # Get latest risk score
        ra = db.query(RiskAssessment).filter(
            RiskAssessment.company_id == request.company_id
        ).order_by(RiskAssessment.created_at.desc()).first()

        entry = WatchlistEntry(
            company_id=request.company_id,
            user_email=request.user_email,
            alert_threshold=request.alert_threshold,
            last_risk_score=ra.risk_score if ra else None,
            last_sentiment_score=None
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return {"status": "added", "id": entry.id, "message": f"{company.name} added to watchlist"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/watchlist/remove")
def remove_watchlist(company_id: int = Query(...), user_email: str = Query(...)):
    db = SessionLocal()
    try:
        entry = db.query(WatchlistEntry).filter(
            WatchlistEntry.company_id == company_id,
            WatchlistEntry.user_email == user_email
        ).first()
        if entry:
            db.delete(entry)
            db.commit()
            return {"status": "removed"}
        return {"status": "not_found"}
    finally:
        db.close()

@app.get("/api/watchlist/{user_email}")
def get_watchlist(user_email: str):
    db = SessionLocal()
    try:
        entries = db.query(WatchlistEntry).filter(
            WatchlistEntry.user_email == user_email
        ).all()
        result = []
        for e in entries:
            company = db.query(Company).filter(Company.id == e.company_id).first()
            result.append({
                "watchlist_id": e.id,
                "company_id": e.company_id,
                "company_name": company.name if company else "Unknown",
                "ticker": company.ticker if company else "",
                "user_email": e.user_email,
                "alert_threshold": e.alert_threshold,
                "last_risk_score": e.last_risk_score,
                "last_sentiment_score": e.last_sentiment_score,
                "created_at": str(e.created_at)
            })
        return result
    finally:
        db.close()

@app.post("/api/compare")
async def compare_companies(request: CompareRequest):
    results = []
    for company_name in request.company_names[:5]:
        try:
            from backend.ingestion.master_pipeline import run_full_ingestion
            from backend.analytics.analytics_runner import run_full_analytics
            from backend.models.risk_scoring import score_company
            ingestion = run_full_ingestion(company_name)
            if ingestion and "company_id" in ingestion:
                analytics = run_full_analytics(ingestion["company_id"])
                risk = score_company(analytics, company_name)
                results.append({
                    "company_name": company_name,
                    "ticker": ingestion.get("ticker", ""),
                    "risk_score": risk["risk_score"],
                    "risk_category": risk["risk_category"],
                    "risk_level_color": risk["risk_level_color"],
                    "sentiment_score": analytics.get('summary', {}).get('sentiment_score', 0.5),
                    "hiring_health": analytics.get('summary', {}).get('hiring_health_score', 50),
                    "patent_velocity": analytics.get('summary', {}).get('patent_velocity', 'unknown')
                })
        except Exception as e:
            print(f"[Compare] Error for {company_name}: {e}")
    return {"companies": results}


# ---- Historical Risk Tracking ----
@app.get("/api/company/{company_id}/history")
def get_risk_history(company_id: int):
    db = SessionLocal()
    try:
        assessments = db.query(RiskAssessment).filter(
            RiskAssessment.company_id == company_id
        ).order_by(RiskAssessment.created_at).all()
        return [{
            "date": a.created_at.strftime("%Y-%m-%d"),
            "timestamp": a.created_at.isoformat(),
            "label": a.created_at.strftime("%d %b %H:%M"),
            "risk_score": a.risk_score,
            "risk_category": a.risk_category
        } for a in assessments]
    finally:
        db.close()

# ---- Industry Benchmark ----
@app.get("/api/company/{company_id}/benchmark")
def get_industry_benchmark(company_id: int):
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        ra = db.query(RiskAssessment).filter(
            RiskAssessment.company_id == company_id
        ).order_by(RiskAssessment.created_at.desc()).first()
        if not company or not ra:
            raise HTTPException(status_code=404, detail="Company not found")
        from backend.analytics.industry_benchmark import get_industry_benchmark
        return get_industry_benchmark(company.name, company.ticker, ra.risk_score)
    finally:
        db.close()

# ---- Acquisition Premium ----
@app.get("/api/company/{company_id}/premium")
def get_acquisition_premium(company_id: int):
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        ra = db.query(RiskAssessment).filter(
            RiskAssessment.company_id == company_id
        ).order_by(RiskAssessment.created_at.desc()).first()
        if not company or not ra:
            raise HTTPException(status_code=404, detail="Company not found")
        from backend.analytics.analytics_runner import run_full_analytics
        from backend.models.acquisition_premium import predict_acquisition_premium
        analytics = run_full_analytics(company_id)
        summary = analytics.get("summary", {})
        return predict_acquisition_premium(
            ra.risk_score,
            summary,
            company_name=company.name,
            ticker=company.ticker,
        )
    finally:
        db.close()

# ---- Top News Articles ----
@app.get("/api/company/{company_id}/news")
def get_company_news(company_id: int):
    from backend.database.schema import NewsArticle
    db = SessionLocal()
    try:
        articles = db.query(NewsArticle).filter(
            NewsArticle.company_id == company_id,
            NewsArticle.sentiment_score.isnot(None)
        ).order_by(NewsArticle.published_date.desc()).all()
        if not articles:
            return {"positive": [], "negative": [], "recent": []}
        sorted_pos = sorted([a for a in articles if a.sentiment_score and a.sentiment_score > 0.6],
                           key=lambda x: x.sentiment_score, reverse=True)[:5]
        sorted_neg = sorted([a for a in articles if a.sentiment_score and a.sentiment_score < 0.4],
                           key=lambda x: x.sentiment_score)[:5]
        recent = sorted(articles, key=lambda x: x.published_date, reverse=True)[:10]
        def fmt(a):
            return {"headline": a.headline, "source": a.source,
                    "date": str(a.published_date), "sentiment_score": round(a.sentiment_score, 3)}
        return {
            "positive": [fmt(a) for a in sorted_pos],
            "negative": [fmt(a) for a in sorted_neg],
            "recent": [fmt(a) for a in recent]
        }
    finally:
        db.close()

# ---- Financial Trend Data ----
@app.get("/api/company/{company_id}/financials")
def get_financial_trends(company_id: int):
    from backend.database.schema import Company, Filing
    from backend.ingestion.financials_pipeline import get_financials
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return {"years": [], "revenue": [], "net_income": [], "debt": [], "cash": [],
                    "currency": "USD Billions", "error": "Company not found"}

        # Try multi-source pipeline first
        result = get_financials(company.ticker, company.name)
        if result and result.get("years"):
            return result

        # Final fallback: DB data deduplicated by year
        filings = db.query(Filing).filter(
            Filing.company_id == company_id,
            or_(
                Filing.revenue.isnot(None),
                Filing.net_income.isnot(None),
                Filing.total_debt.isnot(None),
                Filing.cash.isnot(None),
            )
        ).order_by(Filing.filing_date).all()

        if not filings:
            return {"years": [], "revenue": [], "net_income": [], "debt": [], "cash": [],
                    "currency": "USD Billions",
                    "error": "Financial data unavailable for this company"}

        seen = {}
        for f in filings:
            yr = str(f.filing_date)[:4]
            if int(yr) >= 2019:
                seen[yr] = f
        years = sorted(seen.keys())
        return {
            "years": years,
            "revenue":    [round(float(seen[y].revenue)/1e9, 2)    if seen[y].revenue    else None for y in years],
            "net_income": [round(float(seen[y].net_income)/1e9, 2) if seen[y].net_income else None for y in years],
            "debt":       [round(float(seen[y].total_debt)/1e9, 2) if seen[y].total_debt else None for y in years],
            "cash":       [round(float(seen[y].cash)/1e9, 2)       if seen[y].cash       else None for y in years],
            "currency": "USD Billions", "source": "Database"
        }
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
