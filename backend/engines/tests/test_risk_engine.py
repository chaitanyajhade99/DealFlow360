"""score_risk tests.

Split in two:
  TestScoreRulesOnly - pins the deterministic rule engine (use_model=False),
      so retraining the model can never silently change these expectations.
  TestHybridScoring  - pins how the rule floor and the model combine.

The first case is the PDF section 10 worked example.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import risk_model  # noqa: E402
from risk_engine import score_risk, score_rules_only  # noqa: E402

PDF_EXAMPLE_LINES = [
    {
        "id": 1, "product_name": "Laptop", "category": "Hardware",
        "qty": 10, "unit_price": 1200.0,
        "discount_pct": 12.0, "category_limit_pct": 15.0,
    },
    {
        "id": 2, "product_name": "Setup Service", "category": "Service",
        "qty": 1, "unit_price": 2000.0,
        "discount_pct": 18.0, "category_limit_pct": 10.0,
    },
]


class TestScoreRulesOnly(unittest.TestCase):
    """Deterministic rule engine. No model involvement."""

    def test_pdf_worked_example_is_high(self):
        """PDF section 10: Gold customer, Laptop fine, Setup Service 8 points over.

        'Even though the customer is Gold and 15 percent sounds fine on paper,
        the Service line broke its own stricter limit. So the whole quotation
        gets flagged for approval, because of that one line.'

        Note the blend alone is only 1.14 points -- the big clean Laptop line
        dilutes it. It is the single-line rule that forces HIGH, which is
        exactly the behaviour the PDF describes.
        """
        result = score_risk(PDF_EXAMPLE_LINES, use_model=False)

        self.assertEqual(result["blended_risk"], "HIGH")
        self.assertEqual(result["rule_risk"], "HIGH")
        self.assertEqual(result["worst_line_over_pct"], 8.0)
        self.assertEqual(result["blended_score_pct"], 1.14)  # 8 * 2000 / 14000
        self.assertEqual(result["approval_chain"], ["Sales Manager", "Finance"])

        # Only the Service line broke its own ceiling; the Laptop is clean.
        self.assertEqual(len(result["flagged_lines"]), 1)
        flagged = result["flagged_lines"][0]
        self.assertEqual(flagged["line"], "Setup Service")
        self.assertEqual(flagged["discount_given_pct"], 18.0)
        self.assertEqual(flagged["limit_allowed_pct"], 10.0)
        self.assertEqual(flagged["over_by_pct"], 8.0)

    def test_many_small_overages_are_not_ignored(self):
        """PDF 'Why blended?': 2 over, 3 over, 2 over -- none alarming alone."""
        lines = [
            {"id": i, "product_name": name, "qty": 10, "unit_price": 1000.0,
             "discount_pct": 10.0 + over, "category_limit_pct": 10.0}
            for i, (name, over) in enumerate(
                [("Line A", 2.0), ("Line B", 3.0), ("Line C", 2.0)], start=1
            )
        ]

        result = score_risk(lines, use_model=False)

        # Flagged rather than slipping through, but no single line is severe.
        self.assertEqual(result["blended_risk"], "MEDIUM")
        self.assertEqual(result["approval_chain"], ["Sales Manager"])
        self.assertEqual(result["worst_line_over_pct"], 3.0)
        self.assertEqual(result["blended_score_pct"], 2.33)  # (2+3+2)/3
        self.assertEqual(len(result["flagged_lines"]), 3)
        # Worst overage sorts first for screen 6.
        self.assertEqual(
            [row["over_by_pct"] for row in result["flagged_lines"]], [3.0, 2.0, 2.0]
        )

    def test_blended_escalates_without_any_severe_line(self):
        """Spread-out overages reach HIGH even though no line hits 5 points.

        Proves the blend is a real value-weighted sum, not just max().
        """
        lines = [
            {"id": 1, "product_name": "A", "qty": 5, "unit_price": 400.0,
             "discount_pct": 14.0, "category_limit_pct": 10.0},
            {"id": 2, "product_name": "B", "qty": 5, "unit_price": 600.0,
             "discount_pct": 19.0, "category_limit_pct": 15.0},
        ]

        result = score_risk(lines, use_model=False)

        self.assertEqual(result["worst_line_over_pct"], 4.0)  # below single-line rule
        self.assertEqual(result["blended_score_pct"], 4.0)  # at/above blended rule
        self.assertEqual(result["blended_risk"], "HIGH")

    def test_clean_quote_is_low_with_no_flagged_lines(self):
        lines = [
            {"id": 1, "product_name": "Laptop", "category": "Hardware", "qty": 5,
             "unit_price": 1200.0, "discount_pct": 5.0, "category_limit_pct": 15.0},
            {"id": 2, "product_name": "Setup Service", "category": "Service",
             "qty": 1, "unit_price": 500.0,
             "discount_pct": 10.0, "category_limit_pct": 10.0},  # exactly at ceiling
        ]

        result = score_risk(lines, use_model=False)

        self.assertEqual(result["blended_risk"], "LOW")
        self.assertEqual(result["flagged_lines"], [])
        self.assertEqual(result["blended_score_pct"], 0.0)
        self.assertEqual(result["approval_chain"], [])

    def test_empty_quote_is_low(self):
        result = score_risk([], use_model=False)
        self.assertEqual(result["blended_risk"], "LOW")
        self.assertEqual(result["flagged_lines"], [])
        self.assertEqual(result["total_line_value"], 0.0)

    def test_missing_category_limit_fails_closed(self):
        """A line with no ceiling flags instead of silently passing."""
        lines = [
            {"id": 1, "product_id": "P1", "qty": 1, "unit_price": 100.0,
             "discount_pct": 7.0}
        ]

        result = score_risk(lines, use_model=False)

        self.assertEqual(result["blended_risk"], "HIGH")
        self.assertEqual(result["flagged_lines"][0]["limit_allowed_pct"], 0.0)
        self.assertEqual(result["flagged_lines"][0]["over_by_pct"], 7.0)
        # Falls back to product_id when no product_name is supplied.
        self.assertEqual(result["flagged_lines"][0]["line"], "P1")

    def test_score_rules_only_is_callable_directly(self):
        """Person 1 can bypass the model entirely if they want to."""
        result = score_rules_only(PDF_EXAMPLE_LINES)

        self.assertEqual(result["risk"], "HIGH")
        self.assertEqual(result["worst_line_over_pct"], 8.0)


class _FakeModel:
    """Stand-in booster, so escalation logic is tested without depending on
    what the real model happens to have learned this training run."""

    def __init__(self, band, confidence):
        self.band = band
        self.confidence = confidence

    def predict(self, features):
        return {
            "risk_label": {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[self.band],
            "risk_band": self.band,
            "confidence": self.confidence,
            "probabilities": {"LOW": 0.1, "MEDIUM": 0.2, "HIGH": 0.7},
        }


class TestHybridScoring(unittest.TestCase):
    def setUp(self):
        self._saved = dict(risk_model._MODEL_CACHE)

    def tearDown(self):
        risk_model._MODEL_CACHE.clear()
        risk_model._MODEL_CACHE.update(self._saved)

    def _install(self, band, confidence):
        risk_model._MODEL_CACHE["model"] = _FakeModel(band, confidence)

    def test_confident_model_escalates_a_clean_quote(self):
        """The whole point of the model: catch what line-level rules cannot."""
        clean = [{"id": 1, "product_name": "Laptop", "category": "Hardware",
                  "qty": 5, "unit_price": 1200.0,
                  "discount_pct": 5.0, "category_limit_pct": 15.0}]
        self._install("HIGH", 0.91)

        result = score_risk(clean, customer_tier="Bronze", is_quarter_end=True)

        self.assertEqual(result["rule_risk"], "LOW")
        self.assertEqual(result["blended_risk"], "HIGH")
        self.assertTrue(result["escalated_by_model"])
        self.assertEqual(result["approval_chain"], ["Sales Manager", "Finance"])

    def test_model_can_never_lower_the_rule_floor(self):
        """A ceiling breach is a ceiling breach. The model does not get a veto."""
        self._install("LOW", 0.99)

        result = score_risk(PDF_EXAMPLE_LINES, customer_tier="Gold")

        self.assertEqual(result["rule_risk"], "HIGH")
        self.assertEqual(result["model_risk"], "LOW")
        self.assertEqual(result["blended_risk"], "HIGH")  # floor holds
        self.assertFalse(result["escalated_by_model"])

    def test_unconfident_model_does_not_escalate(self):
        """Below the confidence gate the model is guessing; do not waste a
        manager's time on it."""
        clean = [{"id": 1, "product_name": "Laptop", "qty": 5, "unit_price": 1200.0,
                  "discount_pct": 5.0, "category_limit_pct": 15.0}]
        self._install("HIGH", 0.31)

        result = score_risk(clean)

        self.assertEqual(result["blended_risk"], "LOW")
        self.assertFalse(result["escalated_by_model"])
        self.assertEqual(result["model_risk"], "HIGH")  # still reported

    def test_missing_artifact_degrades_to_rules_only(self):
        """A fresh clone with no trained model must not crash."""
        risk_model._MODEL_CACHE["model"] = None

        result = score_risk(PDF_EXAMPLE_LINES)

        self.assertFalse(result["model_available"])
        self.assertIsNone(result["model_risk"])
        self.assertEqual(result["blended_risk"], "HIGH")  # rules still work

    def test_reason_is_populated_for_the_audit_trail(self):
        """PDF A3 requires approvals logged with a reason."""
        result = score_risk(PDF_EXAMPLE_LINES, use_model=False)

        self.assertIn("Setup Service", result["reason"])
        self.assertIn("18.0%", result["reason"])
        self.assertIn("10.0%", result["reason"])

    def test_use_model_false_reports_no_model_fields(self):
        result = score_risk(PDF_EXAMPLE_LINES, use_model=False)

        self.assertFalse(result["model_available"])
        self.assertIsNone(result["model_risk"])
        self.assertIsNone(result["model_confidence"])


if __name__ == "__main__":
    unittest.main()
