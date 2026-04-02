import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session
from backend.database.schema import SessionLocal, Filing, Company

def _financials_payload_to_df(payload: dict) -> pd.DataFrame:
    years = payload.get("years") or []
    revenue = payload.get("revenue") or []
    net_income = payload.get("net_income") or []
    debt = payload.get("debt") or []
    cash = payload.get("cash") or []

    if not years:
        return pd.DataFrame()

    rows = []
    for i, year in enumerate(years):
        rows.append({
            "filing_date": pd.to_datetime(f"{year}-12-31"),
            "revenue": float(revenue[i]) * 1e9 if i < len(revenue) and revenue[i] is not None else None,
            "net_income": float(net_income[i]) * 1e9 if i < len(net_income) and net_income[i] is not None else None,
            "total_debt": float(debt[i]) * 1e9 if i < len(debt) and debt[i] is not None else None,
            "cash": float(cash[i]) * 1e9 if i < len(cash) and cash[i] is not None else None,
        })

    df = pd.DataFrame(rows)
    df['filing_date'] = pd.to_datetime(df['filing_date'])
    return df.sort_values('filing_date').reset_index(drop=True)

def get_financial_data(company_id: int) -> pd.DataFrame:
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        filings = db.query(Filing).filter(
            Filing.company_id == company_id
        ).order_by(Filing.filing_date).all()
        
        if not filings:
            print(f"[Anomaly] No filings found for company {company_id}")
            if company and company.ticker:
                try:
                    from backend.ingestion.financials_pipeline import get_financials
                    pipeline_data = get_financials(company.ticker, company.name or "")
                    if pipeline_data and pipeline_data.get("years"):
                        print(f"[Anomaly] Using financials pipeline fallback for company {company_id}")
                        return _financials_payload_to_df(pipeline_data)
                except Exception as e:
                    print(f"[Anomaly] Financials pipeline fallback error for company {company_id}: {e}")
            return pd.DataFrame()
        
        data = []
        for f in filings:
            row = {
                "filing_date": f.filing_date,
                "revenue": float(f.revenue) if f.revenue else None,
                "net_income": float(f.net_income) if f.net_income else None,
                "total_debt": float(f.total_debt) if f.total_debt else None,
                "cash": float(f.cash) if f.cash else None
            }
            # Only include rows with at least revenue data
            if row["revenue"] is not None:
                data.append(row)
        
        if not data:
            print(f"[Anomaly] No revenue data found for company {company_id}")
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        df['filing_date'] = pd.to_datetime(df['filing_date'])
        df = df.sort_values('filing_date').reset_index(drop=True)
        print(f"[Anomaly] Loaded {len(df)} financial periods for company {company_id}")

        if (len(df) < 4 or df['revenue'].notna().sum() < 4) and company and company.ticker:
            try:
                from backend.ingestion.financials_pipeline import get_financials
                pipeline_data = get_financials(company.ticker, company.name or "")
                pipeline_df = _financials_payload_to_df(pipeline_data) if pipeline_data and pipeline_data.get("years") else pd.DataFrame()
                if len(pipeline_df) > len(df):
                    print(f"[Anomaly] Replacing sparse filing data with financials pipeline fallback for company {company_id}")
                    return pipeline_df
            except Exception as e:
                print(f"[Anomaly] Sparse-data fallback error for company {company_id}: {e}")

        return df
    finally:
        db.close()

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 2:
        return df

    df = df.copy()
    numeric_cols = ['revenue', 'net_income', 'total_debt', 'cash']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Core growth metrics
    df['revenue_growth'] = df['revenue'].pct_change(fill_method=None)
    df['net_income_growth'] = df['net_income'].pct_change(fill_method=None)
    df['profit_margin'] = df['net_income'] / (df['revenue'].abs() + 1)
    df['profit_margin_change'] = df['profit_margin'].diff()
    
    # Leverage metrics
    df['debt_to_cash'] = df['total_debt'] / (df['cash'].abs() + 1)
    df['debt_growth'] = df['total_debt'].pct_change(fill_method=None)
    df['cash_change'] = df['cash'].pct_change(fill_method=None)
    df['cash_to_revenue'] = df['cash'] / (df['revenue'].abs() + 1)
    df['debt_to_revenue'] = df['total_debt'] / (df['revenue'].abs() + 1)
    
    # Replace infinities
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    return df

def generate_explanation(row) -> str:
    parts = []
    if pd.notna(row.get('revenue_growth')):
        if row['revenue_growth'] < -0.15:
            parts.append(f"Revenue declined {abs(row['revenue_growth']*100):.1f}% year-over-year")
        elif row['revenue_growth'] > 0.6:
            parts.append(f"Revenue surged unusually {row['revenue_growth']*100:.1f}%")
    if pd.notna(row.get('net_income_growth')):
        if row['net_income_growth'] < -0.25:
            parts.append(f"Net income fell sharply {abs(row['net_income_growth']*100):.1f}% year-over-year")
        elif row['net_income_growth'] > 0.6:
            parts.append(f"Net income increased unusually {row['net_income_growth']*100:.1f}%")
    if pd.notna(row.get('profit_margin')):
        if row['profit_margin'] < -0.05:
            parts.append(f"Operating at a loss — margin {row['profit_margin']*100:.1f}%")
        elif row['profit_margin'] < 0.02:
            parts.append(f"Critically thin profit margin {row['profit_margin']*100:.1f}%")
    if pd.notna(row.get('debt_to_cash')):
        if row['debt_to_cash'] > 10:
            parts.append(f"Debt is {row['debt_to_cash']:.1f}x cash reserves")
    if pd.notna(row.get('cash_change')):
        if row['cash_change'] < -0.30:
            parts.append(f"Cash reserves dropped {abs(row['cash_change']*100):.1f}%")
    if pd.notna(row.get('debt_growth')):
        if row['debt_growth'] > 0.40:
            parts.append(f"Debt increased {row['debt_growth']*100:.1f}%")
    return ". ".join(parts) if parts else "Statistical outlier detected in financial pattern"

def detect_anomalies(company_id: int) -> dict:
    default = {
        "anomalies": [], "risk_level": "unknown", "anomaly_count": 0,
        "total_periods_analyzed": 0,
        "financial_summary": {
            "avg_revenue_growth": 0.05, "latest_profit_margin": 0.08,
            "latest_debt_to_cash": 2.0, "revenue_trend": "stable", "data_years": 0
        }
    }

    df = get_financial_data(company_id)
    if df.empty:
        return default

    df = engineer_features(df)

    feature_cols = ['revenue_growth', 'net_income_growth', 'profit_margin', 'profit_margin_change',
                    'debt_to_cash', 'debt_growth', 'cash_change',
                    'cash_to_revenue', 'debt_to_revenue']
    available = [c for c in feature_cols if c in df.columns and df[c].notna().sum() >= 2]
    if len(available) < 2:
        print(f"[Anomaly] Not enough populated features: {available}")
        return {**default, "financial_summary": build_summary(df)}

    # Keep partially available rows and impute remaining gaps so sparse but useful
    # financial histories still produce an anomaly signal.
    df_model = df[available].copy()
    row_signal = df_model.notna().sum(axis=1)
    df_model = df_model[row_signal >= max(2, min(len(available), 3))]

    if len(df_model) < 2:
        print(f"[Anomaly] Not enough usable rows after filtering: {len(df_model)}")
        return {**default, "financial_summary": build_summary(df)}

    df_clean = df_model.fillna(df_model.median(numeric_only=True))

    print(f"[Anomaly] Running IsolationForest on {len(df_clean)} periods with {len(available)} features")

    scaler = StandardScaler()
    scaled = scaler.fit_transform(df_clean)

    # Scale contamination with dataset size
    contamination = min(0.18, max(0.08, 1.0 / len(df_clean)))
    iso = IsolationForest(contamination=contamination, random_state=42, n_estimators=150)
    predictions = iso.fit_predict(scaled)
    scores = iso.score_samples(scaled)

    df_result = df.loc[df_clean.index].copy()
    df_result['is_anomaly'] = predictions
    df_result['anomaly_score'] = scores

    anomalies = []
    for _, row in df_result[df_result['is_anomaly'] == -1].iterrows():
        anomalies.append({
            "date": str(row['filing_date'].date()),
            "explanation": generate_explanation(row),
            "severity": "high" if row['anomaly_score'] < -0.15 else "medium",
            "metrics": {
                "revenue_growth_pct": round(float(row['revenue_growth']) * 100, 1) if pd.notna(row.get('revenue_growth')) else None,
                "profit_margin_pct": round(float(row['profit_margin']) * 100, 1) if pd.notna(row.get('profit_margin')) else None,
                "debt_to_cash": round(float(row['debt_to_cash']), 2) if pd.notna(row.get('debt_to_cash')) else None,
            }
        })

    risk_level = "low" if len(anomalies) == 0 else "medium" if len(anomalies) <= 1 else "high"
    print(f"[Anomaly] Detected {len(anomalies)} anomalies — risk level: {risk_level}")

    return {
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "risk_level": risk_level,
        "total_periods_analyzed": len(df_clean),
        "financial_summary": build_summary(df)
    }

def build_summary(df: pd.DataFrame) -> dict:
    summary = {
        "avg_revenue_growth": 0.05,
        "latest_profit_margin": 0.08,
        "latest_debt_to_cash": 2.0,
        "revenue_trend": "stable",
        "data_years": len(df)
    }
    try:
        if 'revenue_growth' in df.columns and df['revenue_growth'].notna().any():
            summary['avg_revenue_growth'] = float(df['revenue_growth'].mean())
        if 'profit_margin' in df.columns and df['profit_margin'].notna().any():
            summary['latest_profit_margin'] = float(df['profit_margin'].dropna().iloc[-1])
        if 'debt_to_cash' in df.columns and df['debt_to_cash'].notna().any():
            summary['latest_debt_to_cash'] = float(df['debt_to_cash'].dropna().iloc[-1])
        if 'revenue_growth' in df.columns and len(df['revenue_growth'].dropna()) >= 2:
            recent = df['revenue_growth'].dropna().iloc[-2:].mean()
            summary['revenue_trend'] = "growing" if recent > 0.05 else "declining" if recent < -0.02 else "stable"
    except Exception as e:
        print(f"[Anomaly] Summary error: {e}")
    return summary
