import random
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.database.schema import SessionLocal, JobPosting

# Company-specific hiring profiles
COMPANY_PROFILES = {
    "apple": {"total": 450, "focus": "Engineering", "trend": "stable", "senior_ratio": 0.4},
    "microsoft": {"total": 520, "focus": "Engineering", "trend": "growing", "senior_ratio": 0.45},
    "google": {"total": 380, "focus": "Engineering", "trend": "shrinking", "senior_ratio": 0.5},
    "alphabet": {"total": 380, "focus": "Engineering", "trend": "shrinking", "senior_ratio": 0.5},
    "amazon": {"total": 680, "focus": "Operations", "trend": "stable", "senior_ratio": 0.3},
    "meta": {"total": 220, "focus": "Engineering", "trend": "shrinking", "senior_ratio": 0.55},
    "tesla": {"total": 410, "focus": "Engineering", "trend": "growing", "senior_ratio": 0.35},
    "netflix": {"total": 180, "focus": "Product", "trend": "stable", "senior_ratio": 0.5},
    "nvidia": {"total": 290, "focus": "Research", "trend": "growing", "senior_ratio": 0.55},
    "salesforce": {"total": 310, "focus": "Sales", "trend": "stable", "senior_ratio": 0.4},
    "jpmorgan": {"total": 580, "focus": "Finance", "trend": "stable", "senior_ratio": 0.45},
    "goldman sachs": {"total": 320, "focus": "Finance", "trend": "stable", "senior_ratio": 0.55},
    "walmart": {"total": 720, "focus": "Operations", "trend": "stable", "senior_ratio": 0.2},
    "target": {"total": 480, "focus": "Operations", "trend": "stable", "senior_ratio": 0.2},
    "pfizer": {"total": 350, "focus": "Research", "trend": "shrinking", "senior_ratio": 0.45},
    "tcs": {"total": 890, "focus": "Engineering", "trend": "growing", "senior_ratio": 0.3},
    "infosys": {"total": 760, "focus": "Engineering", "trend": "stable", "senior_ratio": 0.3},
    "wipro": {"total": 640, "focus": "Engineering", "trend": "stable", "senior_ratio": 0.3},
    "adani ports": {"total": 180, "focus": "Operations", "trend": "growing", "senior_ratio": 0.3},
    "reliance": {"total": 420, "focus": "Operations", "trend": "growing", "senior_ratio": 0.35},
    "zomato": {"total": 290, "focus": "Engineering", "trend": "growing", "senior_ratio": 0.35},
}

DEPT_WEIGHTS = {
    "Engineering": {"default": 35, "focus_boost": 15},
    "Sales": {"default": 18, "focus_boost": 15},
    "Marketing": {"default": 10, "focus_boost": 12},
    "Finance": {"default": 8, "focus_boost": 15},
    "Operations": {"default": 10, "focus_boost": 18},
    "Legal": {"default": 5, "focus_boost": 0},
    "HR": {"default": 5, "focus_boost": 0},
    "Product": {"default": 7, "focus_boost": 15},
    "Research": {"default": 5, "focus_boost": 18},
}

SENIORITY = ["Junior", "Mid", "Senior", "Director", "VP"]
SENIORITY_WEIGHTS = [20, 35, 30, 10, 5]
LOCATIONS = ["New York", "San Francisco", "Austin", "Remote", "Seattle", "Boston", "Chicago", "London", "Bangalore", "Singapore"]

def get_company_profile(company_name: str) -> dict:
    """Get company-specific hiring profile or generate a consistent one."""
    name_lower = company_name.lower().strip()

    # Direct match
    if name_lower in COMPANY_PROFILES:
        return COMPANY_PROFILES[name_lower]

    # Partial match
    for key, profile in COMPANY_PROFILES.items():
        if key in name_lower or name_lower in key:
            return profile

    # Generate consistent profile based on company name
    seed = int(hashlib.md5(name_lower.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    # Industry-based totals
    if any(w in name_lower for w in ['bank', 'financial', 'insurance']):
        total = rng.randint(250, 450)
        focus = "Finance"
    elif any(w in name_lower for w in ['tech', 'software', 'cloud', 'data']):
        total = rng.randint(200, 400)
        focus = "Engineering"
    elif any(w in name_lower for w in ['retail', 'store', 'mart']):
        total = rng.randint(400, 700)
        focus = "Operations"
    elif any(w in name_lower for w in ['pharma', 'bio', 'health', 'medical']):
        total = rng.randint(200, 380)
        focus = "Research"
    else:
        total = rng.randint(150, 350)
        focus = rng.choice(["Engineering", "Operations", "Sales"])

    trends = ["growing", "stable", "stable", "shrinking"]
    return {
        "total": total,
        "focus": focus,
        "trend": rng.choice(trends),
        "senior_ratio": round(rng.uniform(0.25, 0.55), 2)
    }

def generate_realistic_postings(company_name: str) -> list:
    """Generate company-specific realistic job postings over 12 months."""
    profile = get_company_profile(company_name)
    seed = int(hashlib.md5(company_name.lower().encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    total_postings = profile["total"]
    focus_dept = profile["focus"]
    trend = profile["trend"]
    senior_ratio = profile["senior_ratio"]

    # Build department weights based on focus
    weights = {}
    for dept, w in DEPT_WEIGHTS.items():
        if dept == focus_dept:
            weights[dept] = w["default"] + w["focus_boost"]
        else:
            weights[dept] = w["default"]

    postings = []
    base_date = datetime.now() - timedelta(days=365)

    # Distribute postings over 12 months with trend
    for month in range(12):
        # Apply trend to monthly volume
        if trend == "growing":
            monthly_factor = 1 + (month / 12) * 0.5
        elif trend == "shrinking":
            monthly_factor = 1 - (month / 12) * 0.4
        else:
            monthly_factor = 1 + rng.uniform(-0.1, 0.1)

        monthly_total = int((total_postings / 12) * monthly_factor)
        month_start = base_date + timedelta(days=month * 30)

        for _ in range(max(1, monthly_total)):
            dept = rng.choices(list(weights.keys()), weights=list(weights.values()))[0]

            # Senior ratio affects seniority distribution
            if rng.random() < senior_ratio:
                level_weights = [5, 20, 40, 25, 10]  # More senior
            else:
                level_weights = [25, 40, 25, 8, 2]   # More junior

            level = rng.choices(SENIORITY, weights=level_weights)[0]

            day_offset = rng.randint(0, 28)
            posting_date = month_start + timedelta(days=day_offset)

            # Location based on company
            name_lower = company_name.lower()
            if any(w in name_lower for w in ['tcs', 'infosys', 'wipro', 'adani', 'zomato', 'paytm', 'reliance']):
                locations = ["Bangalore", "Mumbai", "Hyderabad", "Chennai", "Pune", "Delhi", "Remote"]
            else:
                locations = LOCATIONS

            postings.append({
                "role_title": f"{level} {dept} {'Manager' if level in ['Director', 'VP'] else 'Specialist'}",
                "department": dept,
                "seniority_level": level,
                "posted_date": posting_date.strftime("%Y-%m-%d"),
                "location": rng.choice(locations)
            })

    return postings

def save_job_postings_to_db(company_id: int, postings: list):
    db: Session = SessionLocal()
    try:
        db.query(JobPosting).filter(JobPosting.company_id == company_id).delete()
        count = 0
        for posting in postings:
            job = JobPosting(
                company_id=company_id,
                role_title=posting["role_title"],
                department=posting["department"],
                seniority_level=posting["seniority_level"],
                posted_date=datetime.strptime(posting["posted_date"], "%Y-%m-%d").date(),
                location=posting["location"]
            )
            db.add(job)
            count += 1
        db.commit()
        print(f"[Hiring] Saved {count} job postings")
    except Exception as e:
        db.rollback()
        print(f"[Hiring] Error: {e}")
    finally:
        db.close()

def run_hiring_pipeline(company_name: str, company_id: int) -> list:
    print(f"[Hiring] Starting pipeline for: {company_name}")
    postings = generate_realistic_postings(company_name)
    print(f"[Hiring] Generated {len(postings)} company-specific postings")
    save_job_postings_to_db(company_id, postings)
    return postings
