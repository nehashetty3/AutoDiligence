from backend.database.schema import SessionLocal, Company
from backend.ingestion.sec_pipeline import get_canonical_financial_data, save_company_to_db


def refresh_all_company_financials():
    db = SessionLocal()
    try:
        companies = db.query(Company).order_by(Company.id).all()
        print(f"Refreshing financials for {len(companies)} companies")

        refreshed = 0
        skipped = 0

        for company in companies:
            company_info = {
                "name": company.name,
                "ticker": company.ticker,
                "cik": company.cik,
                "country": "US",
            }
            print(f"\n[{company.id}] {company.name} ({company.ticker})")
            financial_data = get_canonical_financial_data(company_info)
            periods = sum(len(financial_data.get(key, [])) for key in ("revenue", "net_income", "total_debt", "cash"))

            if periods == 0:
                print("  No refreshed financial data found; leaving current stored filings unchanged")
                skipped += 1
                continue

            company_id = save_company_to_db(company_info, financial_data)
            if company_id:
                refreshed += 1
            else:
                skipped += 1

        print(f"\nRefresh complete: {refreshed} refreshed, {skipped} skipped")
    finally:
        db.close()


if __name__ == "__main__":
    refresh_all_company_financials()
