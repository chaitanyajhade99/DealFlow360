"""Indian-focused bulk demo data pools + generators, used by seed.py to
populate 70-100+ rows of products, customers, and quotations so every
screen has a realistic, varied dataset instead of a handful of sparse rows.

Kept in its own module so seed.py's hand-authored "named demo accounts"
section (Acme/Beta/Delta/Globex/Initech -- referenced by the README's
credentials and the backend/demo/run_demo.py script) stays easy to read on
its own.
"""
import random

RNG = random.Random(42)  # deterministic -- same seed data every run

# ---- Product catalog templates: (name, price_inr, cost_inr) ----

HARDWARE_TEMPLATES = [
    ("Business Laptop 14", 55000, 40000), ("Business Laptop 15", 62000, 45000),
    ("Gaming Laptop 16", 95000, 70000), ("Ultrabook 13", 78000, 58000),
    ("All-in-One Desktop", 48000, 34000), ("Mini Tower Desktop", 32000, 22000),
    ("Workstation Desktop", 110000, 82000),
    ("24-Inch Monitor", 9500, 6500), ("27-Inch Monitor", 14500, 10000),
    ("32-Inch 4K Monitor", 32000, 23000),
    ("Wireless Mouse", 799, 400), ("Mechanical Keyboard", 2499, 1500),
    ("Docking Station", 6500, 4200), ("24-Port Network Switch", 28000, 19000),
    ("8-Port Network Switch", 6200, 4000), ("48-Port Network Switch", 52000, 37000),
    ("WiFi Router AC1200", 3200, 1900), ("WiFi Mesh System (3-Pack)", 12500, 8600),
    ("UPS 1KVA", 5800, 3900), ("UPS 2KVA", 11500, 8200), ("UPS 5KVA", 38000, 27000),
    ("Server Rack 42U", 45000, 32000), ("Server Rack 24U", 24000, 17000),
    ("Biometric Attendance Device", 8200, 5100), ("CCTV Camera (4 Channel Kit)", 15500, 10800),
    ("CCTV Camera (8 Channel Kit)", 28500, 20000), ("Barcode Scanner", 3600, 2200),
    ("Laser Printer A4", 13500, 9500), ("MFP Printer A3", 42000, 30500),
    ("Thermal Label Printer", 8900, 5800),
    ("External HDD 2TB", 5200, 3600), ("External HDD 4TB", 8900, 6200),
    ("SSD 1TB", 6800, 4700), ("SSD 512GB", 3900, 2600),
    ("Projector Full HD", 38000, 27000), ("Video Conferencing Kit", 62000, 45000),
    ("Webcam HD 1080p", 2200, 1300), ("Headset with Mic", 1500, 850),
    ("Laptop Bag", 1200, 650), ("Laptop Stand", 900, 450),
    ("USB Hub 4-Port", 650, 320), ("Ethernet Cable 10m", 450, 200),
    ("Power Strip (6 Socket)", 850, 400), ("Laptop Cooling Pad", 1100, 600),
    ("Server (Tower, Entry Level)", 145000, 105000), ("Server (Rack, Enterprise)", 320000, 235000),
    ("NAS Storage 8TB", 42000, 30000), ("Interactive Smart Board 65-Inch", 165000, 120000),
]

SERVICES_TEMPLATES = [
    ("Onsite Installation Service", 8500, 5500), ("Network Setup & Configuration", 12500, 8000),
    ("Annual Maintenance Contract (AMC)", 18000, 11000),
    ("Data Migration Service", 22000, 14500), ("ERP Implementation - Tally", 55000, 38000),
    ("ERP Implementation - SAP B1", 185000, 130000), ("ERP Implementation - Zoho Books", 65000, 44000),
    ("Extended Warranty (1 Year)", 4500, 1800), ("Extended Warranty (2 Year)", 8200, 3400),
    ("IT Staffing - Onsite Engineer (Monthly)", 45000, 32000),
    ("Server Rack Installation", 9800, 6200), ("CCTV Installation Service", 6500, 4000),
    ("Firewall Configuration Service", 15500, 10500), ("Cloud Migration Assessment", 28000, 19000),
    ("Employee Training Workshop", 12000, 7000), ("Penetration Testing Audit", 65000, 45000),
    ("GST-Compliant Billing Setup", 9800, 6000), ("Data Center Relocation", 95000, 68000),
    ("Disaster Recovery Planning", 42000, 29000), ("On-Demand IT Support (10 Hours)", 15000, 9500),
]

SUBSCRIPTION_TEMPLATES = [
    ("Care Plan 2yr", 1699, 350, "Monthly"), ("Premium Support Plan", 2999, 750, "Monthly"),
    ("Basic Support Plan", 999, 250, "Monthly"), ("Cloud Backup - 500GB", 799, 150, "Monthly"),
    ("Cloud Backup - 2TB", 1899, 400, "Monthly"), ("Antivirus Enterprise (Per Seat)", 349, 90, "Yearly"),
    ("Microsoft 365 Business (Per Seat)", 1150, 700, "Monthly"), ("Zoho One (Per Seat)", 890, 500, "Monthly"),
    ("Tally Prime Annual License", 21600, 15000, "Yearly"), ("AWS Managed Support", 24999, 18000, "Monthly"),
    ("SLA Gold Support Plan", 6999, 3200, "Monthly"), ("SLA Platinum Support Plan", 12999, 6500, "Monthly"),
    ("Website Hosting - Business", 1499, 600, "Monthly"), ("Zoom Enterprise Plan", 2200, 1300, "Monthly"),
    ("VOIP Business Calling Plan", 1799, 900, "Monthly"), ("Domain + SSL Bundle (Yearly)", 2400, 900, "Yearly"),
]

# ---- Indian customer organizations ----

COMPANY_PREFIXES = [
    "Shree", "Bharat", "National", "Sri", "Om", "Royal", "Metro", "United", "Sunrise", "Prime",
    "Apex", "Vishwa", "Ganga", "Himalaya", "Deccan", "Konkan", "Nilgiri", "Saffron", "Lotus",
    "Trident", "Krishna", "Vindhya", "Malabar", "Coastal", "Northstar", "Greenfield", "Silverline",
    "Goldline", "Blueberry", "Everest",
]
COMPANY_NOUNS = [
    "Textiles", "Industries", "Enterprises", "Solutions", "Technologies", "Traders", "Exports",
    "Logistics", "Pharma", "Agro", "Motors", "Electricals", "Constructions", "Realty", "Foods",
    "Hospitality", "Retail", "Fintech", "Systems", "Infra", "Polymers", "Chemicals", "Apparel",
    "Steel", "Auto Components", "Consultants", "Media", "Analytics", "Packaging", "Distributors",
]
COMPANY_SUFFIXES = ["Pvt Ltd", "Limited", "LLP", "& Co."]

INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad",
    "Jaipur", "Lucknow", "Surat", "Nagpur", "Indore", "Coimbatore", "Kochi", "Chandigarh",
    "Bhopal", "Visakhapatnam", "Vadodara", "Nashik",
]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Ishaan", "Kabir", "Rohan", "Karan",
    "Aryan", "Dhruv", "Nikhil", "Rahul", "Sanjay", "Ramesh", "Suresh", "Anil", "Ravi", "Deepak",
    "Amit", "Manoj", "Vikram", "Rajesh", "Sandeep", "Priya", "Ananya", "Diya", "Isha", "Kavya",
    "Neha", "Pooja", "Meera", "Sneha", "Divya", "Anjali", "Riya", "Shreya", "Kriti", "Nisha",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Reddy", "Nair", "Iyer", "Menon", "Rao", "Patel", "Shah", "Mehta",
    "Joshi", "Kulkarni", "Deshmukh", "Chatterjee", "Banerjee", "Mukherjee", "Das", "Singh", "Kumar",
    "Yadav", "Pillai", "Naidu", "Chawla", "Malhotra",
]


def _slug(name: str) -> str:
    return "".join(c for c in name.upper().replace(" ", "-") if c.isalnum() or c == "-")


def build_products():
    """Returns a list of product dicts covering ~80 SKUs across Hardware,
    Services, and Subscription -- enough variety for upsell rules, warehouse
    stock, and a realistic quotation builder catalog.
    """
    products = []
    for name, price, cost in HARDWARE_TEMPLATES:
        products.append({
            "code": f"HW-{_slug(name)}", "name": name, "category": "Hardware",
            "price": float(price), "cost": float(cost), "unit": "each",
        })
    for name, price, cost in SERVICES_TEMPLATES:
        products.append({
            "code": f"SVC-{_slug(name)}", "name": name, "category": "Services",
            "price": float(price), "cost": float(cost), "unit": "engagement",
        })
    for name, price, cost, cycle in SUBSCRIPTION_TEMPLATES:
        products.append({
            "code": f"SUB-{_slug(name)}", "name": name, "category": "Subscription",
            "price": float(price), "cost": float(cost), "unit": "license",
            "is_subscription": True, "recurring_cycle": cycle,
        })

    # Mark ~1 in 5 as promoted, with a rotating promo tag.
    promo_tags = ["Festive Offer", "Bundle Deal", "High Margin", "Q4 Push", "New Launch"]
    for i, p in enumerate(products):
        if i % 5 == 0:
            p["is_promoted"] = True
            p["promo_tag"] = promo_tags[i % len(promo_tags)]
        else:
            p["is_promoted"] = False
            p["promo_tag"] = None
        p["quantity_on_hand"] = RNG.randint(5, 250) if p["category"] != "Subscription" else None
    return products


def build_companies(count: int, exclude_names: set[str]):
    """Returns `count` distinct (name, city, sector) tuples, never colliding
    with exclude_names (the hand-authored demo accounts).
    """
    seen = set(exclude_names)
    out = []
    attempts = 0
    while len(out) < count and attempts < count * 20:
        attempts += 1
        prefix = RNG.choice(COMPANY_PREFIXES)
        noun = RNG.choice(COMPANY_NOUNS)
        suffix = RNG.choice(COMPANY_SUFFIXES)
        name = f"{prefix} {noun} {suffix}"
        if name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "city": RNG.choice(INDIAN_CITIES), "sector": noun})
    return out


def random_person_name() -> str:
    return f"{RNG.choice(FIRST_NAMES)} {RNG.choice(LAST_NAMES)}"


def random_email(person_name: str, company_name: str, index: int) -> str:
    local = person_name.lower().replace(" ", ".")
    domain = "".join(c for c in company_name.lower() if c.isalnum())[:18] or "company"
    return f"{local}{index}@{domain}.example"
