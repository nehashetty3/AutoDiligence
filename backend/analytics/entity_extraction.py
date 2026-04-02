import re
from collections import Counter
from sqlalchemy.orm import Session
from backend.database.schema import SessionLocal, Filing, Company

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        print("[NER] Loading spaCy model...")
        _nlp = spacy.load("en_core_web_lg")
        print("[NER] spaCy loaded")
    return _nlp

def extract_entities(text: str) -> dict:
    if not text or len(text) < 100:
        return {"people": [], "organizations": [], "locations": []}
    nlp = get_nlp()
    chunks = [text[i:i+50000] for i in range(0, min(len(text), 200000), 50000)]
    people, orgs, locs = [], [], []
    for chunk in chunks:
        doc = nlp(chunk)
        for ent in doc.ents:
            if ent.label_ == "PERSON" and len(ent.text) > 3:
                people.append(ent.text.strip())
            elif ent.label_ == "ORG" and len(ent.text) > 2:
                orgs.append(ent.text.strip())
            elif ent.label_ in ["GPE", "LOC"]:
                locs.append(ent.text.strip())
    return {"people": people, "organizations": orgs, "locations": locs}

def extract_risk_factors(text: str) -> list:
    if not text:
        return []
    risk_phrases = ["risk", "uncertainty", "may adversely", "could negatively", "litigation",
                    "regulatory", "competition", "cybersecurity", "disruption", "decline", "failure to"]
    sentences = re.split(r'[.!?]+', text)
    risks = [s.strip() for s in sentences if len(s.strip()) > 50
             and any(p in s.lower() for p in risk_phrases)]
    risks.sort(key=len, reverse=True)
    return risks[:15]

def analyze_company_entities(company_id: int) -> dict:
    db = SessionLocal()
    try:
        filings = db.query(Filing).filter(
            Filing.company_id == company_id,
            Filing.raw_text.isnot(None)
        ).all()
        company = db.query(Company).filter(Company.id == company_id).first()
        company_name_parts = company.name.lower().split() if company else []
        if not filings:
            return {"key_people": [], "key_organizations": [], "top_risk_factors": [],
                    "summary": {"unique_people_mentioned": 0, "unique_organizations_mentioned": 0, "risk_statements_identified": 0}}
        all_people, all_orgs, all_risks = [], [], []
        for filing in filings:
            if filing.raw_text:
                ents = extract_entities(filing.raw_text)
                all_people.extend(ents["people"])
                all_orgs.extend(ents["organizations"])
                all_risks.extend(extract_risk_factors(filing.raw_text))
        people_freq = Counter(all_people).most_common(15)
        org_freq = Counter(all_orgs).most_common(20)
        filtered_orgs = [(o, c) for o, c in org_freq
                         if not any(p in o.lower() for p in company_name_parts) and len(o) > 3]
        return {
            "key_people": [{"name": n, "mentions": c} for n, c in people_freq],
            "key_organizations": [{"name": o, "mentions": c} for o, c in filtered_orgs[:15]],
            "top_risk_factors": all_risks[:10],
            "summary": {
                "unique_people_mentioned": len(set(all_people)),
                "unique_organizations_mentioned": len(set(all_orgs)),
                "risk_statements_identified": len(all_risks)
            }
        }
    finally:
        db.close()
