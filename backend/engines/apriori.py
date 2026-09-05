"""Apriori frequent-itemset mining and association rules, from scratch.

No mlxtend dependency -- this is the algorithm layer, so the algorithm lives
here. Pure functions: baskets in, rules out. Nothing touches a DB.

Apriori in one line: an itemset can only be frequent if every one of its
subsets is frequent. So build itemsets up one size at a time, and prune any
candidate with an infrequent subset before spending a pass counting it. That
downward-closure prune is what makes it tractable.

Used by upsell_engine.recommend_upsell() via build_co_occurrence(), which
turns mined rules into the co_occurrence_data dict API_CONTRACT.md specifies.
"""

from __future__ import annotations

from itertools import combinations

# Defaults tuned for the synthetic catalogue (14 products, ~3000 baskets).
DEFAULT_MIN_SUPPORT = 0.02
DEFAULT_MIN_CONFIDENCE = 0.25
DEFAULT_MIN_LIFT = 1.05
DEFAULT_MAX_LEN = 3


def find_frequent_itemsets(
    transactions: list[list[str]],
    min_support: float = DEFAULT_MIN_SUPPORT,
    max_len: int = DEFAULT_MAX_LEN,
) -> dict[frozenset, float]:
    """Mine frequent itemsets by Apriori's level-wise search.

    Args:
        transactions: baskets, each a list of product ids. Duplicates within a
            basket are ignored (presence is what matters, not quantity).
        min_support: minimum fraction of baskets an itemset must appear in.
        max_len: largest itemset size to mine. Bounds the combinatorics.

    Returns:
        {frozenset(items): support} for every itemset clearing min_support,
        all sizes from 1 to max_len.
    """
    baskets = [frozenset(basket) for basket in transactions if basket]
    n_baskets = len(baskets)
    if n_baskets == 0 or max_len < 1:
        return {}

    frequent: dict[frozenset, float] = {}

    # --- Level 1: count every individual item. ---
    counts: dict[frozenset, int] = {}
    for basket in baskets:
        for item in basket:
            key = frozenset([item])
            counts[key] = counts.get(key, 0) + 1

    current = set()
    for itemset, count in counts.items():
        support = count / n_baskets
        if support >= min_support:
            frequent[itemset] = support
            current.add(itemset)

    # --- Levels 2..max_len ---
    k = 2
    while current and k <= max_len:
        candidates = _generate_candidates(current, k)
        if not candidates:
            break

        counts = {}
        for basket in baskets:
            for candidate in candidates:
                if candidate <= basket:  # subset test
                    counts[candidate] = counts.get(candidate, 0) + 1

        current = set()
        for itemset, count in counts.items():
            support = count / n_baskets
            if support >= min_support:
                frequent[itemset] = support
                current.add(itemset)
        k += 1

    return frequent


def _generate_candidates(previous: set[frozenset], k: int) -> set[frozenset]:
    """Join frequent (k-1)-itemsets into k-itemsets, then prune.

    The prune step is the heart of Apriori: a candidate survives only if all
    of its (k-1)-subsets were themselves frequent. Anything else cannot
    possibly be frequent, so it is dropped without ever being counted.
    """
    candidates = set()
    previous_list = sorted(previous, key=sorted)

    for i, left in enumerate(previous_list):
        for right in previous_list[i + 1:]:
            union = left | right
            if len(union) != k:
                continue
            # Downward closure: every (k-1)-subset must be frequent.
            if all(frozenset(subset) in previous for subset in combinations(union, k - 1)):
                candidates.add(union)

    return candidates


def generate_rules(
    frequent_itemsets: dict[frozenset, float],
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_lift: float = DEFAULT_MIN_LIFT,
) -> list[dict]:
    """Derive association rules antecedent -> consequent from frequent itemsets.

    For each frequent itemset, try every way of splitting it into a non-empty
    antecedent and a non-empty consequent, and keep the splits that are strong
    enough.

        confidence = support(A u C) / support(A)
            "of the baskets containing A, what fraction also contain C"
        lift       = confidence / support(C)
            "how much more likely is C given A than C on its own"

    Lift is the one that matters for upsell. Confidence alone will happily
    recommend a product that appears in most baskets regardless of the cart
    (high confidence, lift ~= 1, no actual signal). Lift > 1 means a genuine
    association rather than a popularity artefact.

    Args:
        frequent_itemsets: output of find_frequent_itemsets().
        min_confidence: minimum confidence to keep a rule.
        min_lift: minimum lift to keep a rule. Keep this above 1.0.

    Returns:
        Rule dicts sorted by lift descending:
        {"antecedent": tuple[str, ...], "consequent": tuple[str, ...],
         "support": float, "confidence": float, "lift": float}
    """
    rules = []

    for itemset, itemset_support in frequent_itemsets.items():
        if len(itemset) < 2:
            continue
        items = sorted(itemset)
        for size in range(1, len(items)):
            for antecedent_items in combinations(items, size):
                antecedent = frozenset(antecedent_items)
                consequent = itemset - antecedent
                antecedent_support = frequent_itemsets.get(antecedent)
                consequent_support = frequent_itemsets.get(consequent)
                if not antecedent_support or not consequent_support:
                    continue

                confidence = itemset_support / antecedent_support
                if confidence < min_confidence:
                    continue
                lift = confidence / consequent_support
                if lift < min_lift:
                    continue

                rules.append(
                    {
                        "antecedent": tuple(sorted(antecedent)),
                        "consequent": tuple(sorted(consequent)),
                        "support": round(itemset_support, 6),
                        "confidence": round(confidence, 6),
                        "lift": round(lift, 6),
                    }
                )

    rules.sort(key=lambda rule: (-rule["lift"], -rule["confidence"], rule["antecedent"]))
    return rules


def build_co_occurrence(
    transactions: list[list[str]],
    product_meta: dict[str, dict] | None = None,
    min_support: float = DEFAULT_MIN_SUPPORT,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_lift: float = DEFAULT_MIN_LIFT,
) -> dict[str, list[dict]]:
    """Mine baskets and emit the co_occurrence_data dict recommend_upsell() eats.

    Keeps the single-item -> single-item rules, since recommend_upsell() looks
    up one cart product at a time per API_CONTRACT.md. The miner itself
    handles arbitrary antecedent sizes; wiring multi-item antecedents ("laptop
    AND monitor together imply a dock") into the cart lookup is the obvious
    next improvement.

    Args:
        transactions: historical baskets.
        product_meta: product_id -> {product_name, margin, is_promoted,
            promo_tag}. Apriori only ever sees ids, so this is what supplies
            the margin that ranking needs. Missing products get margin 0.0.
        min_support / min_confidence / min_lift: mining thresholds.

    Returns:
        {antecedent_product_id: [suggestion, ...]} where each suggestion is
        {"product_id", "product_name", "co_purchase_count", "margin",
         "is_promoted", "promo_tag", "support", "confidence", "lift"},
        sorted by lift descending within each key.

        co_purchase_count is the absolute number of baskets containing both
        products, so the existing count-based ranking keeps working unchanged.
    """
    product_meta = product_meta or {}
    n_baskets = len([basket for basket in transactions if basket])

    frequent = find_frequent_itemsets(transactions, min_support, max_len=2)
    rules = generate_rules(frequent, min_confidence, min_lift)

    co_occurrence: dict[str, list[dict]] = {}
    for rule in rules:
        if len(rule["antecedent"]) != 1 or len(rule["consequent"]) != 1:
            continue
        anchor = rule["antecedent"][0]
        suggested = rule["consequent"][0]
        meta = product_meta.get(suggested, {})

        co_occurrence.setdefault(anchor, []).append(
            {
                "product_id": suggested,
                "product_name": meta.get("product_name", suggested),
                "co_purchase_count": round(rule["support"] * n_baskets),
                "margin": float(meta.get("margin", 0.0)),
                "is_promoted": bool(meta.get("is_promoted", False)),
                "promo_tag": meta.get("promo_tag"),
                "support": rule["support"],
                "confidence": rule["confidence"],
                "lift": rule["lift"],
            }
        )

    for suggestions in co_occurrence.values():
        suggestions.sort(key=lambda row: -row["lift"])

    return co_occurrence
