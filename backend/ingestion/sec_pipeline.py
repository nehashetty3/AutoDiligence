import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import re
from sqlalchemy.orm import Session
from backend.database.schema import SessionLocal, Company, Filing
from backend.ingestion.financials_pipeline import get_financials

HEADERS = {
    "User-Agent": "AutoDiligence autodiligence@research.com",
    "Accept-Encoding": "gzip, deflate",
}

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

_company_cache = {}
_QUERY_ALIASES = {
    "adani ports and sez": "Adani Ports and Special Economic Zone Limited",
    "adani ports & sez": "Adani Ports and Special Economic Zone Limited",
    "adani port": "Adani Ports and Special Economic Zone Limited",
    "adani ports": "Adani Ports and Special Economic Zone Limited",
}

_COMPANY_SUFFIX_PATTERN = re.compile(
    r"\b(limited|ltd|incorporated|inc|corp|corporation|company|co|plc|ag|group|holdings?)\b",
    re.IGNORECASE,
)


def _normalize_company_name(name: str) -> str:
    normalized = _COMPANY_SUFFIX_PATTERN.sub(" ", name or "")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized.lower())
    return " ".join(normalized.split())


def _company_match_score(query: str, result_name: str, result_ticker: str) -> float:
    query_clean = (query or "").strip()
    query_norm = _normalize_company_name(query_clean)
    name_norm = _normalize_company_name(result_name or "")
    ticker_upper = (result_ticker or "").upper()
    query_upper = query_clean.upper()
    score = 0.0

    if query_upper and ticker_upper == query_upper:
        score += 6.0
    elif query_upper and ticker_upper.startswith(query_upper):
        score += 4.0

    if name_norm == query_norm and query_norm:
        score += 10.0
    elif query_norm and name_norm.startswith(query_norm):
        score += 8.0
    elif query_norm and query_norm in name_norm:
        score += 4.0

    if query_norm:
        query_tokens = query_norm.split()
        name_tokens = name_norm.split()
        if any(token == query_norm for token in name_tokens):
            score += 8.0
        shared = len(set(query_tokens) & set(name_tokens))
        score += shared * 1.5

    # Penalize obvious mismatches for short uppercase ticker-style queries like BYD -> Boyd.
    if query_clean.isupper() and len(query_clean) <= 4 and query_norm and name_norm:
        if not name_norm.startswith(query_norm) and query_norm not in name_norm.split():
            score -= 3.0

    return score


def _find_existing_company(db: Session, company_info: dict):
    ticker = company_info.get("ticker")
    cik = company_info.get("cik")
    name = company_info.get("name", "")

    if ticker:
        existing = db.query(Company).filter(Company.ticker == ticker).first()
        if existing:
            return existing

    if cik:
        existing = db.query(Company).filter(Company.cik == cik).first()
        if existing:
            return existing

    normalized_name = _normalize_company_name(name)
    if not normalized_name:
        return None

    for candidate in db.query(Company).all():
        if _normalize_company_name(candidate.name) == normalized_name:
            return candidate
    return None

# ─── COMPANY SEARCH ──────────────────────────────────────────────────────────

def search_yahoo_finance(company_name: str) -> dict:
    """Search Yahoo Finance for any public company globally."""
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {"q": company_name, "quotesCount": 5, "newsCount": 0}
        response = requests.get(url, params=params, headers=YAHOO_HEADERS, timeout=10)
        data = response.json()
        quotes = [q for q in data.get("quotes", []) if q.get("quoteType") == "EQUITY"]
        if quotes:
            scored = sorted(
                quotes,
                key=lambda q: _company_match_score(
                    company_name,
                    q.get("longname") or q.get("shortname") or "",
                    q.get("symbol", ""),
                ),
                reverse=True,
            )
            best = scored[0]
            name = best.get("longname") or best.get("shortname") or company_name
            ticker = best.get("symbol", "")
            exchange = best.get("exchange", "")
            country = infer_country_from_exchange(exchange, ticker)
            print(f"[SEC] Yahoo found: {name} ({ticker}) on {exchange} [{country}]")
            return {"name": name, "ticker": ticker, "exchange": exchange,
                    "country": country, "cik": f"YAHOO_{ticker}"}
    except Exception as e:
        print(f"[SEC] Yahoo search error: {e}")
    return None

def search_sec_edgar(company_name: str) -> dict:
    """Search SEC EDGAR for US-listed companies."""
    try:
        response = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=HEADERS, timeout=10
        )
        tickers_data = response.json()
        name_lower = company_name.lower().strip()

        # Exact match
        for key, value in tickers_data.items():
            if name_lower == value['title'].lower():
                return {"cik": str(value['cik_str']).zfill(10), "name": value['title'],
                        "ticker": value['ticker'], "country": "US"}

        # Exact ticker match should beat fuzzy name matches like TCS -> BTCS
        for key, value in tickers_data.items():
            if company_name.upper().strip() == value['ticker'].upper():
                return {"cik": str(value['cik_str']).zfill(10), "name": value['title'],
                        "ticker": value['ticker'], "country": "US"}

        # Best partial match
        if len(name_lower) >= 4:
            matches = []
            for key, value in tickers_data.items():
                title_lower = value['title'].lower()
                if name_lower in title_lower:
                    score = len(name_lower) / len(title_lower)
                    if title_lower.startswith(name_lower):
                        score += 0.25
                    matches.append((score, value))
            if matches:
                matches.sort(key=lambda x: x[0], reverse=True)
                best = matches[0][1]
                return {"cik": str(best['cik_str']).zfill(10), "name": best['title'],
                        "ticker": best['ticker'], "country": "US"}
    except Exception as e:
        print(f"[SEC] EDGAR error: {e}")
    return None

def infer_country_from_exchange(exchange: str, ticker: str) -> str:
    e = (exchange or "").upper()
    t = (ticker or "").upper()
    if any(x in e for x in ['NSI', 'BSE', 'NSE', 'BO']) or t.endswith('.NS') or t.endswith('.BO'): return "IN"
    if any(x in e for x in ['LSE', 'LON']) or t.endswith('.L'): return "GB"
    if any(x in e for x in ['TYO', 'TSE']) or t.endswith('.T'): return "JP"
    if any(x in e for x in ['FRA', 'XETRA']) or t.endswith('.DE') or t.endswith('.F'): return "DE"
    if any(x in e for x in ['HKG', 'HKSE']) or t.endswith('.HK'): return "HK"
    if any(x in e for x in ['TSX', 'TOR']) or t.endswith('.TO'): return "CA"
    if any(x in e for x in ['ASX']) or t.endswith('.AX'): return "AU"
    if any(x in e for x in ['SHH', 'SHZ', 'SHA']): return "CN"
    if any(x in e for x in ['KSE', 'KOE']): return "KR"
    return "US"

def get_company_cik(company_name: str) -> dict:
    name_lower = company_name.lower().strip()
    if name_lower in _company_cache:
        return _company_cache[name_lower]

    canonical_query = _QUERY_ALIASES.get(name_lower, company_name)

    sec_result = search_sec_edgar(canonical_query)
    yahoo_result = search_yahoo_finance(canonical_query)

    if sec_result and yahoo_result:
        sec_score = _company_match_score(canonical_query, sec_result.get("name", ""), sec_result.get("ticker", ""))
        yahoo_score = _company_match_score(canonical_query, yahoo_result.get("name", ""), yahoo_result.get("ticker", ""))
        result = yahoo_result if yahoo_score > sec_score else sec_result
    else:
        result = sec_result or yahoo_result

    if result:
        _company_cache[name_lower] = result
    return result

# ─── FINANCIAL DATA ───────────────────────────────────────────────────────────

def get_yahoo_financials(ticker: str, company_name: str) -> dict:
    """
    Fetch real financial data from Yahoo Finance for any global company.
    Covers NSE, BSE, NYSE, NASDAQ, LSE, TSE and all major exchanges.
    """
    print(f"[Finance] Fetching real financials from Yahoo Finance for {ticker}...")

    financial_data = {}

    try:
        # Income statement — annual
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
        params = {"modules": "incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory"}
        response = requests.get(url, params=params, headers=YAHOO_HEADERS, timeout=15)
        data = response.json()

        result = data.get("quoteSummary", {}).get("result", [])
        if not result:
            print(f"[Finance] No Yahoo Finance data for {ticker}")
            return {}

        result = result[0]

        # Revenue
        income_stmts = result.get("incomeStatementHistory", {}).get("incomeStatementHistory", [])
        revenues, net_incomes = [], []
        for stmt in income_stmts[-4:]:
            date = stmt.get("endDate", {}).get("fmt", "")
            rev = stmt.get("totalRevenue", {}).get("raw")
            net = stmt.get("netIncome", {}).get("raw")
            if date and rev:
                revenues.append({"end": date, "val": int(rev), "form": "10-K"})
            if date and net:
                net_incomes.append({"end": date, "val": int(net), "form": "10-K"})

        # Balance sheet
        balance_sheets = result.get("balanceSheetHistory", {}).get("balanceSheetStatements", [])
        debts, cashes = [], []
        for sheet in balance_sheets[-4:]:
            date = sheet.get("endDate", {}).get("fmt", "")
            debt = sheet.get("longTermDebt", {}).get("raw") or sheet.get("shortLongTermDebt", {}).get("raw")
            cash = sheet.get("cash", {}).get("raw") or sheet.get("cashAndCashEquivalents", {}).get("raw")
            if date and debt:
                debts.append({"end": date, "val": int(debt), "form": "10-K"})
            if date and cash:
                cashes.append({"end": date, "val": int(cash), "form": "10-K"})

        if revenues:
            financial_data['revenue'] = revenues
            financial_data['net_income'] = net_incomes
            financial_data['total_debt'] = debts
            financial_data['cash'] = cashes
            print(f"[Finance] Retrieved {len(revenues)} years of real financial data for {ticker}")
            return financial_data

    except Exception as e:
        print(f"[Finance] Yahoo Finance financials error: {e}")

    return {}

def get_sec_financials_extended(cik: str) -> dict:
    """
    Get extended US financial data from SEC — 5+ years of quarterly data
    for more accurate anomaly detection.
    """
    facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    try:
        response = requests.get(facts_url, headers=HEADERS, timeout=15)
        data = response.json()
        us_gaap = data.get('facts', {}).get('us-gaap', {})
        financial_data = {}

        # Revenue — get 6 years of annual data
        for revenue_field in ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
                              'SalesRevenueNet', 'SalesRevenueGoodsNet']:
            if revenue_field in us_gaap:
                units = us_gaap[revenue_field].get('units', {}).get('USD', [])
                # Annual 10-K data
                annual = [x for x in units if x.get('form') == '10-K' and x.get('end')]
                if annual:
                    # Sort by date and get last 6 years
                    annual.sort(key=lambda x: x['end'])
                    financial_data['revenue'] = annual[-6:]
                    break

        # Net income
        if 'NetIncomeLoss' in us_gaap:
            units = us_gaap['NetIncomeLoss'].get('units', {}).get('USD', [])
            annual = [x for x in units if x.get('form') == '10-K']
            if annual:
                annual.sort(key=lambda x: x['end'])
                financial_data['net_income'] = annual[-6:]

        # Operating income for additional signal
        if 'OperatingIncomeLoss' in us_gaap:
            units = us_gaap['OperatingIncomeLoss'].get('units', {}).get('USD', [])
            annual = [x for x in units if x.get('form') == '10-K']
            if annual:
                annual.sort(key=lambda x: x['end'])
                financial_data['operating_income'] = annual[-6:]

        # Debt
        for debt_field in ['LongTermDebt', 'LongTermDebtAndCapitalLeaseObligations',
                           'LongTermDebtNoncurrent']:
            if debt_field in us_gaap:
                units = us_gaap[debt_field].get('units', {}).get('USD', [])
                annual = [x for x in units if x.get('form') == '10-K']
                if annual:
                    annual.sort(key=lambda x: x['end'])
                    financial_data['total_debt'] = annual[-6:]
                    break

        # Cash
        for cash_field in ['CashAndCashEquivalentsAtCarryingValue',
                           'CashCashEquivalentsAndShortTermInvestments']:
            if cash_field in us_gaap:
                units = us_gaap[cash_field].get('units', {}).get('USD', [])
                annual = [x for x in units if x.get('form') == '10-K']
                if annual:
                    annual.sort(key=lambda x: x['end'])
                    financial_data['cash'] = annual[-6:]
                    break

        # R&D spending — innovation signal
        if 'ResearchAndDevelopmentExpense' in us_gaap:
            units = us_gaap['ResearchAndDevelopmentExpense'].get('units', {}).get('USD', [])
            annual = [x for x in units if x.get('form') == '10-K']
            if annual:
                annual.sort(key=lambda x: x['end'])
                financial_data['rd_expense'] = annual[-6:]

        # Total assets
        if 'Assets' in us_gaap:
            units = us_gaap['Assets'].get('units', {}).get('USD', [])
            annual = [x for x in units if x.get('form') == '10-K']
            if annual:
                annual.sort(key=lambda x: x['end'])
                financial_data['total_assets'] = annual[-6:]

        print(f"[Finance] SEC data: {len(financial_data.get('revenue', []))} years retrieved")
        return financial_data

    except Exception as e:
        print(f"[Finance] SEC extended error: {e}")
        return {}

def get_financial_facts(cik: str, company_name: str = "", country: str = "US",
                        ticker: str = "") -> dict:
    """Route to correct financial data source based on company country."""
    if country == "US" and cik and cik.isdigit():
        # US company — use SEC EDGAR with extended 6-year data
        data = get_sec_financials_extended(cik)
        if data:
            return data
        # Fallback to Yahoo Finance if SEC fails
        if ticker:
            return get_yahoo_financials(ticker, company_name)
        return {}
    else:
        # Non-US company — use Yahoo Finance for real data
        if ticker and not ticker.startswith("YAHOO_"):
            return get_yahoo_financials(ticker, company_name)
        return {}


def _normalized_financials_to_storage_format(normalized: dict) -> dict:
    """Convert normalized yearly financials into the legacy storage format."""
    if not normalized or not normalized.get("years"):
        return {}

    def build_entries(years, values):
        entries = []
        for year, value in zip(years, values or []):
            if value is None:
                continue
            try:
                entries.append({
                    "end": f"{year}-12-31",
                    "val": int(float(value) * 1e9),
                    "form": "10-K",
                    "frame": f"CY{year}"
                })
            except Exception:
                continue
        return entries

    years = [str(y) for y in normalized.get("years", [])]
    return {
        "revenue": build_entries(years, normalized.get("revenue", [])),
        "net_income": build_entries(years, normalized.get("net_income", [])),
        "total_debt": build_entries(years, normalized.get("debt", [])),
        "cash": build_entries(years, normalized.get("cash", [])),
    }


def get_canonical_financial_data(company_info: dict) -> dict:
    """Use the normalized financial pipeline as the source of truth for storage."""
    ticker = company_info.get("ticker", "")
    name = company_info.get("name", "")
    normalized = get_financials(ticker, name)
    if normalized and normalized.get("years"):
        print(f"[Finance] Canonical financials from {normalized.get('source', 'normalized pipeline')}")
        return _normalized_financials_to_storage_format(normalized)

    print("[Finance] Normalized financial pipeline returned no data, falling back to legacy source")
    return get_financial_facts(
        company_info.get("cik", ""),
        name,
        company_info.get("country", "US"),
        ticker,
    )

# ─── DATABASE ─────────────────────────────────────────────────────────────────

def save_company_to_db(company_info: dict, financial_data: dict) -> int:
    from backend.database.schema import Filing
    db: Session = SessionLocal()
    try:
        existing = _find_existing_company(db, company_info)
        if existing:
            company = existing
            company.name = company_info['name']
            company.cik = company_info.get('cik')
            company.ticker = company_info['ticker']
            # Clear old filings for fresh data
            db.query(Filing).filter(Filing.company_id == company.id).delete()
        else:
            company = Company(
                name=company_info['name'],
                ticker=company_info['ticker'],
                cik=company_info.get('cik')
            )
            db.add(company)
            db.flush()

        revenues = financial_data.get('revenue', []) if financial_data else []
        net_incomes = financial_data.get('net_income', []) if financial_data else []
        debts = financial_data.get('total_debt', []) if financial_data else []
        cashes = financial_data.get('cash', []) if financial_data else []

        # Filter to annual records only — exclude quarterly entries
        # Annual entries have frame like 'CY2023' (no Q), or form == '10-K' with full-year date
        def is_annual(entry):
            frame = entry.get('frame', '')
            # frame='CY2023' is annual, 'CY2023Q3' is quarterly
            if frame and 'Q' in frame:
                return False
            # Also filter by year range 2019-2025
            date_str = entry.get('end', '')[:4]
            try:
                yr = int(date_str)
                return 2019 <= yr <= 2025
            except:
                return False

        # Deduplicate by year — keep one entry per fiscal year
        seen_years = {}
        for rev in revenues:
            if is_annual(rev):
                yr = rev.get('end', '')[:4]
                if yr not in seen_years:
                    seen_years[yr] = rev

        annual_revenues = [seen_years[y] for y in sorted(seen_years.keys())]

        # Build lookup maps for net_income, debt, cash by year
        def build_year_map(entries):
            m = {}
            for e in entries:
                if is_annual(e):
                    yr = e.get('end', '')[:4]
                    if yr not in m:
                        m[yr] = e
            return m

        ni_map   = build_year_map(net_incomes)
        debt_map = build_year_map(debts)
        cash_map = build_year_map(cashes)

        all_years = sorted(set(
            list(seen_years.keys()) +
            list(ni_map.keys()) +
            list(debt_map.keys()) +
            list(cash_map.keys())
        ))

        for yr in all_years:
            rev = seen_years.get(yr, {})
            try:
                date_str = (rev.get('end') or f"{yr}-12-31")
                if len(date_str) == 4:
                    date_str = f"{date_str}-12-31"
                filing_date = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
            except:
                filing_date = datetime.strptime(f"{yr}-12-31", '%Y-%m-%d').date()

            filing = Filing(
                company_id=company.id,
                filing_type='10-K',
                filing_date=filing_date,
                revenue=rev.get('val'),
                net_income=ni_map.get(yr, {}).get('val'),
                total_debt=debt_map.get(yr, {}).get('val'),
                cash=cash_map.get(yr, {}).get('val')
            )
            db.add(filing)

        db.commit()
        print(f"[SEC] Saved {company_info['name']} with {len(all_years)} financial periods (ID: {company.id})")
        return company.id
    except Exception as e:
        db.rollback()
        print(f"[SEC] DB error: {e}")
        return None
    finally:
        db.close()

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run_sec_pipeline(company_name: str) -> dict:
    print(f"[SEC] Universal lookup: {company_name}")
    company_info = get_company_cik(company_name)
    if not company_info:
        return None
    print(f"[SEC] Found: {company_info['name']} | {company_info['ticker']} | {company_info.get('country', 'US')}")
    time.sleep(0.1)
    country = company_info.get('country', 'US')
    ticker = company_info.get('ticker', '')
    cik = company_info.get('cik', '')
    financial_data = get_canonical_financial_data(company_info)
    company_id = save_company_to_db(company_info, financial_data)
    return {"company_info": company_info, "financial_data": financial_data, "company_id": company_id}
