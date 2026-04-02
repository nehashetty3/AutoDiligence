import re

from backend.database.schema import (
    SessionLocal,
    Company,
    Filing,
    NewsArticle,
    Patent,
    JobPosting,
    RiskAssessment,
    WatchlistEntry,
    Alert,
)


SUFFIX_PATTERN = re.compile(
    r"\b(limited|ltd|incorporated|inc|corp|corporation|company|co|plc|ag|group|holdings?)\b",
    re.IGNORECASE,
)


def normalize_name(name: str) -> str:
    cleaned = SUFFIX_PATTERN.sub(" ", name or "")
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned.lower())
    return " ".join(cleaned.split())


def merge_company_group(session, companies):
    canonical = min(companies, key=lambda c: c.id)
    preferred = max(companies, key=lambda c: (c.ticker.endswith((".NS", ".BO")), len(c.ticker or ""), -c.id))

    canonical.name = preferred.name
    canonical.ticker = preferred.ticker
    canonical.cik = preferred.cik

    for duplicate in companies:
        if duplicate.id == canonical.id:
            continue

        for model in (Filing, NewsArticle, Patent, JobPosting, RiskAssessment, WatchlistEntry, Alert):
            rows = session.query(model).filter(model.company_id == duplicate.id).all()
            for row in rows:
                row.company_id = canonical.id

        session.delete(duplicate)

    return canonical


def reconcile_duplicates():
    session = SessionLocal()
    try:
        groups = {}
        for company in session.query(Company).order_by(Company.id).all():
            key = normalize_name(company.name)
            groups.setdefault(key, []).append(company)

        merged = 0
        for key, companies in groups.items():
            if not key or len(companies) < 2:
                continue

            print(f"\nMerging duplicate group: {key}")
            for company in companies:
                print(f"  {company.id}: {company.name} ({company.ticker})")
            canonical = merge_company_group(session, companies)
            print(f"  -> kept {canonical.id}: {canonical.name} ({canonical.ticker})")
            merged += len(companies) - 1

        session.commit()
        print(f"\nCompany reconciliation complete: merged {merged} duplicate records")
    finally:
        session.close()


if __name__ == "__main__":
    reconcile_duplicates()
