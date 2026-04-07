"""Transaction classifier — keyword matching first, LLM fallback.

Classification hierarchy:
1. Keyword rules (instant, free, covers ~70-80% of transactions)
2. Cached classifications (previously classified supplier+description combos)
3. LLM classification via Claude Haiku (batched, cheap, for ambiguous items)
"""

import re
from dataclasses import dataclass


@dataclass
class Classification:
    scope: int  # 1, 2, or 3
    ghg_category: int | None  # 1-15 for Scope 3, None for Scope 1/2
    category_name: str
    method: str  # "keyword", "cached", "llm", "manual"
    confidence: float  # 0.0 to 1.0


# ── KEYWORD RULES ──
# Each rule: (patterns, Classification)
# Patterns are checked against supplier name + description (lowercase)

KEYWORD_RULES: list[tuple[list[str], Classification]] = [
    # ━━━ SCOPE 1: Direct emissions ━━━

    # Natural gas / heating
    (["british gas", "gas bill", "natural gas", "heating oil", "calor gas",
      "lpg", "propane", "butane", "kerosene", "heating fuel"],
     Classification(1, None, "Stationary combustion — gas/heating fuel", "keyword", 0.95)),

    # Company vehicles / fleet fuel
    (["shell fuel", "bp fuel", "esso", "texaco", "total energies", "fuel card",
      "petrol", "diesel", "fleet fuel", "company vehicle", "motor fuel",
      "applegreen", "certas energy", "harvest energy"],
     Classification(1, None, "Mobile combustion — company vehicles", "keyword", 0.90)),

    # Refrigerants
    (["refrigerant", "f-gas", "r-410a", "r-134a", "r-32", "aircon refill",
      "air conditioning recharge", "coolant top"],
     Classification(1, None, "Fugitive emissions — refrigerants", "keyword", 0.85)),

    # ━━━ SCOPE 2: Purchased energy ━━━

    (["electricity", "electric bill", "edf energy", "eon", "e.on", "sse",
      "scottish power", "scottishpower", "octopus energy", "bulb energy",
      "npower", "good energy", "haven power", "opus energy", "total gas & power",
      "drax", "smartest energy", "crown energy", "pozitive energy",
      "british gas electric", "power bill", "kwh"],
     Classification(2, None, "Purchased electricity", "keyword", 0.95)),

    (["district heating", "district heat", "steam supply", "chp",
      "combined heat and power"],
     Classification(2, None, "Purchased heat/steam/cooling", "keyword", 0.85)),

    # ━━━ SCOPE 3 CATEGORY 1: Purchased goods & services ━━━

    # Office supplies
    (["office supplies", "stationery", "paper", "printer cartridge", "toner",
      "envelopes", "pens", "staples", "post-it", "lyreco", "viking direct",
      "office depot", "banner business"],
     Classification(3, 1, "Purchased goods — office supplies", "keyword", 0.85)),

    # IT equipment
    (["computer", "laptop", "monitor", "keyboard", "mouse", "printer",
      "dell", "lenovo", "hp ", "apple mac", "ipad", "tablet",
      "server", "network equipment", "cisco", "software licence"],
     Classification(3, 1, "Purchased goods — IT equipment", "keyword", 0.80)),

    # Catering / food
    (["catering", "food supply", "ingredients", "beverages", "coffee",
      "nescafe", "coca-cola", "pepsi", "brakes", "bidfood", "booker",
      "3663", "sysco", "compass group", "sodexo", "aramark", "elior",
      "greggs", "costa", "baxter storey", "charlton house", "benugo"],
     Classification(3, 1, "Purchased goods — catering/food", "keyword", 0.85)),

    # Drinks / alcohol
    (["beer", "wine", "spirits", "alcohol", "brewery", "heineken",
      "diageo", "molson coors", "carlsberg", "greene king", "marston",
      "punch taverns", "matthew clark", "bibendum"],
     Classification(3, 1, "Purchased goods — drinks/alcohol", "keyword", 0.85)),

    # Cleaning
    (["cleaning", "janitorial", "hygiene", "soap", "sanitiser",
      "bunzl", "jangro", "initial", "rentokil"],
     Classification(3, 1, "Purchased goods — cleaning/hygiene", "keyword", 0.85)),

    # Merchandise / promotional
    (["merchandise", "promotional", "branded goods", "uniforms", "clothing",
      "t-shirt", "hoodie", "freshers", "bpma"],
     Classification(3, 1, "Purchased goods — merchandise/promotional", "keyword", 0.80)),

    # Professional services
    (["legal", "solicitor", "accountant", "audit", "consulting", "consultancy",
      "advisory", "deloitte", "kpmg", "pwc", "ey ", "ernst & young",
      "grant thornton", "bdo", "mazars"],
     Classification(3, 1, "Purchased services — professional", "keyword", 0.80)),

    # Marketing / advertising
    (["marketing", "advertising", "google ads", "facebook ads", "social media",
      "design agency", "creative agency", "print", "printing",
      "signage", "banners", "leaflets", "flyers"],
     Classification(3, 1, "Purchased services — marketing", "keyword", 0.80)),

    # Insurance
    (["insurance", "aviva", "axa", "zurich", "allianz", "hiscox",
      "marsh", "aon", "willis towers"],
     Classification(3, 1, "Purchased services — insurance", "keyword", 0.85)),

    # Telecoms
    (["telephone", "telecom", "mobile phone", "vodafone", "o2", "ee",
      "three", "bt ", "bt business", "virgin media", "sky broadband",
      "internet", "broadband", "wifi"],
     Classification(3, 1, "Purchased services — telecoms", "keyword", 0.85)),

    # ━━━ SCOPE 3 CATEGORY 2: Capital goods ━━━

    (["furniture", "desk", "chair", "table", "shelving", "fitout",
      "refurbishment", "renovation", "building work", "construction",
      "hvac", "boiler install", "solar panel"],
     Classification(3, 2, "Capital goods", "keyword", 0.75)),

    # ━━━ SCOPE 3 CATEGORY 4: Upstream transport ━━━

    (["courier", "delivery", "dhl", "ups", "fedex", "royal mail",
      "parcelforce", "hermes", "yodel", "dpd", "tnt", "freight",
      "shipping", "haulage", "logistics"],
     Classification(3, 4, "Upstream transport & distribution", "keyword", 0.80)),

    # ━━━ SCOPE 3 CATEGORY 5: Waste ━━━

    (["waste", "recycling", "skip hire", "biffa", "veolia", "viridor",
      "suez", "grundon", "waste management", "landfill", "composting",
      "bin collection", "refuse"],
     Classification(3, 5, "Waste generated in operations", "keyword", 0.90)),

    # ━━━ SCOPE 3 CATEGORY 6: Business travel ━━━

    (["train ticket", "rail ticket", "national rail", "lner", "gwr",
      "avanti", "crosscountry", "scotrail", "trainline", "railcard"],
     Classification(3, 6, "Business travel — rail", "keyword", 0.90)),

    (["flight", "airline", "british airways", "easyjet", "ryanair",
      "virgin atlantic", "jet2", "klm", "lufthansa", "air france",
      "skyscanner", "booking.com flight"],
     Classification(3, 6, "Business travel — air", "keyword", 0.90)),

    (["taxi", "uber", "bolt", "addison lee", "gett", "cab fare",
      "minicab"],
     Classification(3, 6, "Business travel — taxi", "keyword", 0.90)),

    (["hotel", "accommodation", "travelodge", "premier inn", "hilton",
      "marriott", "ibis", "novotel", "airbnb", "booking.com"],
     Classification(3, 6, "Business travel — accommodation", "keyword", 0.85)),

    (["mileage", "mileage claim", "car allowance", "travel expense",
      "subsistence"],
     Classification(3, 6, "Business travel — mileage/expenses", "keyword", 0.80)),

    # ━━━ SCOPE 3 CATEGORY 7: Employee commuting ━━━

    (["cycle scheme", "cyclescheme", "cycle to work", "bike scheme",
      "season ticket loan", "commuter loan"],
     Classification(3, 7, "Employee commuting", "keyword", 0.80)),

    # ━━━ SCOPE 3 CATEGORY 8: Upstream leased assets ━━━

    (["rent", "lease", "landlord", "property rental", "office rent",
      "building lease"],
     Classification(3, 8, "Upstream leased assets", "keyword", 0.70)),

    # ━━━ WATER (categorised under Scope 3 Cat 1) ━━━

    (["water bill", "water rate", "thames water", "severn trent",
      "united utilities", "anglian water", "yorkshire water",
      "welsh water", "scottish water", "wessex water", "southern water",
      "south west water", "northumbrian water"],
     Classification(3, 1, "Purchased services — water supply", "keyword", 0.90)),
]


def classify_transaction(
    supplier: str | None,
    description: str | None,
    category: str | None,
) -> Classification | None:
    """Classify a transaction using keyword rules.

    Returns a Classification if matched, None if no match (needs LLM).
    """
    # Build search text from all available fields
    parts = []
    if supplier:
        parts.append(supplier.lower().strip())
    if description:
        parts.append(description.lower().strip())
    if category:
        parts.append(category.lower().strip())
    search_text = " ".join(parts)

    if not search_text:
        return None

    # Try each rule
    best_match: Classification | None = None
    best_score = 0.0

    for patterns, classification in KEYWORD_RULES:
        for pattern in patterns:
            if pattern in search_text:
                # Prefer longer pattern matches (more specific)
                score = len(pattern) * classification.confidence
                if score > best_score:
                    best_score = score
                    best_match = classification
                break  # Only need one pattern match per rule

    return best_match


def classify_batch(transactions: list[dict]) -> list[Classification | None]:
    """Classify a batch of transactions. Returns list aligned with input.

    Each dict should have keys: supplier, description, category
    """
    return [
        classify_transaction(
            t.get("supplier"),
            t.get("description"),
            t.get("category"),
        )
        for t in transactions
    ]
