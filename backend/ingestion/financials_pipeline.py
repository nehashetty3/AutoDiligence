import yfinance as yf
import pandas as pd
import re

def _is_indian_ticker(ticker, company_name=""):
    indian_keywords = ['india', 'indian', 'tata', 'reliance', 'infosys', 'wipro', 'hdfc',
                       'adani', 'bajaj', 'mahindra', 'hindustan', 'bharti', 'airtel', 'consultancy']
    if ticker.endswith('.NS') or ticker.endswith('.BO'):
        return True
    if any(k in company_name.lower() for k in indian_keywords):
        return True
    return False

def _is_chinese_ticker(ticker):
    return bool(re.match(r'^\d{6}$', ticker)) or ticker.endswith('.SH') or ticker.endswith('.SZ')

def _to_billions(val):
    try:
        v = float(val)
        return None if pd.isna(v) else round(v / 1e9, 2)
    except:
        return None

def get_financials_edgar(ticker):
    try:
        import requests
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": "AutoDiligence research@autodiligence.com"},
            timeout=15
        )
        if r.status_code != 200:
            return None
        cik = None
        for entry in r.json().values():
            if entry.get('ticker', '').upper() == ticker.upper():
                cik = str(entry['cik_str']).zfill(10)
                break
        if not cik:
            return None

        facts_r = requests.get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
            headers={"User-Agent": "AutoDiligence research@autodiligence.com"},
            timeout=20
        )
        if facts_r.status_code != 200:
            return None

        us_gaap = facts_r.json().get('facts', {}).get('us-gaap', {})

        def extract_annual(concept):
            data = us_gaap.get(concept, {}).get('units', {}).get('USD', [])
            yearly = {}
            for d in data:
                if d.get('form') == '10-K' and d.get('fp') == 'FY':
                    yr = str(d['end'])[:4]
                    if 2019 <= int(yr) <= 2025:
                        yearly[yr] = d['val']
            return yearly

        revenue_map   = (
            extract_annual('Revenues')
            or extract_annual('RevenueFromContractWithCustomerExcludingAssessedTax')
            or extract_annual('SalesRevenueNet')
            or extract_annual('RevenuesNetOfInterestExpense')
        )
        netincome_map = extract_annual('NetIncomeLoss')
        debt_map      = extract_annual('LongTermDebt')
        cash_map      = extract_annual('CashAndCashEquivalentsAtCarryingValue')

        years = sorted(set(
            list(revenue_map.keys()) +
            list(netincome_map.keys()) +
            list(debt_map.keys()) +
            list(cash_map.keys())
        ))
        if not years:
            return None

        return {
            "years":      years,
            "revenue":    [_to_billions(revenue_map.get(y))   for y in years],
            "net_income": [_to_billions(netincome_map.get(y)) for y in years],
            "debt":       [_to_billions(debt_map.get(y))      for y in years],
            "cash":       [_to_billions(cash_map.get(y))      for y in years],
            "currency":   "USD Billions",
            "source":     "SEC EDGAR"
        }
    except Exception as e:
        print(f"EDGAR error for {ticker}: {e}")
        return None

def get_financials_india(ticker):
    try:
        base = ticker.replace('.NS','').replace('.BO','').upper()
        for suffix in ['.NS', '.BO']:
            try:
                tk = yf.Ticker(base + suffix)
                fin = tk.financials
                bs  = tk.balance_sheet
                if fin is None or fin.empty or len(fin.columns) < 2:
                    continue
                years, revenue, net_income, debt, cash = [], [], [], [], []
                for col in sorted(fin.columns, key=lambda c: c.year):
                    yr = str(col.year)
                    if int(yr) < 2019:
                        continue
                    years.append(yr)
                    rev = fin.loc['Total Revenue', col] if 'Total Revenue' in fin.index else None
                    ni  = fin.loc['Net Income', col]    if 'Net Income'    in fin.index else None
                    revenue.append(_to_billions(rev))
                    net_income.append(_to_billions(ni))
                    d, c = None, None
                    if bs is not None and not bs.empty and col in bs.columns:
                        d = _to_billions(bs.loc['Total Debt', col]                if 'Total Debt'                in bs.index else None)
                        c = _to_billions(bs.loc['Cash And Cash Equivalents', col] if 'Cash And Cash Equivalents' in bs.index else None)
                    debt.append(d)
                    cash.append(c)
                clean = [(y,r,n,d,c) for y,r,n,d,c in zip(years,revenue,net_income,debt,cash) if any(v is not None for v in (r,n,d,c))]
                if clean:
                    ys,rs,ns,ds,cs = zip(*clean)
                    return {"years": list(ys), "revenue": list(rs), "net_income": list(ns), "debt": list(ds), "cash": list(cs), "currency": "INR Billions", "source": f"NSE/BSE India ({base+suffix})"}
            except:
                continue
        return None
    except Exception as e:
        print(f"India financials error for {ticker}: {e}")
        return None

def get_financials_china(ticker):
    try:
        import akshare as ak
        symbol = ticker.replace('.SH','').replace('.SZ','').replace('.HK','').zfill(6)
        df = ak.stock_financial_abstract(symbol=symbol)
        if df is None or df.empty:
            return None

        annual_cols = sorted([c for c in df.columns if str(c).endswith('1231') and 2019 <= int(str(c)[:4]) <= 2025])
        if not annual_cols:
            return None

        years, revenue, net_income = [], [], []
        for col in annual_cols:
            years.append(str(col)[:4])
            rev_row = df[df['指标'] == '营业总收入']
            ni_row  = df[df['指标'] == '归母净利润']
            revenue.append(_to_billions(rev_row[col].values[0]) if not rev_row.empty else None)
            net_income.append(_to_billions(ni_row[col].values[0]) if not ni_row.empty else None)

        return {"years": years, "revenue": revenue, "net_income": net_income,
                "debt": [None]*len(years), "cash": [None]*len(years),
                "currency": "CNY Billions", "source": "AKShare China"}
    except Exception as e:
        print(f"AKShare error for {ticker}: {e}")
        return None

def get_financials_yfinance(ticker):
    try:
        tk = yf.Ticker(ticker)
        fin = tk.financials
        bs  = tk.balance_sheet
        if fin is None or fin.empty:
            return None
        years, revenue, net_income, debt, cash = [], [], [], [], []
        for col in sorted(fin.columns, key=lambda c: c.year):
            yr = str(col.year)
            if int(yr) < 2019:
                continue
            years.append(yr)
            rev = fin.loc['Total Revenue', col] if 'Total Revenue' in fin.index else None
            ni  = fin.loc['Net Income', col]    if 'Net Income'    in fin.index else None
            revenue.append(_to_billions(rev))
            net_income.append(_to_billions(ni))
            d, c = None, None
            if bs is not None and not bs.empty and col in bs.columns:
                d = _to_billions(bs.loc['Total Debt', col]                if 'Total Debt'                in bs.index else None)
                c = _to_billions(bs.loc['Cash And Cash Equivalents', col] if 'Cash And Cash Equivalents' in bs.index else None)
            debt.append(d)
            cash.append(c)
        if not years:
            return None
        clean = [(y,r,n,d,c) for y,r,n,d,c in zip(years,revenue,net_income,debt,cash) if any(v is not None for v in (r,n,d,c))]
        if not clean:
            return None
        years,revenue,net_income,debt,cash = zip(*clean)
        # Detect currency from ticker suffix
        currency = "INR Billions" if ticker.endswith(('.NS','.BO')) else "USD Billions"
        return {"years": list(years), "revenue": list(revenue), "net_income": list(net_income),
                "debt": list(debt), "cash": list(cash), "currency": currency, "source": "Yahoo Finance"}
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        return None

INDIAN_ADR_MAP = {
    'HDB': 'HDFCBANK', 'IBN': 'ICICIBANK', 'WIT': 'WIPRO',
    'INFY': 'INFY', 'TTM': 'TATAMOTORS', 'RDY': 'DRREDDY',
}
def get_financials(ticker, company_name=""):
    if not ticker:
        return None
    ticker = ticker.strip().upper()

    nse_ticker = INDIAN_ADR_MAP.get(ticker)
    if nse_ticker:
        print(f"  Remapping Indian ADR {ticker} -> {nse_ticker}.NS")
        result = get_financials_india(nse_ticker)
        if result and result.get('years'):
            print(f"  SUCCESS: NSE/BSE via ADR remap")
            return result

    is_indian  = _is_indian_ticker(ticker, company_name)
    is_chinese = _is_chinese_ticker(ticker)

    print(f"Fetching financials: {ticker} | Indian:{is_indian} | Chinese:{is_chinese}")

    if not is_indian and not is_chinese:
        result = get_financials_edgar(ticker)
        if result and result.get('years'):
            print(f"  SUCCESS: EDGAR for {ticker}")
            return result

    if is_indian:
        result = get_financials_india(ticker)
        if result and result.get('years'):
            print(f"  SUCCESS: NSE/BSE for {ticker}")
            return result

    if is_chinese:
        result = get_financials_china(ticker)
        if result and result.get('years'):
            print(f"  SUCCESS: AKShare for {ticker}")
            return result

    result = get_financials_yfinance(ticker)
    if result and result.get('years'):
        print(f"  SUCCESS: yfinance fallback for {ticker}")
        return result

    print(f"  FAILED: all sources exhausted for {ticker}")
    return None
