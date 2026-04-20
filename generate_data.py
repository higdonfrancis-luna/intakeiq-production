#!/usr/bin/env python3
"""
Intake IQ - Synthetic Data Generator
Generates 50 fake law firms + ~1,500 calls over 30 days
"""
import json
import random
import hashlib
from datetime import datetime, timedelta

random.seed(42)  # reproducible

# ============================================================================
# FIRM NAMES - realistic, varied, no real firms
# ============================================================================
LAST_NAMES = [
    "Thompson", "Reyes", "Harrison", "Chen", "Whitfield", "Morrison",
    "Bennett", "Caldwell", "Sterling", "Ashford", "Kensington", "Blackwood",
    "Montgomery", "Westbrook", "Hartwell", "Pemberton", "Holloway", "Fairfax",
    "Ramirez", "Okonkwo", "Kowalski", "Nakamura", "Delgado", "Ferraro",
    "Abernathy", "Lockwood", "Donnelly", "Hargrove", "Sinclair", "Ridgeway",
    "Vaughn", "Whitmore", "Calloway", "Pierce", "Langston", "Devereaux",
    "Ashworth", "Clayton", "Merrick", "Stanton", "Grayson", "Holbrook",
    "Rutherford", "Beaumont", "Hollingsworth", "Winslow", "Fairchild",
    "Redding", "Cavendish", "Thorne",
]
FIRM_SUFFIXES = [
    "& Associates", "Law Group", "Legal Partners", "LLP",
    "Law Firm", "& Partners", "Legal", "Law Offices",
]
PRACTICE_NAMES = [
    "Family Law", "Injury Law", "Criminal Defense",
    "Legal Services", "Defense Group",
]

# ============================================================================
# US CITIES - 20 cities distributed geographically for a good map
# ============================================================================
CITIES = [
    # Major metros
    {"city": "New York", "state": "NY", "lat": 40.7128, "lng": -74.0060},
    {"city": "Los Angeles", "state": "CA", "lat": 34.0522, "lng": -118.2437},
    {"city": "Chicago", "state": "IL", "lat": 41.8781, "lng": -87.6298},
    {"city": "Houston", "state": "TX", "lat": 29.7604, "lng": -95.3698},
    {"city": "Phoenix", "state": "AZ", "lat": 33.4484, "lng": -112.0740},
    {"city": "Philadelphia", "state": "PA", "lat": 39.9526, "lng": -75.1652},
    {"city": "San Antonio", "state": "TX", "lat": 29.4241, "lng": -98.4936},
    {"city": "San Diego", "state": "CA", "lat": 32.7157, "lng": -117.1611},
    {"city": "Dallas", "state": "TX", "lat": 32.7767, "lng": -96.7970},
    {"city": "Miami", "state": "FL", "lat": 25.7617, "lng": -80.1918},
    # Mid-size
    {"city": "Atlanta", "state": "GA", "lat": 33.7490, "lng": -84.3880},
    {"city": "Boston", "state": "MA", "lat": 42.3601, "lng": -71.0589},
    {"city": "Seattle", "state": "WA", "lat": 47.6062, "lng": -122.3321},
    {"city": "Denver", "state": "CO", "lat": 39.7392, "lng": -104.9903},
    {"city": "Nashville", "state": "TN", "lat": 36.1627, "lng": -86.7816},
    {"city": "Portland", "state": "OR", "lat": 45.5152, "lng": -122.6784},
    {"city": "Minneapolis", "state": "MN", "lat": 44.9778, "lng": -93.2650},
    {"city": "Charlotte", "state": "NC", "lat": 35.2271, "lng": -80.8431},
    {"city": "Las Vegas", "state": "NV", "lat": 36.1699, "lng": -115.1398},
    {"city": "Kansas City", "state": "MO", "lat": 39.0997, "lng": -94.5786},
]

# ============================================================================
# LEAD TYPES with realistic distribution weights
# ============================================================================
LEAD_TYPES = [
    ("Personal Injury", 25),
    ("Family Law", 18),
    ("Criminal Defense", 14),
    ("Estate Planning", 10),
    ("DUI", 9),
    ("Workers Comp", 7),
    ("Immigration", 6),
    ("Employment", 5),
    ("Business Litigation", 3),
    ("Bankruptcy", 3),
]

OUTCOMES = [
    ("Booked Consultation", 35),
    ("Requested Info", 22),
    ("Not Qualified", 18),
    ("Voicemail", 12),
    ("Hung Up", 8),
    ("Wrong Number", 5),
]

# ============================================================================
# AI SUMMARY TEMPLATES per lead type
# ============================================================================
SUMMARIES = {
    "Personal Injury": [
        "Caller injured in rear-end collision on highway, seeking representation",
        "Slip and fall at grocery store, broken wrist, wants consultation",
        "Motorcycle accident, caller has medical bills mounting",
        "Dog bite incident at neighbor's property, needs legal guidance",
        "Hit by drunk driver last weekend, significant injuries",
        "Caller's spouse injured in workplace accident, not covered by WC",
        "T-bone collision at intersection, other driver ran red light",
        "Rideshare accident, unclear whose insurance covers damages",
    ],
    "Family Law": [
        "Caller filing for divorce, has two minor children, needs custody advice",
        "Contested custody modification, ex-spouse not following agreement",
        "Prenuptial agreement needed, wedding in 3 months",
        "Child support modification due to job loss",
        "Domestic violence situation, needs emergency protective order",
        "Adoption of stepchild, biological father unreachable",
        "Grandparent visitation rights consultation",
        "High-asset divorce, business valuation needed",
    ],
    "Criminal Defense": [
        "Caller arrested for assault, arraignment Monday",
        "Drug possession charge, first offense, needs defense",
        "Shoplifting charge, caller says misunderstanding",
        "Domestic violence charge, needs urgent representation",
        "Theft charge, caller has prior record",
        "White collar investigation, federal subpoena received",
        "Disorderly conduct, caller claims self-defense",
    ],
    "Estate Planning": [
        "Caller needs will updated after spouse's passing",
        "Setting up trust for special needs child",
        "Estate dispute between siblings over parent's house",
        "Probate filing assistance, father passed without will",
        "Living will and healthcare directive consultation",
        "Blended family estate planning, multiple beneficiaries",
    ],
    "DUI": [
        "First DUI arrest last night, court date next week",
        "Second offense DUI, caller facing license suspension",
        "Breathalyzer refusal case, needs immediate help",
        "Out-of-state DUI, caller is a commercial driver",
        "DUI with accident, no injuries but property damage",
    ],
    "Workers Comp": [
        "Back injury at construction site, employer denying claim",
        "Repetitive strain injury, claim recently denied",
        "Caller hurt on job 6 months ago, still not working",
        "Workers comp retaliation, fired after filing claim",
        "Occupational disease claim, chemical exposure at factory",
    ],
    "Immigration": [
        "Green card application stuck, need help with USCIS",
        "Deportation proceedings, court date in two weeks",
        "H1B visa renewal, employer changing status",
        "Family-based immigration, spouse overseas",
        "Asylum case consultation, fleeing persecution",
    ],
    "Employment": [
        "Wrongful termination after reporting harassment",
        "Wage theft case, unpaid overtime for 2 years",
        "Non-compete enforcement, new job offer at risk",
        "Discrimination claim, age-related comments at work",
        "Retaliation for whistleblowing, need EEOC guidance",
    ],
    "Business Litigation": [
        "Partnership dispute, buyout negotiation failed",
        "Contract breach, vendor not delivering services",
        "Trademark infringement from competitor",
        "Commercial lease dispute, landlord threatening eviction",
    ],
    "Bankruptcy": [
        "Chapter 7 consultation, medical debt overwhelming",
        "Chapter 13 restructuring, behind on mortgage",
        "Business bankruptcy, LLC failing after downturn",
        "Creditor harassment, need debt relief options",
    ],
}

# ============================================================================
# GENERATE FIRMS
# ============================================================================
def generate_firms(n=50):
    firms = []
    used_names = set()

    # Size distribution: 15 small, 25 medium, 10 large
    size_plan = ["small"]*15 + ["medium"]*25 + ["large"]*10
    random.shuffle(size_plan)

    for i in range(n):
        # Generate unique firm name
        while True:
            if random.random() < 0.6:
                # Name & Name format
                last1, last2 = random.sample(LAST_NAMES, 2)
                name = f"{last1} & {last2} {random.choice(FIRM_SUFFIXES)}"
            elif random.random() < 0.5:
                # Single last name firm
                name = f"{random.choice(LAST_NAMES)} {random.choice(FIRM_SUFFIXES)}"
            else:
                # Practice-named firm
                last = random.choice(LAST_NAMES)
                pract = random.choice(PRACTICE_NAMES)
                name = f"{last} {pract}"
            if name not in used_names:
                used_names.add(name)
                break

        city_info = random.choice(CITIES)
        # Add small random offset so pins don't perfectly overlap
        lat = city_info["lat"] + random.uniform(-0.05, 0.05)
        lng = city_info["lng"] + random.uniform(-0.05, 0.05)

        firms.append({
            "id": i + 1,
            "name": name,
            "city": city_info["city"],
            "state": city_info["state"],
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "ai_enabled": 1 if random.random() < 0.65 else 0,
            "size_tier": size_plan[i],
        })
    return firms

# ============================================================================
# GENERATE CALLS
# ============================================================================
def weighted_choice(options):
    """options: list of (value, weight) tuples"""
    total = sum(w for _, w in options)
    r = random.uniform(0, total)
    cumulative = 0
    for val, w in options:
        cumulative += w
        if r <= cumulative:
            return val
    return options[-1][0]

def mask_phone():
    area = random.randint(200, 999)
    return f"({area}) ***-{random.randint(1000,9999)}"

def generate_calls(firms, days=30):
    calls = []
    call_id = 1
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    # Calls per firm by size tier
    size_call_counts = {
        "small": (5, 15),     # 5-15 calls in 30d
        "medium": (20, 45),   # 20-45
        "large": (60, 110),   # 60-110
    }

    for firm in firms:
        low, high = size_call_counts[firm["size_tier"]]
        n_calls = random.randint(low, high)

        for _ in range(n_calls):
            # Random timestamp in the 30-day window, weighted toward recent
            day_offset = random.choices(
                range(days),
                weights=[1 + (i * 0.05) for i in range(days)],  # slight recency bias
            )[0]
            # Business hours bias: 60% 9am-6pm, 40% other
            if random.random() < 0.6:
                hour = random.randint(9, 18)
            else:
                hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)

            ts = start + timedelta(days=day_offset, hours=hour, minutes=minute, seconds=second)
            if ts > now:
                ts = now - timedelta(minutes=random.randint(5, 60))

            lead_type = weighted_choice(LEAD_TYPES)
            outcome = weighted_choice(OUTCOMES)

            # Duration depends on outcome
            if outcome == "Voicemail":
                duration = random.randint(15, 45)
            elif outcome == "Hung Up":
                duration = random.randint(5, 30)
            elif outcome == "Wrong Number":
                duration = random.randint(8, 25)
            elif outcome == "Booked Consultation":
                duration = random.randint(240, 900)
            elif outcome == "Not Qualified":
                duration = random.randint(60, 240)
            else:  # Requested Info
                duration = random.randint(120, 480)

            # AI summary only if firm has AI enabled and call was long enough
            if firm["ai_enabled"] and duration > 30 and outcome not in ("Voicemail", "Hung Up", "Wrong Number"):
                summary = random.choice(SUMMARIES.get(lead_type, ["Call recorded, details captured"]))
            else:
                summary = None

            calls.append({
                "id": call_id,
                "firm_id": firm["id"],
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "lead_type": lead_type,
                "duration_seconds": duration,
                "ai_summary": summary,
                "outcome": outcome,
                "caller_phone_masked": mask_phone(),
            })
            call_id += 1

    # Sort by timestamp desc (newest first in DB)
    calls.sort(key=lambda c: c["timestamp"], reverse=True)
    return calls

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    firms = generate_firms(50)
    calls = generate_calls(firms, days=30)

    print(f"Generated {len(firms)} firms")
    print(f"Generated {len(calls)} calls over 30 days")
    print()
    print("=== SAMPLE FIRMS (first 10) ===")
    for f in firms[:10]:
        ai = "AI✓" if f["ai_enabled"] else "   "
        print(f"  [{f['id']:>2}] {f['name']:<45} {f['city']:<15} {f['state']}  {ai}  tier={f['size_tier']}")

    print()
    print("=== SIZE DISTRIBUTION ===")
    from collections import Counter
    tiers = Counter(f["size_tier"] for f in firms)
    for t in ["small","medium","large"]:
        print(f"  {t}: {tiers[t]}")
    ai_on = sum(1 for f in firms if f["ai_enabled"])
    print(f"  AI enabled: {ai_on}/50 ({ai_on*2}%)")

    print()
    print("=== SAMPLE CALLS (first 5) ===")
    for c in calls[:5]:
        firm = next(f for f in firms if f["id"] == c["firm_id"])
        print(f"  {c['timestamp']} | {firm['name'][:30]:<30} | {c['lead_type']:<20} | {c['outcome']:<22} | {c['duration_seconds']}s")
        if c["ai_summary"]:
            print(f"      AI: {c['ai_summary']}")

    print()
    print("=== LEAD TYPE DISTRIBUTION ===")
    lt_counts = Counter(c["lead_type"] for c in calls)
    total = len(calls)
    for lt, w in LEAD_TYPES:
        cnt = lt_counts.get(lt, 0)
        pct = cnt / total * 100
        print(f"  {lt:<20} {cnt:>4}  ({pct:.1f}%)")

    print()
    print("=== OUTCOME DISTRIBUTION ===")
    out_counts = Counter(c["outcome"] for c in calls)
    for o, w in OUTCOMES:
        cnt = out_counts.get(o, 0)
        pct = cnt / total * 100
        print(f"  {o:<22} {cnt:>4}  ({pct:.1f}%)")

    # Save for seeding
    with open("/home/claude/intakeiq/firms.json", "w") as f:
        json.dump(firms, f, indent=2)
    with open("/home/claude/intakeiq/calls.json", "w") as f:
        json.dump(calls, f)
    print()
    print(f"✅ Saved firms.json and calls.json")
