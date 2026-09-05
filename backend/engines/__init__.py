"""STUB ENGINES MODULE — placeholder only.

Person 2 owns backend/engines/ and will replace this file with the real
implementations. Everything below is hardcoded sample data matching the
return shapes from API_CONTRACT.md so Person 1's endpoints can be built and
tested standalone. Swap this file for Person 2's real module — no changes
needed on the API side beyond this import.
"""


def score_risk(
    lines: list[dict],
    customer_tier: str | None = None,
    rep_avg_discount_pct: float | None = None,
    is_quarter_end: bool = False,
    seniority: int | None = None,
) -> dict:
    return {
        "blended_risk": "MEDIUM",
        "flagged_lines": [
            {"product_id": "STUB-PRODUCT", "given_pct": 18, "limit_pct": 10, "over_by": 8}
        ],
        "reason": "Setup Service is 8 points over its category limit (stub reasoning — replace with real engine).",
    }


def split_warehouse(product_id: str, qty: int, warehouses: list[dict]) -> list[dict]:
    return [{"warehouse_id": "STUB-WH", "qty": qty, "cost": 0.0, "is_backorder": False}]


def detect_anomalies(rep_discount_history: list[float], current_discount: float) -> dict:
    return {"is_anomaly": False, "z_score": 0.0}


def recommend_upsell(cart_items: list[str], co_occurrence_data: dict) -> list[dict]:
    return [{"product_id": "STUB-UPSELL", "margin_delta": 0.0}]
