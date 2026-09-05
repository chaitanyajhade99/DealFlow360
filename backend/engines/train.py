"""Generate the synthetic datasets and train both models.

    python backend/engines/train.py            # generate + train + save
    python backend/engines/train.py --quotes 8000 --baskets 6000

Writes everything into backend/engines/data/:

    quotation_history.csv     labelled training rows (one row per quote)
    transactions.csv          historical baskets, one basket per line
    rep_histories.json        per-rep discount history for detect_anomalies
    co_occurrence.json        Apriori-mined rules for recommend_upsell
    risk_model.json           trained XGBoost booster
    risk_model_meta.json      feature order + held-out metrics

Re-runnable and deterministic: the same seed always produces the same
datasets, the same rules, and the same model.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apriori import build_co_occurrence, find_frequent_itemsets, generate_rules  # noqa: E402
from risk_model import extract_features, train_risk_model  # noqa: E402
from synthetic_data import (  # noqa: E402
    generate_quotation_history,
    generate_rep_discount_histories,
    generate_transactions,
    product_margins,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _write_quotation_csv(quotes, rep_histories, path):
    """One row per quote: the model's feature vector plus its label."""
    rep_baselines = {
        rep_id: sum(history) / len(history)
        for rep_id, history in rep_histories.items() if history
    }
    fieldnames = None
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = None
        for quote in quotes:
            features = extract_features(
                quote["lines"],
                customer_tier=quote["customer_tier"],
                rep_avg_discount_pct=rep_baselines.get(quote["rep_id"]),
                is_quarter_end=quote["is_quarter_end"],
                seniority=quote["seniority"],
            )
            row = {
                "quotation_id": quote["quotation_id"],
                "rep_id": quote["rep_id"],
                "customer_tier": quote["customer_tier"],
                "n_lines_raw": len(quote["lines"]),
                **{k: round(v, 6) for k, v in features.items()},
                "latent_risk": quote["latent_risk"],
                "risk_label": quote["risk_label"],
            }
            if writer is None:
                fieldnames = list(row)
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
            writer.writerow(row)
    return fieldnames


def main() -> None:
    parser = argparse.ArgumentParser(description="Train DealFlow360 engine models.")
    parser.add_argument("--quotes", type=int, default=4000)
    parser.add_argument("--baskets", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-support", type=float, default=0.02)
    parser.add_argument("--min-confidence", type=float, default=0.25)
    parser.add_argument("--min-lift", type=float, default=1.05)
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 72)
    print("1/4  Generating synthetic quotation history")
    print("=" * 72)
    quotes = generate_quotation_history(n_quotes=args.quotes, seed=args.seed)
    rep_histories = generate_rep_discount_histories(quotes)
    distribution = {}
    for quote in quotes:
        band = ["LOW", "MEDIUM", "HIGH"][quote["risk_label"]]
        distribution[band] = distribution.get(band, 0) + 1
    print(f"  {len(quotes)} quotes, {sum(len(q['lines']) for q in quotes)} lines")
    print(f"  label distribution: {distribution}")
    print(f"  {len(rep_histories)} reps with discount histories")

    # Attach each rep's baseline so training sees the same feature the API will.
    rep_baselines = {
        rep_id: sum(history) / len(history)
        for rep_id, history in rep_histories.items() if history
    }
    for quote in quotes:
        quote["rep_avg_discount_pct"] = rep_baselines.get(quote["rep_id"])

    quotation_csv = os.path.join(DATA_DIR, "quotation_history.csv")
    _write_quotation_csv(quotes, rep_histories, quotation_csv)
    print(f"  -> {quotation_csv}")

    with open(os.path.join(DATA_DIR, "rep_histories.json"), "w", encoding="utf-8") as handle:
        json.dump(rep_histories, handle, indent=2)
    print(f"  -> {os.path.join(DATA_DIR, 'rep_histories.json')}")

    print()
    print("=" * 72)
    print("2/4  Generating basket transactions")
    print("=" * 72)
    transactions = generate_transactions(n_baskets=args.baskets, seed=args.seed)
    avg_size = sum(len(b) for b in transactions) / len(transactions)
    print(f"  {len(transactions)} baskets, avg {avg_size:.2f} items")
    transactions_csv = os.path.join(DATA_DIR, "transactions.csv")
    with open(transactions_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["basket_id", "product_ids"])
        for i, basket in enumerate(transactions):
            writer.writerow([f"B-{i + 1:05d}", "|".join(basket)])
    print(f"  -> {transactions_csv}")

    print()
    print("=" * 72)
    print("3/4  Mining association rules (Apriori)")
    print("=" * 72)
    frequent = find_frequent_itemsets(transactions, args.min_support, max_len=3)
    by_size = {}
    for itemset in frequent:
        by_size[len(itemset)] = by_size.get(len(itemset), 0) + 1
    print(f"  frequent itemsets by size: {dict(sorted(by_size.items()))}")

    all_rules = generate_rules(frequent, args.min_confidence, args.min_lift)
    print(f"  {len(all_rules)} association rules above "
          f"confidence {args.min_confidence} / lift {args.min_lift}")
    print("\n  Top rules by lift:")
    for rule in all_rules[:8]:
        antecedent = ", ".join(rule["antecedent"])
        consequent = ", ".join(rule["consequent"])
        print(f"    {antecedent:28} -> {consequent:14} "
              f"supp={rule['support']:.3f} conf={rule['confidence']:.3f} "
              f"lift={rule['lift']:.2f}")

    co_occurrence = build_co_occurrence(
        transactions, product_margins(),
        args.min_support, args.min_confidence, args.min_lift,
    )
    co_path = os.path.join(DATA_DIR, "co_occurrence.json")
    with open(co_path, "w", encoding="utf-8") as handle:
        json.dump(co_occurrence, handle, indent=2)
    print(f"\n  {len(co_occurrence)} anchor products with suggestions")
    print(f"  -> {co_path}")

    print()
    print("=" * 72)
    print("4/4  Training XGBoost risk model")
    print("=" * 72)
    metrics = train_risk_model(quotes, seed=args.seed)
    print(f"  train/test: {metrics['n_train']} / {metrics['n_test']}")
    print(f"  accuracy:   {metrics['accuracy']:.4f}")
    print(f"  macro F1:   {metrics['macro_f1']:.4f}")
    print("\n  Held-out classification report:")
    for line in metrics["report"].splitlines():
        print(f"    {line}")
    print("  Feature importance (gain):")
    for name, gain in metrics["feature_importance"][:10]:
        print(f"    {name:28} {gain:>10.2f}")
    print(f"\n  -> {metrics['model_path']}")

    print()
    print("=" * 72)
    print("Done. Run `python backend/engines/demo.py` to see the engines using it.")
    print("=" * 72)


if __name__ == "__main__":
    main()
