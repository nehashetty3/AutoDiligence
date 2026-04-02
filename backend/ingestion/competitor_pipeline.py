import requests
import time
import re

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _normalize_company_label(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"\b(limited|ltd|incorporated|inc|corp|corporation|company|co|plc|ag|group|holdings?)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _is_same_company(target_name: str, target_ticker: str, candidate_name: str, candidate_ticker: str = "") -> bool:
    target_norm = _normalize_company_label(target_name)
    candidate_norm = _normalize_company_label(candidate_name)
    target_ticker = (target_ticker or "").upper().split(".")[0]
    candidate_ticker = (candidate_ticker or "").upper().split(".")[0]

    if target_norm and candidate_norm and target_norm == candidate_norm:
        return True
    if target_ticker and candidate_ticker and target_ticker == candidate_ticker:
        return True
    return False


ALIAS_MAP = {
    "apple inc": "apple",
    "microsoft corp": "microsoft",
    "microsoft corporation": "microsoft",
    "alphabet inc": "alphabet",
    "meta platforms": "meta",
    "amazon com": "amazon",
    "amazon com inc": "amazon",
    "tesla inc": "tesla",
    "nvidia corp": "nvidia",
    "infosys ltd": "infosys",
    "wipro ltd": "wipro",
    "tata consultancy services limited": "tcs",
    "tata consultancy services": "tcs",
    "hcl technologies limited": "hcl technologies",
    "hdfc bank ltd": "hdfc bank",
    "icici bank ltd": "icici bank",
    "goldman sachs group": "goldman sachs",
    "goldman sachs group inc": "goldman sachs",
    "jpmorgan chase": "jpmorgan",
    "jpmorgan chase co": "jpmorgan",
    "blackrock inc": "blackrock",
    "state street corp": "state street",
    "the bank of new york mellon": "bank of new york mellon",
    "the pnc financial services": "pnc",
    "huntington bancshares incorporated": "huntington bancshares",
    "fifth third bancorp": "fifth third",
    "reliance industries limited": "reliance industries",
    "adani ports and special economic zone": "adani ports",
    "adani ports and special economic zone limited": "adani ports",
    "adani ports sez": "adani ports",
    "adani port": "adani ports",
    "adani ports": "adani ports",
    "byd company": "byd",
    "byd co": "byd",
    "byd co ltd": "byd",
    "byd company limited": "byd",
    "volkswagen": "volkswagen",
    "volkswagen ag": "volkswagen",
    "sony group": "sony",
    "sony group corporation": "sony",
}


TICKER_ALIAS_MAP = {
    "AAPL": "apple",
    "MSFT": "microsoft",
    "META": "meta",
    "AMZN": "amazon",
    "TSLA": "tesla",
    "NVDA": "nvidia",
    "INFY": "infosys",
    "WIT": "wipro",
    "TCS": "tcs",
    "TCS.NS": "tcs",
    "HCLTECH.NS": "hcl technologies",
    "HDB": "hdfc bank",
    "IBN": "icici bank",
    "GS": "goldman sachs",
    "JPM": "jpmorgan",
    "BLK": "blackrock",
    "STT": "state street",
    "BK": "bank of new york mellon",
    "PNC": "pnc",
    "HBAN": "huntington bancshares",
    "FITB": "fifth third",
    "RELIANCE": "reliance industries",
    "ADANIPORTS": "adani ports",
    "ADANIPORTS.BO": "adani ports",
    "ADANIPORTS.NS": "adani ports",
    "BYDDF": "byd",
    "BYDDY": "byd",
    "1211.HK": "byd",
    "LI": "li auto",
    "XPEV": "xpeng",
    "NIO": "nio",
    "VOW.PR": "volkswagen",
    "TM": "toyota",
    "SONY": "sony",
}


PROFILE_DEFAULTS = {
    "indian_it": ["TCS", "Infosys", "Wipro", "HCL Technologies"],
    "indian_bank": ["HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra Bank"],
    "global_bank": ["JPMorgan", "Morgan Stanley", "Goldman Sachs", "Bank of America"],
    "asset_management": ["BlackRock", "State Street", "Goldman Sachs", "JPMorgan"],
    "payments": ["Visa", "Mastercard", "PayPal", "American Express"],
    "consumer_tech": ["Apple", "Samsung", "Sony", "Google"],
    "platform_tech": ["Microsoft", "Amazon", "Google", "Meta"],
    "semis": ["Nvidia", "AMD", "Intel", "Qualcomm"],
    "enterprise_software": ["Microsoft", "Oracle", "Salesforce", "SAP"],
    "ev_auto": ["Tesla", "BYD", "Li Auto", "XPeng"],
    "legacy_auto": ["Toyota", "Volkswagen", "Ford", "GM"],
    "ports_logistics": ["JSW Infrastructure", "Gujarat Pipavav Port", "Container Corporation of India", "Gateway Distriparks"],
    "energy": ["Reliance Industries", "ONGC", "BP", "Shell"],
    "telecom": ["AT&T", "Verizon", "T-Mobile", "Comcast"],
    "pharma": ["Pfizer", "Johnson & Johnson", "Merck", "AbbVie"],
    "consumer": ["Hindustan Unilever", "ITC", "Nestle India", "Dabur"],
    "default": ["Accenture", "IBM", "Deloitte", "McKinsey"],
}


PROFILE_COMPATIBILITY = {
    "indian_it": {"indian_it"},
    "indian_bank": {"indian_bank", "global_bank"},
    "global_bank": {"global_bank", "asset_management", "payments"},
    "asset_management": {"asset_management", "global_bank"},
    "payments": {"payments", "global_bank"},
    "consumer_tech": {"consumer_tech", "platform_tech"},
    "platform_tech": {"platform_tech", "consumer_tech", "enterprise_software"},
    "enterprise_software": {"enterprise_software", "platform_tech"},
    "semis": {"semis", "consumer_tech"},
    "ev_auto": {"ev_auto", "legacy_auto"},
    "legacy_auto": {"legacy_auto", "ev_auto"},
    "ports_logistics": {"ports_logistics"},
    "energy": {"energy"},
    "telecom": {"telecom"},
    "pharma": {"pharma"},
    "consumer": {"consumer"},
    "default": {"default"},
}


def _canonical_company_key(company_name: str, ticker: str = "") -> str:
    normalized_name = _normalize_company_label(company_name)
    ticker_key = (ticker or "").upper()
    return (
        TICKER_ALIAS_MAP.get(ticker_key)
        or TICKER_ALIAS_MAP.get(ticker_key.split(".")[0])
        or ALIAS_MAP.get(normalized_name)
        or normalized_name
    )


def _infer_company_profile(company_name: str, ticker: str = "") -> str:
    key = _canonical_company_key(company_name, ticker)
    name = key.lower()
    ticker_base = (ticker or "").upper().split(".")[0]

    if any(term in name for term in ["infosys", "wipro", "tcs", "hcl technologies", "tech mahindra", "cognizant"]):
        return "indian_it"
    if any(term in name for term in ["hdfc bank", "icici bank", "axis bank", "kotak", "sbi"]):
        return "indian_bank"
    if any(term in name for term in ["blackrock", "state street", "vanguard", "fidelity"]):
        return "asset_management"
    if any(term in name for term in ["visa", "mastercard", "paypal", "american express"]):
        return "payments"
    if any(term in name for term in ["goldman sachs", "jpmorgan", "morgan stanley", "bank of america", "pnc", "mellon", "bancshares", "fifth third"]):
        return "global_bank"
    if any(term in name for term in ["apple", "samsung", "sony", "xiaomi", "huawei"]):
        return "consumer_tech"
    if any(term in name for term in ["microsoft", "amazon", "google", "alphabet", "meta"]):
        return "platform_tech"
    if any(term in name for term in ["salesforce", "oracle", "sap", "servicenow", "adobe"]):
        return "enterprise_software"
    if any(term in name for term in ["nvidia", "amd", "intel", "qualcomm", "broadcom"]):
        return "semis"
    if any(term in name for term in ["tesla", "byd", "li auto", "xpeng", "nio", "rivian"]) or ticker_base in {"TSLA", "BYDDF", "BYDDY", "LI", "XPEV", "NIO"}:
        return "ev_auto"
    if any(term in name for term in ["toyota", "volkswagen", "ford", "gm", "stellantis", "honda"]):
        return "legacy_auto"
    if any(term in name for term in ["adani ports", "gujarat pipavav", "dp world", "port", "logistics", "shipping"]):
        return "ports_logistics"
    if any(term in name for term in ["reliance", "ongc", "bp", "shell", "exxon", "chevron", "oil", "gas", "energy"]):
        return "energy"
    if any(term in name for term in ["telecom", "wireless", "verizon", "at t", "comcast", "airtel"]):
        return "telecom"
    if any(term in name for term in ["pharma", "pfizer", "merck", "johnson", "abbvie", "biotech", "therapeutics"]):
        return "pharma"
    if any(term in name for term in ["hindustan unilever", "itc", "nestle", "dabur", "britannia", "marico"]):
        return "consumer"
    return "default"


def _profiles_compatible(target_profile: str, candidate_profile: str) -> bool:
    allowed = PROFILE_COMPATIBILITY.get(target_profile, {target_profile})
    return candidate_profile in allowed

# Comprehensive competitor map — covers most searched companies
COMPETITOR_MAP = {
    # Big Tech US
    "apple": ["Microsoft", "Samsung", "Google", "Sony"],
    "microsoft": ["Apple", "Google", "Amazon", "Salesforce"],
    "google": ["Microsoft", "Apple", "Meta", "Amazon"],
    "alphabet": ["Microsoft", "Apple", "Meta", "Amazon"],
    "meta": ["Google", "TikTok", "Twitter", "Snap"],
    "amazon": ["Microsoft", "Walmart", "Google", "Alibaba"],
    "netflix": ["Disney", "Amazon Prime", "HBO Max", "Apple TV"],
    "tesla": ["BYD", "Ford", "Volkswagen", "Rivian"],
    "byd": ["Tesla", "Li Auto", "XPeng", "NIO"],
    "li auto": ["BYD", "XPeng", "NIO", "Tesla"],
    "xpeng": ["BYD", "Li Auto", "NIO", "Tesla"],
    "nio": ["BYD", "Li Auto", "XPeng", "Tesla"],
    "nvidia": ["AMD", "Intel", "Qualcomm", "Broadcom"],
    "intel": ["AMD", "Nvidia", "Qualcomm", "ARM"],
    "amd": ["Intel", "Nvidia", "Qualcomm", "Broadcom"],
    "salesforce": ["Microsoft", "Oracle", "SAP", "HubSpot"],
    "oracle": ["Microsoft", "SAP", "Salesforce", "IBM"],
    "ibm": ["Accenture", "Microsoft", "Oracle", "HPE"],
    "adobe": ["Microsoft", "Canva", "Figma", "Salesforce"],
    "uber": ["Lyft", "DoorDash", "Grab", "Bolt"],
    "airbnb": ["Booking Holdings", "Expedia", "Marriott", "Hilton"],
    "spotify": ["Apple Music", "Amazon Music", "YouTube Music", "Tidal"],
    "paypal": ["Visa", "Mastercard", "Square", "Stripe"],
    "twitter": ["Meta", "TikTok", "LinkedIn", "Snapchat"],
    "snap": ["Meta", "TikTok", "Twitter", "Pinterest"],
    "shopify": ["WooCommerce", "BigCommerce", "Magento", "Squarespace"],
    "zoom": ["Microsoft Teams", "Google Meet", "Cisco Webex", "Slack"],

    # Finance US
    "jpmorgan": ["Goldman Sachs", "Morgan Stanley", "Bank of America", "Citigroup"],
    "goldman sachs": ["JPMorgan", "Morgan Stanley", "BlackRock", "Citigroup"],
    "morgan stanley": ["Goldman Sachs", "JPMorgan", "BlackRock", "UBS"],
    "bank of america": ["JPMorgan", "Wells Fargo", "Citigroup", "Goldman Sachs"],
    "wells fargo": ["JPMorgan", "Bank of America", "Citigroup", "US Bancorp"],
    "blackrock": ["Vanguard", "Fidelity", "State Street", "Goldman Sachs"],
    "visa": ["Mastercard", "PayPal", "American Express", "Discover"],
    "mastercard": ["Visa", "PayPal", "American Express", "UnionPay"],

    # Indian IT
    "tcs": ["Infosys", "Wipro", "HCL Technologies", "Accenture"],
    "tata consultancy": ["Infosys", "Wipro", "HCL Technologies", "Accenture"],
    "infosys": ["TCS", "Wipro", "HCL Technologies", "Tech Mahindra"],
    "wipro": ["TCS", "Infosys", "HCL Technologies", "Tech Mahindra"],
    "hcl": ["TCS", "Infosys", "Wipro", "Tech Mahindra"],
    "hcl technologies": ["TCS", "Infosys", "Wipro", "Tech Mahindra"],
    "tech mahindra": ["TCS", "Infosys", "Wipro", "HCL Technologies"],
    "mphasis": ["Infosys BPM", "Wipro", "Hexaware", "Cognizant"],
    "cognizant": ["TCS", "Infosys", "Wipro", "Accenture"],

    # Indian Banking
    "hdfc bank": ["ICICI Bank", "SBI", "Axis Bank", "Kotak Mahindra Bank"],
    "hdfc": ["ICICI Bank", "SBI", "Axis Bank", "Kotak Mahindra Bank"],
    "icici bank": ["HDFC Bank", "SBI", "Axis Bank", "Kotak Mahindra Bank"],
    "icici": ["HDFC Bank", "SBI", "Axis Bank", "Kotak Mahindra Bank"],
    "sbi": ["HDFC Bank", "ICICI Bank", "Axis Bank", "Punjab National Bank"],
    "axis bank": ["HDFC Bank", "ICICI Bank", "Kotak Mahindra Bank", "IndusInd Bank"],
    "kotak": ["HDFC Bank", "ICICI Bank", "Axis Bank", "IndusInd Bank"],
    "kotak mahindra": ["HDFC Bank", "ICICI Bank", "Axis Bank", "IndusInd Bank"],
    "bajaj finance": ["HDFC Bank", "Kotak Mahindra", "Muthoot Finance", "Shriram Finance"],
    "bajaj finserv": ["HDFC Bank", "Bajaj Finance", "Kotak Mahindra", "SBI Life"],

    # Indian Consumer & Retail
    "reliance": ["Tata Group", "Adani Group", "Mahindra", "Bajaj"],
    "reliance industries": ["ONGC", "BP", "Shell", "Adani Enterprises"],
    "hindustan unilever": ["Procter & Gamble India", "Nestle India", "ITC", "Dabur"],
    "hul": ["P&G India", "Nestle India", "ITC", "Dabur"],
    "itc": ["Hindustan Unilever", "Nestle India", "Dabur", "Britannia"],
    "asian paints": ["Berger Paints", "Kansai Nerolac", "Indigo Paints", "Akzo Nobel India"],
    "britannia": ["Nestle India", "ITC", "Parle", "Mondelez India"],
    "nestle india": ["Hindustan Unilever", "ITC", "Britannia", "Dabur"],
    "dabur": ["Hindustan Unilever", "Emami", "Marico", "Colgate"],
    "marico": ["Hindustan Unilever", "Dabur", "Emami", "Bajaj Consumer"],

    # Indian Auto
    "maruti": ["Hyundai India", "Tata Motors", "Mahindra", "Kia India"],
    "maruti suzuki": ["Hyundai India", "Tata Motors", "Mahindra", "Kia India"],
    "tata motors": ["Maruti Suzuki", "Hyundai India", "Mahindra", "Kia India"],
    "mahindra": ["Tata Motors", "Maruti Suzuki", "Force Motors", "Bajaj Auto"],
    "bajaj auto": ["Hero MotoCorp", "TVS Motor", "Honda Motorcycles", "Royal Enfield"],
    "hero motocorp": ["Bajaj Auto", "TVS Motor", "Honda Motorcycles", "Royal Enfield"],
    "tvs motor": ["Bajaj Auto", "Hero MotoCorp", "Honda Motorcycles", "Royal Enfield"],
    "eicher motors": ["Bajaj Auto", "TVS Motor", "Hero MotoCorp", "Harley Davidson India"],

    # Indian Pharma
    "sun pharma": ["Dr Reddys", "Cipla", "Lupin", "Aurobindo Pharma"],
    "sun pharmaceutical": ["Dr Reddys", "Cipla", "Lupin", "Aurobindo Pharma"],
    "dr reddys": ["Sun Pharma", "Cipla", "Lupin", "Aurobindo Pharma"],
    "cipla": ["Sun Pharma", "Dr Reddys", "Lupin", "Aurobindo Pharma"],
    "lupin": ["Sun Pharma", "Dr Reddys", "Cipla", "Aurobindo Pharma"],
    "divis": ["Sun Pharma", "Dr Reddys", "Laurus Labs", "Divi's Laboratories"],

    # Indian Infrastructure
    "adani ports": ["JSW Infrastructure", "Gujarat Pipavav Port", "Container Corporation of India", "Gateway Distriparks"],
    "adani enterprises": ["Tata Group", "Reliance Industries", "JSW Group", "Vedanta"],
    "adani green": ["Tata Power Renewables", "ReNew Power", "Greenko", "NTPC Green"],
    "adani": ["Tata Group", "Reliance Industries", "JSW Group", "Mahindra"],
    "larsen": ["Tata Projects", "Shapoorji Pallonji", "Bajaj Construction", "Afcons"],
    "l&t": ["Tata Projects", "Shapoorji Pallonji", "Siemens India", "ABB India"],
    "ntpc": ["Tata Power", "Adani Power", "Torrent Power", "CESC"],
    "tata power": ["NTPC", "Adani Power", "Torrent Power", "JSW Energy"],
    "ongc": ["Reliance Industries", "Oil India", "Cairn India", "BPCL"],

    # Indian New Age
    "zomato": ["Swiggy", "Dunzo", "BigBasket", "Zepto"],
    "swiggy": ["Zomato", "Dunzo", "Amazon Food", "Uber Eats India"],
    "paytm": ["PhonePe", "Google Pay", "Amazon Pay", "BHIM UPI"],
    "nykaa": ["Myntra", "Purplle", "Amazon Beauty", "Flipkart Beauty"],
    "policybazaar": ["Coverfox", "Digit Insurance", "Acko", "InsuranceDekho"],

    # Indian Conglomerates
    "titan": ["Kalyan Jewellers", "Tanishq", "Malabar Gold", "PC Jeweller"],
    "titan company": ["Kalyan Jewellers", "Malabar Gold", "Senco Gold", "PC Jeweller"],
    "tata group": ["Reliance Industries", "Adani Group", "Mahindra Group", "Aditya Birla Group"],
    "aditya birla": ["Tata Group", "Reliance Industries", "Mahindra", "JSW Group"],
    "jsw": ["Tata Steel", "SAIL", "Jindal Steel", "NMDC"],
    "vedanta": ["Hindalco", "Tata Steel", "JSW Steel", "NMDC"],

    # Global
    "samsung": ["Apple", "Xiaomi", "Huawei", "Sony"],
    "alibaba": ["Amazon", "JD.com", "Pinduoduo", "Lazada"],
    "toyota": ["Volkswagen", "Ford", "GM", "Honda"],
    "volkswagen": ["Toyota", "Ford", "GM", "Stellantis"],
    "sony": ["Samsung", "Apple", "Microsoft", "Nintendo"],
    "hsbc": ["Standard Chartered", "Barclays", "Lloyds", "NatWest"],
    "bp": ["Shell", "ExxonMobil", "Chevron", "TotalEnergies"],
    "shell": ["BP", "ExxonMobil", "Chevron", "TotalEnergies"],
    "lvmh": ["Kering", "Richemont", "Hermes", "Burberry"],
    "nestle": ["Unilever", "PepsiCo", "Kraft Heinz", "Danone"],

    # US Healthcare
    "johnson & johnson": ["Pfizer", "Abbott", "Merck", "Roche"],
    "pfizer": ["Moderna", "AstraZeneca", "Johnson & Johnson", "Merck"],
    "merck": ["Pfizer", "Johnson & Johnson", "AbbVie", "Bristol Myers"],
    "unitedhealth": ["CVS Health", "Cigna", "Anthem", "Humana"],
    "abbvie": ["Pfizer", "Merck", "Bristol Myers", "Amgen"],

    # US Energy
    "exxonmobil": ["Chevron", "Shell", "BP", "ConocoPhillips"],
    "chevron": ["ExxonMobil", "Shell", "BP", "TotalEnergies"],

    # US Retail
    "walmart": ["Amazon", "Target", "Costco", "Kroger"],
    "target": ["Walmart", "Amazon", "Costco", "Dollar General"],
    "costco": ["Walmart", "Target", "BJs Wholesale", "Amazon"],
    "home depot": ["Lowes", "Menards", "Ace Hardware", "True Value"],
}


def get_industry_defaults(company_name: str, ticker: str) -> list:
    profile = _infer_company_profile(company_name, ticker)
    return PROFILE_DEFAULTS.get(profile, PROFILE_DEFAULTS["default"])

def fetch_yahoo_recommendations(ticker: str) -> list:
    """
    Use Yahoo Finance recommendations API to get real peer companies.
    This returns companies that analysts actually compare together.
    """
    if not ticker or ticker.startswith("YAHOO_") or ticker.startswith("NON_US_"):
        return []
    try:
        url = f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{ticker}"
        response = requests.get(url, headers=YAHOO_HEADERS, timeout=8)
        data = response.json()
        recommendations = data.get("finance", {}).get("result", [])
        if recommendations:
            peers = recommendations[0].get("recommendedSymbols", [])
            peer_tickers = [p.get("symbol", "") for p in peers[:6] if p.get("symbol")]
            if peer_tickers:
                print(f"[Competitors] Yahoo recommendations for {ticker}: {peer_tickers}")
                return peer_tickers
    except Exception as e:
        print(f"[Competitors] Yahoo recommendations error: {e}")
    return []

def resolve_ticker_candidate(ticker: str) -> dict:
    """Convert a ticker symbol to a company descriptor via Yahoo Finance."""
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search"
        params = {"q": ticker, "quotesCount": 1, "newsCount": 0}
        response = requests.get(url, params=params, headers=YAHOO_HEADERS, timeout=5)
        data = response.json()
        quotes = [q for q in data.get("quotes", []) if q.get("quoteType") == "EQUITY"]
        if quotes:
            quote = quotes[0]
            return {
                "name": quote.get("longname") or quote.get("shortname") or ticker,
                "ticker": quote.get("symbol") or ticker,
            }
    except:
        pass
    return {"name": ticker, "ticker": ticker}

def identify_competitors(company_name: str, ticker: str) -> list:
    """
    Multi-strategy competitor identification:
    1. Check curated map (most accurate)
    2. Try Yahoo Finance peer recommendations, but only keep profile-compatible peers
    3. Fall back to profile-based defaults
    """
    name_lower = _canonical_company_key(company_name, ticker)
    target_ticker = (ticker or "").upper()
    target_profile = _infer_company_profile(company_name, ticker)

    def finalize(peers):
        cleaned = []
        seen = set()
        for peer in peers:
            peer_name = peer if isinstance(peer, str) else str(peer)
            norm = _normalize_company_label(peer_name)
            if not norm or norm in seen:
                continue
            if _is_same_company(company_name, target_ticker, peer_name):
                continue
            seen.add(norm)
            cleaned.append(peer_name)
        return cleaned[:4]

    # Strategy 1: Curated map — exact match
    if name_lower in COMPETITOR_MAP:
        peers = finalize(COMPETITOR_MAP[name_lower])
        print(f"[Competitors] Found in curated map: {peers}")
        return peers

    # Strategy 1b: Partial match in curated map
    for key, competitors in COMPETITOR_MAP.items():
        if key in name_lower or name_lower in key:
            peers = finalize(competitors)
            print(f"[Competitors] Partial match '{key}': {peers}")
            return peers

    # Strategy 2: Yahoo Finance peer recommendations (uses real analyst data)
    if ticker and not ticker.startswith(("YAHOO_", "NON_US_")):
        peer_tickers = fetch_yahoo_recommendations(ticker)
        if len(peer_tickers) >= 3:
            # Resolve tickers to names
            peer_names = []
            for pt in peer_tickers[:4]:
                candidate = resolve_ticker_candidate(pt)
                candidate_name = candidate["name"]
                candidate_ticker = candidate["ticker"]
                if _is_same_company(company_name, target_ticker, candidate_name, candidate_ticker):
                    time.sleep(0.2)
                    continue
                candidate_profile = _infer_company_profile(candidate_name, candidate_ticker)
                if _profiles_compatible(target_profile, candidate_profile):
                    peer_names.append(candidate_name)
                time.sleep(0.2)
            peer_names = finalize(peer_names)
            if len(peer_names) >= 2:
                print(f"[Competitors] Using Yahoo peer data: {peer_names}")
                return peer_names

    # Strategy 3: Industry-based defaults
    defaults = finalize(get_industry_defaults(company_name, ticker))
    print(f"[Competitors] Using industry defaults: {defaults}")
    return defaults

def run_competitor_identification(company_name: str, ticker: str) -> list:
    print(f"[Competitors] Identifying competitors for: {company_name} ({ticker})")
    competitors = identify_competitors(company_name, ticker)
    print(f"[Competitors] Result: {competitors}")
    return competitors
