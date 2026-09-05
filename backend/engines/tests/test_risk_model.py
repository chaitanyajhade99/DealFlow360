"""Feature-extraction and model-artifact tests.

The training run itself is not re-executed here (it takes seconds and needs
the artifact on disk); these pin the feature contract, which is what actually
breaks silently when someone edits an engine.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_model import (  # noqa: E402
    FEATURE_NAMES,
    LABEL_TO_BAND,
    MODEL_PATH,
    RiskModel,
    extract_features,
    features_to_vector,
)
from synthetic_data import generate_quotation_history  # noqa: E402

PDF_EXAMPLE_LINES = [
    {"product_name": "Laptop", "category": "Hardware", "qty": 10,
     "unit_price": 1200.0, "discount_pct": 12.0, "category_limit_pct": 15.0},
    {"product_name": "Setup Service", "category": "Service", "qty": 1,
     "unit_price": 2000.0, "discount_pct": 18.0, "category_limit_pct": 10.0},
]


class TestFeatureExtraction(unittest.TestCase):
    def test_features_match_the_rule_engine_on_the_pdf_example(self):
        """The model's blended/worst features must agree with score_risk's,
        or the two halves of the hybrid are describing different quotes."""
        features = extract_features(
            PDF_EXAMPLE_LINES, customer_tier="Gold",
            rep_avg_discount_pct=6.0, is_quarter_end=False, seniority=2,
        )

        self.assertAlmostEqual(features["blended_overage_pct"], 8 * 2000 / 14000)
        self.assertEqual(features["worst_line_overage_pct"], 8.0)
        self.assertEqual(features["n_lines"], 2.0)
        self.assertEqual(features["n_flagged_lines"], 1.0)
        self.assertEqual(features["tier_ordinal"], 2.0)  # Gold
        self.assertAlmostEqual(features["thin_margin_value_share"], 2000 / 14000)
        self.assertAlmostEqual(features["flagged_value_share"], 2000 / 14000)

    def test_unknown_context_becomes_nan_not_a_guessed_zero(self):
        """Zero would be a confident lie: it means 'Bronze' for tier and
        'junior' for seniority. NaN lets XGBoost route it deliberately."""
        features = extract_features(PDF_EXAMPLE_LINES)

        self.assertTrue(math.isnan(features["tier_ordinal"]))
        self.assertTrue(math.isnan(features["seniority"]))
        self.assertTrue(math.isnan(features["discount_vs_rep_baseline"]))
        # Line-derived features are still fully populated.
        self.assertEqual(features["worst_line_overage_pct"], 8.0)

    def test_vector_order_matches_the_declared_feature_names(self):
        """Train and predict both go through features_to_vector, so this is
        the guard against a silent column-order mismatch."""
        features = extract_features(PDF_EXAMPLE_LINES, customer_tier="Gold")
        vector = features_to_vector(features)

        self.assertEqual(len(vector), len(FEATURE_NAMES))
        for i, name in enumerate(FEATURE_NAMES):
            if not math.isnan(vector[i]):
                self.assertAlmostEqual(vector[i], features[name], places=6)

    def test_empty_quote_produces_a_full_zeroed_vector(self):
        features = extract_features([])

        self.assertEqual(len(features_to_vector(features)), len(FEATURE_NAMES))
        self.assertEqual(features["blended_overage_pct"], 0.0)
        self.assertEqual(features["n_lines"], 0.0)

    def test_zero_value_order_still_reports_overage(self):
        """qty 0 lines must not silently zero the risk signal."""
        features = extract_features(
            [{"qty": 0, "unit_price": 100.0, "discount_pct": 20.0,
              "category_limit_pct": 10.0}]
        )

        self.assertEqual(features["blended_overage_pct"], 10.0)
        self.assertEqual(features["worst_line_overage_pct"], 10.0)


class TestCategoryNaming(unittest.TestCase):
    """The database stores "Services"; the engines were written against
    "Service". Both must fold to the same thin-margin bucket, or every real
    quote silently scores thin_margin_value_share 0.0."""

    def _lines(self, service_category):
        return [
            {"category": "Hardware", "qty": 1, "unit_price": 1000.0,
             "discount_pct": 10.0, "category_limit_pct": 15.0},
            {"category": service_category, "qty": 1, "unit_price": 1000.0,
             "discount_pct": 18.0, "category_limit_pct": 10.0},
        ]

    def test_db_plural_matches_engine_singular(self):
        singular = extract_features(self._lines("Service"))
        plural = extract_features(self._lines("Services"))
        self.assertEqual(
            singular["thin_margin_value_share"],
            plural["thin_margin_value_share"],
        )

    def test_thin_margin_share_is_actually_counted(self):
        # Half the order value sits on the Services line. A regression here
        # would read 0.0 rather than raising, so assert the value itself.
        features = extract_features(self._lines("Services"))
        self.assertAlmostEqual(features["thin_margin_value_share"], 0.5)

    def test_case_and_whitespace_are_tolerated(self):
        features = extract_features(self._lines("  services  "))
        self.assertAlmostEqual(features["thin_margin_value_share"], 0.5)

    def test_hardware_is_not_thin_margin(self):
        features = extract_features(self._lines("Hardware"))
        self.assertAlmostEqual(features["thin_margin_value_share"], 0.0)


class TestSyntheticData(unittest.TestCase):
    def test_generation_is_deterministic_under_a_seed(self):
        first = generate_quotation_history(n_quotes=200, seed=99)
        second = generate_quotation_history(n_quotes=200, seed=99)

        self.assertEqual(
            [q["risk_label"] for q in first], [q["risk_label"] for q in second]
        )
        self.assertEqual(first[0]["lines"], second[0]["lines"])

    def test_all_three_risk_bands_are_represented(self):
        """A dataset with no HIGH examples would train a useless model."""
        quotes = generate_quotation_history(n_quotes=800, seed=42)

        labels = {quote["risk_label"] for quote in quotes}
        self.assertEqual(labels, {0, 1, 2})

    def test_line_limits_use_the_stricter_of_tier_and_category(self):
        """PDF A3: a Gold customer still only gets 10% on Service lines."""
        quotes = generate_quotation_history(n_quotes=300, seed=42)

        for quote in quotes:
            for line in quote["lines"]:
                self.assertLessEqual(line["category_limit_pct"], 15.0)
                if quote["customer_tier"] == "Bronze":
                    self.assertLessEqual(line["category_limit_pct"], 5.0)


class TestTrainedArtifact(unittest.TestCase):
    """Skipped when train.py has not been run yet."""

    def setUp(self):
        if not os.path.exists(MODEL_PATH):
            self.skipTest("no trained artifact; run train.py first")
        self.model = RiskModel.load()

    def test_artifact_loads_and_predicts_a_valid_band(self):
        prediction = self.model.predict(
            extract_features(PDF_EXAMPLE_LINES, customer_tier="Gold")
        )

        self.assertIn(prediction["risk_band"], set(LABEL_TO_BAND.values()))
        self.assertGreaterEqual(prediction["confidence"], 0.0)
        self.assertLessEqual(prediction["confidence"], 1.0)
        self.assertAlmostEqual(
            sum(prediction["probabilities"].values()), 1.0, places=3
        )

    def test_artifact_feature_order_matches_the_code(self):
        """Catches a stale artifact trained before a feature was added."""
        self.assertEqual(self.model.feature_names, FEATURE_NAMES)

    def test_a_blatant_quote_scores_riskier_than_a_clean_one(self):
        """Sanity check that the model learned the direction of the signal."""
        clean = extract_features(
            [{"category": "Hardware", "qty": 5, "unit_price": 1000.0,
              "discount_pct": 2.0, "category_limit_pct": 15.0}],
            customer_tier="Gold", seniority=2,
        )
        blatant = extract_features(
            [{"category": "Service", "qty": 40, "unit_price": 3000.0,
              "discount_pct": 40.0, "category_limit_pct": 10.0}],
            customer_tier="Bronze", seniority=0, is_quarter_end=True,
        )

        clean_high = self.model.predict(clean)["probabilities"]["HIGH"]
        blatant_high = self.model.predict(blatant)["probabilities"]["HIGH"]

        self.assertGreater(blatant_high, clean_high)

    def test_missing_artifact_path_returns_none_rather_than_raising(self):
        self.assertIsNone(RiskModel.load(model_path="does-not-exist.json"))


if __name__ == "__main__":
    unittest.main()
