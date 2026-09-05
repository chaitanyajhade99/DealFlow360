"""Run all four engines against realistic seed data and print what each
wireframe screen would render.

    python backend/engines/demo.py          # from the repo root
    python demo.py                          # from backend/engines/

No arguments, no DB, no dependencies. Edit the SEED DATA block below to poke
the engines with your own numbers -- every function is pure, so whatever you
put in is exactly what the API will pass through.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from anomaly_engine import detect_anomalies  # noqa: E402
from apriori import build_co_occurrence, find_frequent_itemsets, generate_rules  # noqa: E402
from fulfillment_engine import split_warehouse  # noqa: E402
from risk_engine import FLAGGED_LINE_COLUMNS, score_risk  # noqa: E402
from risk_model import get_default_model  # noqa: E402
from synthetic_data import generate_transactions, product_margins  # noqa: E402
from upsell_engine import recommend_upsell  # noqa: E402

# --------------------------------------------------------------------------
# SEED DATA -- edit freely
# --------------------------------------------------------------------------

# The PDF section 10 worked example: Gold customer, Laptop within its ceiling,
# Setup Service 8 points over its stricter one.
PDF_EXAMPLE_LINES = [
    {"id": 1, "product_name": "Laptop", "product_id": "LAPTOP-01",
     "category": "Hardware", "qty": 10, "unit_price": 1200.0,
     "discount_pct": 12.0, "category_limit_pct": 15.0},
    {"id": 2, "product_name": "Setup Service", "product_id": "SETUP-01",
     "category": "Service", "qty": 1, "unit_price": 2000.0,
     "discount_pct": 18.0, "category_limit_pct": 10.0},
]

# The PDF's "why blended?" case: nothing alarming alone, plenty together.
DEATH_BY_PAPERCUTS_LINES = [
    {"id": 1, "product_name": "Server Rack", "category": "Hardware",
     "qty": 4, "unit_price": 2500.0, "discount_pct": 12.0, "category_limit_pct": 10.0},
    {"id": 2, "product_name": "Install Labour", "category": "Service",
     "qty": 20, "unit_price": 150.0, "discount_pct": 13.0, "category_limit_pct": 10.0},
    {"id": 3, "product_name": "Support Plan", "category": "Service",
     "qty": 1, "unit_price": 4000.0, "discount_pct": 12.0, "category_limit_pct": 10.0},
]

CLEAN_LINES = [
    {"id": 1, "product_name": "Laptop", "category": "Hardware", "qty": 5,
     "unit_price": 1200.0, "discount_pct": 5.0, "category_limit_pct": 15.0},
]

# Quote Q-00017 straight out of the generated history. Every line is INSIDE
# its ceiling, so the rule engine sees nothing at all -- but it is a 187k deal
# run by a junior rep with most of the value in thin-margin Subscription, and
# the generator's latent process labelled it genuinely HIGH risk. This is the
# case the model exists to catch.
MODEL_ESCALATION_LINES = [
    {"id": 1, "product_name": "Rack Server", "product_id": "SERVER-01",
     "category": "Hardware", "qty": 18, "unit_price": 6500.0,
     "discount_pct": 1.55, "category_limit_pct": 10.0},
    {"id": 2, "product_name": "Premium Support", "product_id": "SUPPORT-01",
     "category": "Subscription", "qty": 17, "unit_price": 4000.0,
     "discount_pct": 9.18, "category_limit_pct": 10.0},
    {"id": 3, "product_name": "Docking Station", "product_id": "DOCK-01",
     "category": "Accessories", "qty": 9, "unit_price": 240.0,
     "discount_pct": 3.22, "category_limit_pct": 10.0},
]

WAREHOUSES = [
    {"id": "WH-MAIN", "name": "Main Warehouse",
     "stock": [{"product_id": "LAPTOP-01", "qty": 50}],
     "shipping_cost_per_unit": 2.0, "shipment_fixed_cost": 25.0},
    {"id": "WH-EAST", "name": "East Depot",
     "stock": [{"product_id": "LAPTOP-01", "qty": 30}],
     "shipping_cost_per_unit": 3.0, "shipment_fixed_cost": 20.0},
]

REP_HISTORY = [5.0, 6.0, 5.0, 7.0, 6.0, 5.0]  # a rep who lives at 5-7 percent

CO_OCCURRENCE = {
    "LAPTOP-01": [
        {"product_id": "DOCK-01", "product_name": "Docking Station",
         "co_purchase_count": 40, "margin": 50.0},
        {"product_id": "MOUSE-01", "product_name": "Wireless Mouse",
         "co_purchase_count": 90, "margin": 5.0},
        {"product_id": "WARRANTY-01", "product_name": "3yr Warranty",
         "co_purchase_count": 20, "margin": 85.0,
         "is_promoted": True, "promo_tag": "Q1 Bundle"},
    ],
    "MONITOR-01": [
        {"product_id": "DOCK-01", "product_name": "Docking Station",
         "co_purchase_count": 10, "margin": 50.0},
    ],
}


# --------------------------------------------------------------------------
# Tiny console table renderer (no dependencies)
# --------------------------------------------------------------------------

def heading(text: str) -> None:
    print(f"\n{'=' * 74}\n{text}\n{'=' * 74}")


def table(headers: list[str], rows: list[list]) -> None:
    if not rows:
        print("  (no rows)")
        return
    cells = [[str(value) for value in row] for row in rows]
    widths = [
        max(len(headers[i]), max(len(row[i]) for row in cells))
        for i in range(len(headers))
    ]
    line = "  " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(line)
    print("  " + "-+-".join("-" * w for w in widths))
    for row in cells:
        print("  " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))))


def show_quote(title: str, lines: list[dict], **context) -> None:
    result = score_risk(lines, **context)
    print(f"\n{title}")
    print(
        f"  FINAL={result['blended_risk']}"
        f"   rules={result['rule_risk']}"
        f"   model={result['model_risk'] or 'n/a'}"
        + (f" (conf {result['model_confidence']:.2f})"
           if result["model_confidence"] is not None else "")
        + ("   <- ESCALATED BY MODEL" if result["escalated_by_model"] else "")
    )
    print(
        f"  blended={result['blended_score_pct']} pts"
        f"  worst_line={result['worst_line_over_pct']} pts"
        f"  value={result['total_line_value']:,.2f}"
    )
    chain = " -> ".join(result["approval_chain"]) or "no approval needed"
    print(f"  approval chain: {chain}")
    print(f"  audit reason: {result['reason']}")
    keys = [key for key, _ in FLAGGED_LINE_COLUMNS]
    headers = [label for _, label in FLAGGED_LINE_COLUMNS]
    table(headers, [[row[key] for key in keys] for row in result["flagged_lines"]])


# --------------------------------------------------------------------------

def main() -> None:
    heading("MODEL STATUS")

    model = get_default_model()
    if model is None:
        print("\n  No trained artifact found -- engines run rules-only.")
        print("  Run `python backend/engines/train.py` to train both models.")
    else:
        meta = model.metadata
        print(f"\n  XGBoost risk model loaded from data/risk_model.json")
        print(f"    trained on {meta.get('n_train', '?')} quotes, "
              f"held-out {meta.get('n_test', '?')}")
        print(f"    accuracy {meta.get('accuracy', '?')}  "
              f"macro F1 {meta.get('macro_f1', '?')}")
        print("\n  Top features by gain:")
        table(
            ["Feature", "Gain"],
            [[name, f"{gain:.2f}"] for name, gain in model.feature_importance(6)],
        )
        print(
            "    ^ the top two are the rule engine's own signals -- but the model\n"
            "      also leans on deal size, seniority and quarter-end, which the\n"
            "      line-level rules cannot see. That is the margin it adds."
        )

    heading("SCREEN 6 - Why This Quote Was Flagged  (score_risk)")

    show_quote(
        "[1] PDF section 10 worked example -- Laptop 12/15 ok, Setup Service 18/10 over",
        PDF_EXAMPLE_LINES,
    )
    print(
        "      ^ note the blend is only 1.14 pts -- the big clean Laptop line dilutes it.\n"
        "        It is the single-line rule (8 pts over) that forces HIGH, exactly as the PDF says."
    )

    show_quote(
        "[2] PDF 'why blended?' -- 2 over, 3 over, 2 over: nothing alarming alone",
        DEATH_BY_PAPERCUTS_LINES,
    )
    print("      ^ no single line is severe, but the pattern still earns a review.")

    show_quote(
        "[3] A clean quote -- everything inside its ceiling",
        CLEAN_LINES, customer_tier="Gold", seniority=2,
    )

    show_quote(
        "[4] Q-00017 from history: every line INSIDE its ceiling, junior rep, 187k deal",
        MODEL_ESCALATION_LINES, customer_tier="Silver", seniority=0,
    )
    print(
        "      ^ the flagged-lines table is empty -- the rule engine has nothing to\n"
        "        say, because no line broke its ceiling. The model escalates anyway on\n"
        "        deal size, a junior rep, and most of the value sitting in thin-margin\n"
        "        Subscription at 9.18% against a 10% ceiling. The generator's own latent\n"
        "        label for this quote was HIGH, so the escalation is a genuine catch.\n"
        "        Across 1500 held-out quotes the model escalates ~12%, 77 of them with\n"
        "        no flagged lines at all."
    )

    heading("SCREEN 8 - Fulfillment Split  (split_warehouse)")

    for qty in (20, 70, 100):
        rows = split_warehouse("LAPTOP-01", qty, WAREHOUSES)
        real = [r for r in rows if not r["is_backorder"]]
        backorder = next((r for r in rows if r["is_backorder"]), None)
        print(f"\n  Order: {qty} x LAPTOP-01   (80 on hand across 2 warehouses)")
        table(
            ["Warehouse", "Qty Fulfilled", "Est. Shipments", "Cost"],
            [[r["warehouse"], r["qty"], r["est_shipments"], f"{r['cost']:.2f}"]
             for r in rows],
        )
        print(
            f"    shipments={len(real)}"
            f"  total cost={sum(r['cost'] for r in real):.2f}"
            + (f"  BACKORDER {backorder['qty']} units -> B6 consolidate prompt"
               if backorder else "  fully fulfilled")
        )

    heading("SCREEN 14 - Discount Anomalies  (detect_anomalies)")

    print(f"\n  Rep's discount history: {REP_HISTORY}")
    table(
        ["Quote discount", "Rep avg", "Std dev", "Threshold", "Z-score", "ANOMALY?"],
        [
            [f"{r['current_discount']}%", f"{r['mean']}%", r["stddev"],
             f"{r['threshold']}%", r["z_score"], "YES" if r["is_anomaly"] else "no"]
            for r in (detect_anomalies(REP_HISTORY, d) for d in (6.0, 7.0, 12.0, 25.0))
        ],
    )
    print(
        "    ^ 7.0% is above this rep's average yet still normal for them;\n"
        "      12% and 25% clear the 2-sigma threshold and raise the card."
    )

    edge = detect_anomalies([], 40.0)
    print(
        f"\n  New rep, no history: is_anomaly={edge['is_anomaly']}"
        f" sample_size={edge['sample_size']}"
        "  <- render 'not enough history yet', not 'clean'"
    )

    heading("APRIORI - mining association rules from 3000 baskets")

    transactions = generate_transactions(n_baskets=3000, seed=42)
    frequent = find_frequent_itemsets(transactions, min_support=0.02, max_len=3)
    by_size = {}
    for itemset in frequent:
        by_size[len(itemset)] = by_size.get(len(itemset), 0) + 1
    print(f"\n  {len(transactions)} baskets -> frequent itemsets by size: "
          f"{dict(sorted(by_size.items()))}")

    rules = generate_rules(frequent, min_confidence=0.25, min_lift=1.05)
    print(f"  {len(rules)} rules above confidence 0.25 / lift 1.05\n")
    table(
        ["Antecedent", "Consequent", "Support", "Confidence", "Lift"],
        [[", ".join(r["antecedent"]), ", ".join(r["consequent"]),
          f"{r['support']:.3f}", f"{r['confidence']:.3f}", f"{r['lift']:.2f}"]
         for r in rules[:8]],
    )
    print(
        "    ^ the generator planted SERVER-01 -> RACK/INSTALL/SUPPORT and\n"
        "      LAPTOP-01 -> MOUSE/DOCK/WARRANTY. Apriori rediscovered them from\n"
        "      raw baskets, with no knowledge of how they were generated."
    )

    heading("SCREEN 4 - Upsell / Cross-sell Cards  (recommend_upsell)")

    mined = build_co_occurrence(transactions, product_margins())
    print("\n  Using Apriori-mined rules. Cart: [LAPTOP-01]")
    table(
        ["Product", "Margin", "Confidence", "Lift", "Expected Margin", "Score", "Promo"],
        [[r["product_name"], f"{r['margin_delta']:.2f}", f"{r['confidence']:.3f}",
          f"{r['lift']:.2f}", f"{r['expected_margin']:.2f}", r["score"],
          r["promo_tag"] or "-"]
         for r in recommend_upsell(["LAPTOP-01"], mined, limit=6)],
    )
    print(
        "    ^ ranked by EXPECTED MARGIN (confidence x margin), not raw count:\n"
        "      'X% of laptop baskets also took this, and it earns Y per unit'.\n"
        "      A cheap accessory in 70% of baskets loses to a 50-margin dock in 60%."
    )

    print("\n  Same cart, min_margin=20.0 (PDF A6 healthy-margin threshold)")
    table(
        ["Product", "Margin", "Confidence", "Lift", "Expected Margin", "Score"],
        [[r["product_name"], f"{r['margin_delta']:.2f}", f"{r['confidence']:.3f}",
          f"{r['lift']:.2f}", f"{r['expected_margin']:.2f}", r["score"]]
         for r in recommend_upsell(["LAPTOP-01"], mined, min_margin=20.0, limit=6)],
    )
    print(
        "    ^ the mouse and cable are real associations (lift 3.70 and 1.58) but\n"
        "      they are not worth a rep's breath at 5.00 and 3.00 margin.\n"
        "      Lift filtering already happened at mining time: build_co_occurrence\n"
        "      drops anything below lift 1.05, which is why every row above beats\n"
        "      its own base rate. recommend_upsell(min_lift=...) tightens it further."
    )

    heading("SCREEN 4 (cont.) - hand-authored fallback, no Apriori")

    print("\n  Cart: [LAPTOP-01]")
    table(
        ["Product", "Margin Delta", "Co-purchases", "Score", "Promo Tag"],
        [[r["product_name"], f"+{r['margin_delta']:.2f}", int(r["co_purchase_count"]),
          r["score"], r["promo_tag"] or "-"]
         for r in recommend_upsell(["LAPTOP-01"], CO_OCCURRENCE)],
    )
    print(
        "    ^ Warranty's raw score is 20x85=1700 vs the Dock's 40x50=2000,\n"
        "      but the 1.25x promotion boost lifts it to 2125 and it takes the top card.\n"
        "      The 90-count Wireless Mouse loses on thin margin -- count alone would have won."
    )

    print("\n  Cart: [LAPTOP-01, DOCK-01]  (dock already quoted)")
    table(
        ["Product", "Margin Delta", "Co-purchases", "Score", "Promo Tag"],
        [[r["product_name"], f"+{r['margin_delta']:.2f}", int(r["co_purchase_count"]),
          r["score"], r["promo_tag"] or "-"]
         for r in recommend_upsell(["LAPTOP-01", "DOCK-01"], CO_OCCURRENCE)],
    )
    print("    ^ the dock is gone -- never suggest what is already in the cart.")

    print("\n  Cart: [LAPTOP-01] with min_margin=20.0  (PDF A6 margin threshold)")
    table(
        ["Product", "Margin Delta", "Co-purchases", "Score", "Promo Tag"],
        [[r["product_name"], f"+{r['margin_delta']:.2f}", int(r["co_purchase_count"]),
          r["score"], r["promo_tag"] or "-"]
         for r in recommend_upsell(["LAPTOP-01"], CO_OCCURRENCE, min_margin=20.0)],
    )
    print("    ^ thin-margin mouse filtered out before ranking.")

    print()


if __name__ == "__main__":
    main()
