"""Upsell / cross-sell ranking (PDF A6 / B5, wireframe screen 4).

Consumes the co_occurrence_data dict from API_CONTRACT.md. That dict can come
from either source, and the ranking adapts:

  * Apriori-mined rules (apriori.build_co_occurrence) -- carries confidence
    and lift, so ranking uses EXPECTED MARGIN: confidence x margin.
  * A hand-authored dict -- no confidence, so ranking falls back to the
    original co_purchase_count x margin.

Each row reports which basis was used in "ranking_basis", so screen 4 can show
"62% of laptop buyers also take this" when the data supports it.

Pure function layer. No DB access, no imports from models/ or api/.
"""

from __future__ import annotations

# Promoted products rank higher (PDF A6). Applied as a score multiplier rather
# than a hard pin, so a promoted-but-weak suggestion still loses to a strong one.
PROMOTION_BOOST = 1.25

# Key aliases tolerated on each suggestion dict, since seed data naming drifts.
_COUNT_KEYS = ("co_purchase_count", "count", "co_occurrence", "times_bought_together")
_MARGIN_KEYS = ("margin", "margin_delta", "margin_impact")
_PROMO_FLAG_KEYS = ("is_promoted", "promoted")


def _as_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _first_present(entry: dict, keys, default=None):
    for key in keys:
        if entry.get(key) is not None:
            return entry[key]
    return default


def recommend_upsell(
    cart_items: list[str],
    co_occurrence_data: dict,
    *,
    min_margin: float = 0.0,
    min_lift: float = 0.0,
    limit: int | None = None,
) -> list[dict]:
    """Rank cross-sell suggestions for the products currently in the cart.

    Ranking, in order of preference:

      1. Apriori data (confidence present):  confidence x margin
         "Of the baskets containing the laptop, 62% also contained the dock;
          the dock earns 50 margin; so suggesting it is worth ~31."
         This is an expected-value ranking, which is what a rep actually wants.
      2. Hand-authored data (no confidence): co_purchase_count x margin
         Raw count stands in for likelihood.
      3. No margin available anywhere (products.margin not in the database
         yet): likelihood alone -- confidence if present, else count. Without
         this fallback every score would be x 0.0 and the sort would collapse
         onto its product_id tiebreak, returning alphabetical order that looks
         like a ranking. ranking_basis says which of the four applied.

    Either way the score is multiplied by PROMOTION_BOOST for promoted
    products (PDF A6). Count alone would float cheap high-volume accessories
    to the top; margin alone would float expensive things nobody buys
    alongside. The product of likelihood and margin ranks suggestions that are
    both plausible and worth selling.

    A suggestion co-occurring with several cart items has counts SUMMED (more
    evidence) while margin, confidence and lift take the MAX seen -- the
    strongest association wins, and margin belongs to the product rather than
    to any one pairing.

    Args:
        cart_items: product ids already in the quotation. Anything already in
            the cart is never suggested back.
        co_occurrence_data: {cart_product_id: [suggestion, ...]}. Each
            suggestion:
              {"product_id": "DOCK-01",
               "co_purchase_count": 42,        # or count / co_occurrence
               "margin": 55.0,                 # or margin_delta / margin_impact
               "confidence": 0.62,             # optional, from Apriori
               "lift": 2.4,                    # optional, from Apriori
               "is_promoted": True,            # optional, or promoted
               "promo_tag": "Q1 Bundle",       # optional
               "product_name": "Dock Station"} # optional
            Cart products absent from the dict contribute nothing.
        min_margin: keyword-only. Drop suggestions below this margin, so only
            healthy-margin products surface (PDF A6).
        min_lift: keyword-only. Drop associations weaker than this. 1.0 means
            "only keep pairings stronger than the product's base popularity".
            Ignored for suggestions with no lift.
        limit: keyword-only. Cap the number of cards returned.

    Returns:
        Ranked list, best first:
        [{
          "product_id": str,          # API_CONTRACT key
          "margin_delta": float,      # API_CONTRACT key -- margin if added
          # --- additive, beyond the contract ---
          "co_purchase_count": float,
          "score": float,
          "ranking_basis": "confidence_x_margin" | "count_x_margin"
                            | "confidence_only" | "count_only",
                            # the _only forms mean no margin data was
                            # available -- the ranking is likelihood-only
          "confidence": float | None, # P(suggested | in cart), from Apriori
          "lift": float | None,       # association strength vs base rate
          "expected_margin": float | None,  # confidence x margin
          "is_promoted": bool,
          "promo_tag": str | None,    # None when not promoted
          "product_name": str,
        }]

        Sorted by score desc, then margin_delta desc, then product_id asc, so
        ordering is deterministic for demos and tests.
    """
    cart = [str(item) for item in (cart_items or [])]
    in_cart = set(cart)
    if not cart or not isinstance(co_occurrence_data, dict):
        return []

    aggregated: dict[str, dict] = {}

    for cart_product in cart:
        suggestions = co_occurrence_data.get(cart_product) or []
        if isinstance(suggestions, dict):
            # Tolerate {"DOCK-01": {...}} keyed by product id.
            suggestions = [
                {**value, "product_id": key} if isinstance(value, dict) else value
                for key, value in suggestions.items()
            ]
        if not isinstance(suggestions, list):
            continue

        for entry in suggestions:
            if not isinstance(entry, dict):
                continue
            product_id = entry.get("product_id")
            if product_id is None:
                continue
            product_id = str(product_id)
            if product_id in in_cart:
                continue  # already quoted, never suggest it back

            count = _as_float(_first_present(entry, _COUNT_KEYS))
            margin = _as_float(_first_present(entry, _MARGIN_KEYS))
            promoted = bool(_first_present(entry, _PROMO_FLAG_KEYS, False))
            confidence = entry.get("confidence")
            confidence = _as_float(confidence, None) if confidence is not None else None
            lift = entry.get("lift")
            lift = _as_float(lift, None) if lift is not None else None

            existing = aggregated.get(product_id)
            if existing is None:
                aggregated[product_id] = {
                    "product_id": product_id,
                    "margin_delta": margin,
                    "co_purchase_count": count,
                    "confidence": confidence,
                    "lift": lift,
                    "is_promoted": promoted,
                    "promo_tag": entry.get("promo_tag"),
                    "product_name": entry.get("product_name") or product_id,
                    # "upsell" (richer plan/tier for the same purchase) vs
                    # "cross_sell" (a separate, complementary product) --
                    # admin-set on the UpsellRule, passed through untouched;
                    # this function doesn't infer it. Defaults to cross_sell
                    # for callers that don't supply it.
                    "suggestion_type": entry.get("suggestion_type") or "cross_sell",
                }
            else:
                existing["co_purchase_count"] += count
                existing["margin_delta"] = max(existing["margin_delta"], margin)
                existing["is_promoted"] = existing["is_promoted"] or promoted
                existing["promo_tag"] = existing["promo_tag"] or entry.get("promo_tag")
                if confidence is not None:
                    existing["confidence"] = (
                        confidence if existing["confidence"] is None
                        else max(existing["confidence"], confidence)
                    )
                if lift is not None:
                    existing["lift"] = (
                        lift if existing["lift"] is None
                        else max(existing["lift"], lift)
                    )

    # Margin is what makes the ranking meaningful, but it is not always there:
    # products.margin does not exist in the database yet, so every suggestion
    # can arrive with margin 0.0. Multiplying by it would zero every score and
    # collapse the sort onto its product_id tiebreak -- alphabetical order
    # dressed up as a recommendation. When no suggestion carries a usable
    # margin, rank on likelihood alone and say so in ranking_basis, so a caller
    # can tell a degraded ranking from a real one.
    has_margin = any(row["margin_delta"] > 0 for row in aggregated.values())

    results = []
    for row in aggregated.values():
        if row["margin_delta"] < min_margin:
            continue
        if min_lift and row["lift"] is not None and row["lift"] < min_lift:
            continue

        if not has_margin:
            expected_margin = None
            if row["confidence"] is not None:
                score = row["confidence"]
                basis = "confidence_only"
            else:
                score = row["co_purchase_count"]
                basis = "count_only"
        elif row["confidence"] is not None:
            expected_margin = row["confidence"] * row["margin_delta"]
            score = expected_margin
            basis = "confidence_x_margin"
        else:
            expected_margin = None
            score = row["co_purchase_count"] * row["margin_delta"]
            basis = "count_x_margin"

        if row["is_promoted"]:
            score *= PROMOTION_BOOST

        results.append(
            {
                "product_id": row["product_id"],
                "margin_delta": round(row["margin_delta"], 2),
                "co_purchase_count": round(row["co_purchase_count"], 2),
                "score": round(score, 2),
                "ranking_basis": basis,
                "confidence": (
                    round(row["confidence"], 4) if row["confidence"] is not None else None
                ),
                "lift": round(row["lift"], 4) if row["lift"] is not None else None,
                "expected_margin": (
                    round(expected_margin, 2) if expected_margin is not None else None
                ),
                "is_promoted": row["is_promoted"],
                "promo_tag": row["promo_tag"] if row["is_promoted"] else None,
                "product_name": row["product_name"],
                "suggestion_type": row["suggestion_type"],
            }
        )

    results.sort(
        key=lambda row: (-row["score"], -row["margin_delta"], row["product_id"])
    )

    if limit is not None and limit >= 0:
        results = results[:limit]
    return results
