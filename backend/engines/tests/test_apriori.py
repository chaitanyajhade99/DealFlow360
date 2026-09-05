"""Apriori tests: support counting, the downward-closure prune, and rules."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apriori import (  # noqa: E402
    build_co_occurrence,
    find_frequent_itemsets,
    generate_rules,
)
from synthetic_data import generate_transactions, product_margins  # noqa: E402

# Hand-countable baskets, so every support below can be verified by eye.
TOY_BASKETS = [
    ["bread", "milk"],
    ["bread", "nappies", "beer", "eggs"],
    ["milk", "nappies", "beer", "cola"],
    ["bread", "milk", "nappies", "beer"],
    ["bread", "milk", "nappies", "cola"],
]


class TestFrequentItemsets(unittest.TestCase):
    def test_supports_match_hand_counted_values(self):
        itemsets = find_frequent_itemsets(TOY_BASKETS, min_support=0.4, max_len=3)

        # bread in 4 of 5 baskets, milk in 4, nappies in 4, beer in 3.
        self.assertAlmostEqual(itemsets[frozenset(["bread"])], 0.8)
        self.assertAlmostEqual(itemsets[frozenset(["milk"])], 0.8)
        self.assertAlmostEqual(itemsets[frozenset(["nappies"])], 0.8)
        self.assertAlmostEqual(itemsets[frozenset(["beer"])], 0.6)
        # The classic pair: nappies+beer in baskets 2, 3, 4 -> 3 of 5.
        self.assertAlmostEqual(itemsets[frozenset(["nappies", "beer"])], 0.6)

    def test_infrequent_items_are_pruned(self):
        itemsets = find_frequent_itemsets(TOY_BASKETS, min_support=0.4, max_len=3)

        # eggs appears once (0.2), cola twice (0.4 -> kept at the boundary).
        self.assertNotIn(frozenset(["eggs"]), itemsets)
        self.assertIn(frozenset(["cola"]), itemsets)

    def test_downward_closure_prunes_supersets(self):
        """No itemset can survive if one of its subsets did not.

        This is the invariant that makes Apriori tractable, so assert it
        directly across the whole result.
        """
        itemsets = find_frequent_itemsets(TOY_BASKETS, min_support=0.4, max_len=3)

        for itemset in itemsets:
            for item in itemset:
                subset = itemset - frozenset([item])
                if subset:
                    self.assertIn(
                        subset, itemsets,
                        f"{set(itemset)} kept but subset {set(subset)} was not",
                    )

    def test_max_len_bounds_itemset_size(self):
        itemsets = find_frequent_itemsets(TOY_BASKETS, min_support=0.2, max_len=2)

        self.assertTrue(all(len(itemset) <= 2 for itemset in itemsets))

    def test_empty_input_returns_nothing(self):
        self.assertEqual(find_frequent_itemsets([], min_support=0.1), {})


class TestAssociationRules(unittest.TestCase):
    def test_confidence_and_lift_are_computed_correctly(self):
        itemsets = find_frequent_itemsets(TOY_BASKETS, min_support=0.4, max_len=2)
        rules = generate_rules(itemsets, min_confidence=0.5, min_lift=1.0)

        rule = next(
            r for r in rules
            if r["antecedent"] == ("beer",) and r["consequent"] == ("nappies",)
        )
        # beer in 3 baskets, all 3 also contain nappies -> confidence 1.0
        self.assertAlmostEqual(rule["confidence"], 1.0, places=4)
        # nappies base rate is 0.8, so lift = 1.0 / 0.8 = 1.25
        self.assertAlmostEqual(rule["lift"], 1.25, places=4)

    def test_min_lift_drops_popularity_artefacts(self):
        """A rule with lift ~1 says nothing beyond 'this product is popular'."""
        itemsets = find_frequent_itemsets(TOY_BASKETS, min_support=0.2, max_len=2)

        loose = generate_rules(itemsets, min_confidence=0.1, min_lift=0.0)
        strict = generate_rules(itemsets, min_confidence=0.1, min_lift=1.2)

        self.assertLess(len(strict), len(loose))
        self.assertTrue(all(rule["lift"] >= 1.2 for rule in strict))

    def test_rules_are_sorted_by_lift_descending(self):
        itemsets = find_frequent_itemsets(TOY_BASKETS, min_support=0.2, max_len=3)
        rules = generate_rules(itemsets, min_confidence=0.1, min_lift=0.0)

        lifts = [rule["lift"] for rule in rules]
        self.assertEqual(lifts, sorted(lifts, reverse=True))


class TestBuildCoOccurrence(unittest.TestCase):
    def test_recovers_the_planted_associations(self):
        """The generator plants SERVER-01 -> RACK/INSTALL/SUPPORT at high
        probability. Apriori must rediscover that from raw baskets alone."""
        transactions = generate_transactions(n_baskets=2000, seed=7)

        co_occurrence = build_co_occurrence(transactions, product_margins())

        server_suggestions = {row["product_id"] for row in co_occurrence["SERVER-01"]}
        self.assertIn("RACK-01", server_suggestions)
        self.assertIn("INSTALL-01", server_suggestions)
        self.assertIn("SUPPORT-01", server_suggestions)

    def test_output_matches_the_recommend_upsell_contract(self):
        transactions = generate_transactions(n_baskets=1000, seed=7)

        co_occurrence = build_co_occurrence(transactions, product_margins())

        for anchor, suggestions in co_occurrence.items():
            self.assertIsInstance(anchor, str)
            for row in suggestions:
                for key in ("product_id", "margin", "co_purchase_count",
                            "confidence", "lift", "is_promoted"):
                    self.assertIn(key, row)
                self.assertGreater(row["lift"], 1.0)
            # Strongest association first within each anchor.
            lifts = [row["lift"] for row in suggestions]
            self.assertEqual(lifts, sorted(lifts, reverse=True))

    def test_margin_metadata_is_joined_onto_mined_ids(self):
        """Apriori only sees product ids; margin has to come from the catalogue."""
        transactions = generate_transactions(n_baskets=1000, seed=7)

        co_occurrence = build_co_occurrence(transactions, product_margins())

        warranty = next(
            row for rows in co_occurrence.values() for row in rows
            if row["product_id"] == "WARRANTY-01"
        )
        self.assertEqual(warranty["margin"], 85.0)
        self.assertTrue(warranty["is_promoted"])
        self.assertEqual(warranty["promo_tag"], "Q1 Bundle")


if __name__ == "__main__":
    unittest.main()
