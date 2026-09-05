"""Synthetic dataset generation for the DealFlow360 algorithm layer.

Produces two datasets, both fully deterministic under a fixed seed:

  1. Quotation history  -> trains the XGBoost risk model (risk_model.py)
  2. Basket transactions -> mined by Apriori for cross-sell (apriori.py)

Nothing here touches a DB. Run it via train.py, or import the generators
directly to experiment with different distributions.

WHY THE LABELS ARE NOT JUST THE RULE
------------------------------------
It would be circular to label each quote with the deterministic rule and then
train a model to re-learn that rule -- the model would add nothing. So the
label comes from a richer latent process that includes signals the line-level
rule cannot see:

  * rep seniority        - a junior rep discounting hard is riskier than a
                           principal rep doing the same
  * customer tier        - the same overage on a Bronze account is worse
  * thin-margin mix      - overage concentrated in Service/Subscription lines
                           costs far more margin than the same overage on
                           Hardware
  * deal size            - a 2-point overage on a 500k order is real money
  * quarter-end pressure - discounts spike and get rubber-stamped
  * label noise          - human approvers are not perfectly consistent

The rule sees only "how far over its ceiling is each line". The model gets
the context, which is exactly why the hybrid in risk_engine.py is worth
having: rules for the floor and the audit reason, model for the patterns.
"""

from __future__ import annotations

import random

# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------

# category -> discount ceiling in percentage points (PDF A3).
# Thin-margin categories get stricter ceilings.
CATEGORY_LIMITS = {
    "Hardware": 15.0,
    "Accessories": 20.0,
    "Subscription": 12.0,
    "Service": 10.0,
}

# Categories whose margin is thin enough that overage there hurts most.
THIN_MARGIN_CATEGORIES = {"Service", "Subscription"}

# Customer tier -> overall discount ceiling (PDF A3 example).
TIER_LIMITS = {"Bronze": 5.0, "Silver": 10.0, "Gold": 15.0}
TIER_ORDINAL = {"Bronze": 0, "Silver": 1, "Gold": 2}

# product_id -> (name, category, unit_price, margin_per_unit, is_promoted, promo_tag)
PRODUCT_CATALOG = {
    "LAPTOP-01":   ("Business Laptop 14\"", "Hardware",     1200.0, 180.0, False, None),
    "LAPTOP-02":   ("Workstation Laptop",   "Hardware",     2100.0, 290.0, False, None),
    "MONITOR-01":  ("27\" 4K Monitor",      "Hardware",      450.0,  70.0, False, None),
    "SERVER-01":   ("Rack Server",          "Hardware",     6500.0, 900.0, False, None),
    "DOCK-01":     ("Docking Station",      "Accessories",   240.0,  50.0, False, None),
    "MOUSE-01":    ("Wireless Mouse",       "Accessories",    45.0,   5.0, False, None),
    "CABLE-01":    ("USB-C Cable 2m",       "Accessories",    25.0,   3.0, False, None),
    "RACK-01":     ("Server Rack 42U",      "Hardware",     1800.0, 210.0, False, None),
    "INSTALL-01":  ("On-site Installation", "Service",      1500.0, 120.0, False, None),
    "SETUP-01":    ("Setup Service",        "Service",      2000.0, 160.0, False, None),
    "TRAINING-01": ("User Training Day",    "Service",       900.0,  95.0, True,  "Enablement Push"),
    "SUPPORT-01":  ("Premium Support",      "Subscription", 4000.0, 520.0, False, None),
    "WARRANTY-01": ("3yr Extended Warranty","Subscription",  600.0,  85.0, True,  "Q1 Bundle"),
    "CLOUD-01":    ("Cloud Backup 1TB",     "Subscription",  300.0,  60.0, True,  "Attach Rate Drive"),
}

# Baskets are generated from these anchors. Each anchor pulls its attachments
# in with the given probability -- this is the ground-truth association
# structure that Apriori has to rediscover from raw baskets.
BASKET_ANCHORS = {
    "LAPTOP-01": [("DOCK-01", 0.62), ("MOUSE-01", 0.71), ("WARRANTY-01", 0.44),
                  ("CABLE-01", 0.33), ("SETUP-01", 0.18)],
    "LAPTOP-02": [("DOCK-01", 0.58), ("MONITOR-01", 0.40), ("WARRANTY-01", 0.47),
                  ("TRAINING-01", 0.21)],
    "MONITOR-01": [("CABLE-01", 0.55), ("DOCK-01", 0.30)],
    "SERVER-01": [("RACK-01", 0.68), ("INSTALL-01", 0.61), ("SUPPORT-01", 0.52),
                  ("CLOUD-01", 0.35)],
    "SETUP-01": [("TRAINING-01", 0.38), ("SUPPORT-01", 0.29)],
}

REP_NAMES = [
    "R. Mehta", "S. Okafor", "L. Nguyen", "D. Alvarez",
    "K. Bianchi", "T. Haruna", "P. Sorensen", "M. Devlin",
]


def _rep_profiles(rng: random.Random) -> list[dict]:
    """Each rep has a personal discounting baseline and a seniority level.

    detect_anomalies() compares a quote against the rep's OWN history, so the
    generator has to give reps genuinely different baselines for that to mean
    anything.
    """
    profiles = []
    for i, name in enumerate(REP_NAMES):
        seniority = rng.choice([0, 0, 1, 1, 2])  # 0 junior, 1 mid, 2 principal
        profiles.append(
            {
                "rep_id": f"REP-{i + 1:02d}",
                "rep_name": name,
                "seniority": seniority,
                # Junior reps lean on discount harder to close.
                "baseline_discount": round(rng.uniform(3.0, 9.0) - seniority * 0.9, 2),
                "discount_volatility": round(rng.uniform(0.8, 2.6), 2),
            }
        )
    return profiles


def generate_quotation_history(n_quotes: int = 4000, seed: int = 42) -> list[dict]:
    """Generate labelled historical quotations for training the risk model.

    Args:
        n_quotes: how many quotes to synthesise.
        seed: RNG seed. Same seed always gives the same dataset.

    Returns:
        List of quote dicts:
        {
          "quotation_id": str, "rep_id": str, "rep_name": str,
          "seniority": int, "customer_tier": str, "is_quarter_end": bool,
          "lines": [ {product_id, product_name, category, qty, unit_price,
                      discount_pct, category_limit_pct}, ... ],
          "risk_label": 0 | 1 | 2,      # 0 LOW, 1 MEDIUM, 2 HIGH
          "latent_risk": float,          # the pre-noise score, for inspection
        }

        Lines carry category_limit_pct = min(category ceiling, tier ceiling),
        which is exactly how the PDF's Gold/Hardware/Service example works.
    """
    rng = random.Random(seed)
    reps = _rep_profiles(rng)
    product_ids = list(PRODUCT_CATALOG)
    quotes = []

    for n in range(n_quotes):
        rep = rng.choice(reps)
        tier = rng.choices(["Bronze", "Silver", "Gold"], weights=[0.3, 0.45, 0.25])[0]
        tier_limit = TIER_LIMITS[tier]
        is_quarter_end = rng.random() < 0.28

        n_lines = rng.choices([1, 2, 3, 4, 5, 6], weights=[15, 25, 24, 18, 11, 7])[0]
        chosen = rng.sample(product_ids, k=min(n_lines, len(product_ids)))

        lines = []
        for product_id in chosen:
            name, category, unit_price, _margin, _promo, _tag = PRODUCT_CATALOG[product_id]
            # The effective ceiling is the stricter of the two (PDF A3).
            limit = min(CATEGORY_LIMITS[category], tier_limit)

            # Discount is drawn around the rep's baseline, pushed up at
            # quarter end and for bigger-ticket items.
            centre = rep["baseline_discount"]
            if is_quarter_end:
                centre += 2.4
            if unit_price > 1500:
                centre += 1.5
            discount = rng.gauss(centre, rep["discount_volatility"] + 1.4)
            # Occasional deliberate deep discount to close a deal.
            if rng.random() < 0.12:
                discount += rng.uniform(3.0, 11.0)
            discount = round(max(0.0, min(discount, 45.0)), 2)

            lines.append(
                {
                    "product_id": product_id,
                    "product_name": name,
                    "category": category,
                    "qty": rng.randint(1, 25),
                    "unit_price": unit_price,
                    "discount_pct": discount,
                    "category_limit_pct": limit,
                }
            )

        latent = _latent_risk(lines, tier, rep, is_quarter_end)
        # Approvers are not perfectly consistent -- add label noise so the
        # model has to generalise instead of memorising a threshold.
        noisy = latent + rng.gauss(0.0, 0.32)
        label = 2 if noisy >= 2.05 else (1 if noisy >= 0.95 else 0)

        quotes.append(
            {
                "quotation_id": f"Q-{n + 1:05d}",
                "rep_id": rep["rep_id"],
                "rep_name": rep["rep_name"],
                "seniority": rep["seniority"],
                "customer_tier": tier,
                "is_quarter_end": is_quarter_end,
                "lines": lines,
                "risk_label": label,
                "latent_risk": round(latent, 4),
            }
        )

    return quotes


def _latent_risk(lines, tier, rep, is_quarter_end) -> float:
    """The hidden process that decides how risky a quote really was.

    Deliberately richer than the line-level rule: it weights overage by how
    thin the category's margin is, scales with deal size, and forgives a
    senior rep on a Gold account. The rule engine cannot see any of that,
    which is what leaves room for the model to add signal.
    """
    total_value = 0.0
    weighted_overage = 0.0
    thin_value = 0.0
    worst = 0.0

    for line in lines:
        value = line["qty"] * line["unit_price"]
        overage = max(line["discount_pct"] - line["category_limit_pct"], 0.0)
        # Overage on a thin-margin line burns roughly twice the margin.
        weight = 2.0 if line["category"] in THIN_MARGIN_CATEGORIES else 1.0
        total_value += value
        weighted_overage += overage * value * weight
        if line["category"] in THIN_MARGIN_CATEGORIES:
            thin_value += value
        worst = max(worst, overage)

    if total_value <= 0:
        return 0.0

    blended = weighted_overage / total_value
    thin_share = thin_value / total_value

    score = 0.0
    score += blended * 0.42            # the core signal
    score += worst * 0.11              # one badly-broken line still matters
    score += thin_share * 0.55         # margin-sensitive mix
    score += (total_value / 120_000.0) # big deals carry more absolute risk
    score += 0.45 if is_quarter_end else 0.0
    score -= rep["seniority"] * 0.30   # senior reps get more latitude
    score -= TIER_ORDINAL[tier] * 0.22 # strategic accounts get more latitude
    return max(score, 0.0)


def generate_transactions(n_baskets: int = 3000, seed: int = 42) -> list[list[str]]:
    """Generate historical order baskets for Apriori to mine.

    Each basket starts from an anchor product and pulls in its attachments
    with the probabilities in BASKET_ANCHORS, plus occasional random noise
    items. Apriori has to recover that structure from the raw baskets alone.

    Args:
        n_baskets: how many historical orders to synthesise.
        seed: RNG seed.

    Returns:
        List of baskets, each a list of unique product_ids.
    """
    rng = random.Random(seed + 1)
    anchors = list(BASKET_ANCHORS)
    all_products = list(PRODUCT_CATALOG)
    baskets = []

    for _ in range(n_baskets):
        anchor = rng.choice(anchors)
        basket = {anchor}
        for attachment, probability in BASKET_ANCHORS[anchor]:
            if rng.random() < probability:
                basket.add(attachment)
        # A second anchor sometimes joins, creating cross-anchor overlap.
        if rng.random() < 0.18:
            second = rng.choice(anchors)
            basket.add(second)
            for attachment, probability in BASKET_ANCHORS[second]:
                if rng.random() < probability * 0.6:
                    basket.add(attachment)
        # Background noise so support/confidence are not artificially clean.
        if rng.random() < 0.22:
            basket.add(rng.choice(all_products))
        baskets.append(sorted(basket))

    return baskets


def product_margins() -> dict[str, dict]:
    """Margin and promotion metadata, keyed by product_id.

    recommend_upsell() needs margin to rank, and Apriori only ever sees
    product ids in baskets, so this is what joins the two together.
    """
    return {
        product_id: {
            "product_name": name,
            "category": category,
            "unit_price": unit_price,
            "margin": margin,
            "is_promoted": is_promoted,
            "promo_tag": promo_tag,
        }
        for product_id, (name, category, unit_price, margin, is_promoted, promo_tag)
        in PRODUCT_CATALOG.items()
    }


def generate_rep_discount_histories(quotes: list[dict]) -> dict[str, list[float]]:
    """Per-rep discount history, for detect_anomalies().

    Each entry is one quote's value-weighted average discount, which is the
    same granularity /deal-health compares a live quote against.
    """
    histories: dict[str, list[float]] = {}
    for quote in quotes:
        total_value = sum(line["qty"] * line["unit_price"] for line in quote["lines"])
        if total_value <= 0:
            continue
        weighted = sum(
            line["discount_pct"] * line["qty"] * line["unit_price"]
            for line in quote["lines"]
        )
        histories.setdefault(quote["rep_id"], []).append(
            round(weighted / total_value, 2)
        )
    return histories
