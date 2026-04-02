import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_llm_client():
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key not in ["your_groq_key_here", ""]:
        try:
            from groq import Groq
            return ("groq", Groq(api_key=groq_key))
        except ImportError:
            pass
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key not in ["your_gemini_key_here", ""]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            return ("gemini", genai)
        except ImportError:
            pass
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key not in ["your_openai_key_here", "skip", ""]:
        try:
            from openai import OpenAI
            return ("openai", OpenAI(api_key=openai_key))
        except ImportError:
            pass
    return ("fallback", None)

def call_llm(prompt: str) -> str:
    provider, client = get_llm_client()
    try:
        if provider == "groq":
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000, temperature=0.3
            )
            return response.choices[0].message.content
        elif provider == "gemini":
            model = client.GenerativeModel("gemini-1.5-flash")
            return model.generate_content(prompt).text
        elif provider == "openai":
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000, temperature=0.3
            )
            return response.choices[0].message.content
    except Exception as e:
        print(f"[Report] LLM error: {e}")
    return None

def retrieve_relevant_context(company_id: int, query: str) -> str:
    try:
        from backend.llm.rag_pipeline import retrieve_relevant_context as rag_retrieve
        return rag_retrieve(company_id, query) or ""
    except:
        return ""

def generate_report(company_name: str, company_id: int, analytics_results: dict,
                    risk_assessment: dict) -> str:
    anomalies = analytics_results.get('anomalies', {})
    sentiment = analytics_results.get('sentiment', {})
    patents = analytics_results.get('patents', {})
    hiring = analytics_results.get('hiring', {})

    financial_context = retrieve_relevant_context(company_id, "financial performance revenue earnings risk")
    competitive_context = retrieve_relevant_context(company_id, "competition market position competitors")

    prompt = f"""You are a senior M&A consultant at a top-tier advisory firm (McKinsey/Goldman Sachs level).
Generate a professional due diligence report for {company_name}.

QUANTITATIVE DATA:
- Overall Risk Score: {risk_assessment.get('risk_score', 'N/A')}/100
- Risk Category: {risk_assessment.get('risk_category', 'N/A').upper()}
- Financial Anomalies Detected: {anomalies.get('anomaly_count', 0)}
- News Sentiment: {sentiment.get('overall_sentiment', 'N/A')} (score: {sentiment.get('overall_score', 'N/A')})
- Sentiment Trend: {sentiment.get('sentiment_trend', 'N/A')}
- Patent Velocity: {patents.get('velocity', {}).get('trend', 'N/A')}
- Dominant Innovation Area: {patents.get('dominant_innovation_area', 'N/A')}
- Hiring Health Score: {hiring.get('hiring_health_score', 'N/A')}/100
- Hiring Trend: {hiring.get('overall_hiring_trend', 'N/A')}
- Hiring Red Flags: {len(hiring.get('red_flags', []))}
- Key Risk Drivers: {risk_assessment.get('narrative', '')}

ADDITIONAL CONTEXT:
{financial_context[:800] if financial_context else 'SEC filing analysis completed'}
{competitive_context[:400] if competitive_context else 'Competitive analysis completed'}

Generate a structured report with these EXACT sections:

## Executive Summary
[3-4 sentences with direct acquisition recommendation]

## Financial Health Assessment
[Revenue trends, margins, debt position, anomalies with specific numbers]

## Leadership & Talent Risk
[Hiring trends, red flags, organizational health]

## Innovation & Competitive Position
[Patent analysis, innovation velocity, competitive landscape]

## Red Flags & Deal Breakers
[All flagged concerns with HIGH/MEDIUM/LOW severity]

## Strategic Recommendation
[Final verdict with specific rationale and conditions]

Tone: Professional, direct, data-backed. Suitable for C-suite presentation."""

    try:
        result = call_llm(prompt)
        if result:
            print(f"[Report] Generated for {company_name}")
            return result
    except Exception as e:
        print(f"[Report] Error: {e}")

    return generate_fallback_report(company_name, analytics_results, risk_assessment)

def generate_fallback_report(company_name: str, analytics_results: dict, risk_assessment: dict) -> str:
    risk_score = risk_assessment.get('risk_score', 50)
    risk_cat = risk_assessment.get('risk_category', 'medium').upper()
    sentiment = analytics_results.get('sentiment', {})
    anomalies = analytics_results.get('anomalies', {})
    patents = analytics_results.get('patents', {})
    hiring = analytics_results.get('hiring', {})

    if risk_score > 75:
        rec = "DO NOT PROCEED without significant risk mitigation planning."
    elif risk_score > 45:
        rec = "PROCEED WITH CONDITIONS — enhanced due diligence required."
    else:
        rec = "PROCEED with standard due diligence process."

    return f"""## Executive Summary
AutoDiligence has completed a comprehensive analysis of {company_name}, assigning an overall risk score of {risk_score:.0f}/100 ({risk_cat} risk). The analysis covered SEC financial filings, news sentiment over 24 months, patent innovation activity, and hiring patterns. {rec}

## Financial Health Assessment
Financial analysis identified {anomalies.get('anomaly_count', 0)} statistical anomalies using IsolationForest detection across revenue growth, profit margins, debt ratios, and cash burn rates. {"Multiple anomalies signal irregular financial patterns requiring deeper investigation." if anomalies.get('anomaly_count', 0) > 1 else "Financial metrics appear within acceptable parameters."} Overall financial risk: {anomalies.get('risk_level', 'medium').upper()}.

## Leadership & Talent Risk
Hiring pattern analysis across {hiring.get('total_postings_analyzed', 0)} job postings reveals an overall {hiring.get('overall_hiring_trend', 'stable')} trajectory with a health score of {hiring.get('hiring_health_score', 50):.0f}/100. {f"Red flags identified: {'; '.join([r['description'] for r in hiring.get('red_flags', [])])}." if hiring.get('red_flags') else "No significant hiring anomalies detected."}

## Innovation & Competitive Position
Patent analysis identified {patents.get('total_patents_analyzed', 0)} patents with dominant focus in {patents.get('dominant_innovation_area', 'technology')}. Innovation velocity is {patents.get('velocity', {}).get('trend', 'stable')} with diversity score {patents.get('innovation_diversity_score', 0.5):.2f}/1.0. News sentiment: {sentiment.get('overall_sentiment', 'neutral')} with a {sentiment.get('sentiment_trend', 'stable')} trajectory over {sentiment.get('total_articles_analyzed', 0)} articles.

## Red Flags & Deal Breakers
{"CRITICAL: Multiple risk indicators identified across financial and operational dimensions." if risk_score > 65 else "MODERATE: Several risk factors require attention before proceeding." if risk_score > 35 else "LOW: No critical deal breakers identified at this stage."} Sentiment score: {sentiment.get('overall_score', 0.5):.2f}/1.0.

## Strategic Recommendation
{rec} Risk profile is {risk_cat} with a score of {risk_score:.0f}/100. {"Recommend deep-dive investigation into flagged financial anomalies and sentiment deterioration before proceeding." if risk_score > 65 else "Recommend validating financial projections and monitoring sentiment trend before final close." if risk_score > 35 else "Risk profile is acceptable for acquisition consideration."}

*Report generated by AutoDiligence — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*"""

def export_report_pdf(report_text: str, company_name: str) -> bytes:
    try:
        from fpdf import FPDF

        def clean(text):
            """Remove non-latin characters that FPDF can't handle."""
            return ''.join(c if ord(c) < 128 else '?' for c in (text or ''))

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_page()

        # Header
        pdf.set_fill_color(10, 37, 64)
        pdf.rect(0, 0, 210, 28, 'F')
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(0, 8)
        pdf.cell(210, 10, "AutoDiligence", align="C", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(180, 200, 220)
        pdf.cell(210, 6, "M&A Due Diligence Intelligence Platform", align="C", ln=True)

        # Title bar
        pdf.set_fill_color(245, 244, 240)
        pdf.rect(0, 28, 210, 20, 'F')
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(26, 25, 22)
        pdf.set_xy(15, 33)
        pdf.cell(0, 8, clean(f"Due Diligence Report: {company_name}"), ln=True)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(130, 130, 130)
        pdf.set_x(15)
        pdf.cell(0, 5, f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}  |  Confidential", ln=True)

        # Divider
        pdf.set_draw_color(10, 37, 64)
        pdf.set_line_width(0.5)
        pdf.line(15, 50, 195, 50)
        pdf.ln(8)

        # Body
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(26, 25, 22)

        for line in report_text.split('\n'):
            line = clean(line)
            if line.startswith('## '):
                pdf.ln(4)
                pdf.set_fill_color(240, 253, 244)
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(10, 37, 64)
                pdf.set_x(15)
                pdf.cell(180, 8, line[3:], fill=True, ln=True)
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(26, 25, 22)
                pdf.ln(2)
            elif line.startswith('- ') or line.startswith('* '):
                pdf.set_x(20)
                pdf.multi_cell(175, 5, f"- {clean(line[2:])}")
            elif line.strip():
                pdf.set_x(15)
                pdf.multi_cell(180, 5, line)

        # Footer
        pdf.set_y(-18)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(160, 160, 160)
        pdf.cell(0, 8, f"AutoDiligence AI Platform  |  Confidential  |  {datetime.now().strftime('%Y-%m-%d')}", align="C")

        output = pdf.output(dest="S")
        if isinstance(output, bytearray):
            return bytes(output)
        if isinstance(output, bytes):
            return output
        return output.encode("latin-1")

    except Exception as e:
        print(f"[PDF] Error: {e}")
        import traceback
        traceback.print_exc()
        return report_text.encode('utf-8')
