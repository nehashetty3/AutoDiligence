from backend.analytics.analytics_runner import run_full_analytics
from backend.database.schema import SessionLocal, Company, RiskAssessment
from backend.llm.report_generator import generate_fallback_report
from backend.models.risk_scoring import score_company


def refresh_risk_assessments():
    db = SessionLocal()
    try:
        latest_by_company = {}
        for ra in db.query(RiskAssessment).order_by(RiskAssessment.created_at).all():
            latest_by_company[ra.company_id] = ra

        companies = db.query(Company).order_by(Company.id).all()
        updated = 0

        for company in companies:
            latest = latest_by_company.get(company.id)
            if not latest:
                continue

            print(f"\nRefreshing risk assessment for {company.name} ({company.ticker})")
            analytics_results = run_full_analytics(company.id)
            risk_assessment = score_company(analytics_results, company.name)
            latest.risk_score = risk_assessment["risk_score"]
            latest.risk_category = risk_assessment["risk_category"]
            latest.shap_values = risk_assessment["shap_explanation"][:10]
            latest.report_text = generate_fallback_report(company.name, analytics_results, risk_assessment)
            updated += 1

        db.commit()
        print(f"\nUpdated {updated} latest risk assessments")
    finally:
        db.close()


if __name__ == "__main__":
    refresh_risk_assessments()
