import time
from backend.ingestion.sec_pipeline import run_sec_pipeline
from backend.ingestion.news_pipeline import run_news_pipeline
from backend.ingestion.patent_pipeline import run_patent_pipeline
from backend.ingestion.hiring_pipeline import run_hiring_pipeline
from backend.ingestion.competitor_pipeline import run_competitor_identification

def run_full_ingestion(company_name: str) -> dict:
    print(f"\n{'='*50}")
    print(f"INGESTION STARTING: {company_name.upper()}")
    print(f"{'='*50}")
    results = {}

    print("\n[1/4] SEC EDGAR Pipeline...")
    sec_result = run_sec_pipeline(company_name)
    if not sec_result:
        return {"error": f"Could not find '{company_name}'. Try using the full company name or stock ticker."}

    company_id = sec_result["company_id"]
    ticker = sec_result["company_info"]["ticker"]
    results["sec"] = sec_result
    time.sleep(0.3)

    print("\n[2/4] News Pipeline...")
    news_result = run_news_pipeline(company_name, ticker, company_id)
    results["news_count"] = len(news_result) if news_result else 0
    time.sleep(0.3)

    print("\n[3/4] Patent Pipeline...")
    patent_result = run_patent_pipeline(company_name, company_id, ticker)
    results["patent_count"] = len(patent_result) if patent_result else 0
    time.sleep(0.3)

    print("\n[4/4] Hiring Pipeline...")
    hiring_result = run_hiring_pipeline(company_name, company_id)
    results["hiring_count"] = len(hiring_result) if hiring_result else 0

    competitors = run_competitor_identification(company_name, ticker)
    results["competitors"] = competitors
    results["company_id"] = company_id
    results["company_name"] = company_name
    results["ticker"] = ticker

    print(f"\n{'='*50}")
    print(f"INGESTION COMPLETE: {company_name.upper()}")
    print(f"News: {results['news_count']} | Patents: {results['patent_count']} | Jobs: {results['hiring_count']}")
    print(f"Competitors: {competitors}")
    print(f"{'='*50}\n")
    return results
