"""recommend_upsell tests."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from upsell_engine import recommend_upsell  # noqa: E402


def co_occurrence():
    return {
        "LAPTOP-01": [
            # Strong on both axes: 40 * 50 = 2000.
            {"product_id": "DOCK-01", "product_name": "Docking Station",
             "co_purchase_count": 40, "margin": 50.0},
            # High volume, thin margin: 90 * 5 = 450.
            {"product_id": "MOUSE-01", "product_name": "Wireless Mouse",
             "co_purchase_count": 90, "margin": 5.0},
            # 20 * 85 = 1700 raw, but promoted -> 2125, so it outranks the dock.
            {"product_id": "WARRANTY-01", "product_name": "3yr Warranty",
             "co_purchase_count": 20, "margin": 85.0,
             "is_promoted": True, "promo_tag": "Q1 Bundle"},
        ],
        "MONITOR-01": [
            {"product_id": "DOCK-01", "product_name": "Docking Station",
             "co_purchase_count": 10, "margin": 50.0},
        ],
    }


class TestRecommendUpsell(unittest.TestCase):
    def test_ranks_by_co_purchase_count_times_margin(self):
        result = recommend_upsell(["LAPTOP-01"], co_occurrence())

        self.assertEqual(
            [row["product_id"] for row in result],
            ["WARRANTY-01", "DOCK-01", "MOUSE-01"],
        )
        # The high-volume, thin-margin mouse loses to both despite the count.
        self.assertEqual(result[2]["co_purchase_count"], 90.0)
        self.assertEqual(result[2]["score"], 450.0)

    def test_promoted_product_outranks_a_higher_raw_score(self):
        """Warranty's raw score is 1700 vs the dock's 2000; the boost flips it."""
        result = recommend_upsell(["LAPTOP-01"], co_occurrence())

        top = result[0]
        self.assertEqual(top["product_id"], "WARRANTY-01")
        self.assertTrue(top["is_promoted"])
        self.assertEqual(top["promo_tag"], "Q1 Bundle")
        self.assertEqual(top["score"], 2125.0)  # 20 * 85 * 1.25
        self.assertEqual(top["margin_delta"], 85.0)
        # Non-promoted cards carry no tag for screen 4 to render.
        self.assertIsNone(result[1]["promo_tag"])
        self.assertFalse(result[1]["is_promoted"])

    def test_products_already_in_the_cart_are_never_suggested(self):
        result = recommend_upsell(["LAPTOP-01", "DOCK-01"], co_occurrence())

        self.assertNotIn("DOCK-01", [row["product_id"] for row in result])
        self.assertEqual(
            [row["product_id"] for row in result], ["WARRANTY-01", "MOUSE-01"]
        )

    def test_counts_aggregate_across_multiple_cart_items(self):
        """The dock co-occurs with both the laptop (40) and the monitor (10)."""
        result = recommend_upsell(["LAPTOP-01", "MONITOR-01"], co_occurrence())

        dock = next(row for row in result if row["product_id"] == "DOCK-01")
        self.assertEqual(dock["co_purchase_count"], 50.0)
        self.assertEqual(dock["score"], 2500.0)  # 50 * 50
        self.assertEqual(dock["product_id"], result[0]["product_id"])  # now the top

    def test_min_margin_filters_out_thin_margin_suggestions(self):
        """PDF A6: only healthy-margin suggestions should surface."""
        result = recommend_upsell(["LAPTOP-01"], co_occurrence(), min_margin=20.0)

        self.assertEqual(
            [row["product_id"] for row in result], ["WARRANTY-01", "DOCK-01"]
        )

    def test_limit_caps_the_number_of_cards(self):
        result = recommend_upsell(["LAPTOP-01"], co_occurrence(), limit=2)

        self.assertEqual(len(result), 2)

    def test_empty_cart_or_unknown_products_return_nothing(self):
        self.assertEqual(recommend_upsell([], co_occurrence()), [])
        self.assertEqual(recommend_upsell(["UNKNOWN-99"], co_occurrence()), [])

    def test_hand_authored_data_falls_back_to_count_ranking(self):
        """No confidence in the data -> the original count x margin basis."""
        result = recommend_upsell(["LAPTOP-01"], co_occurrence())

        self.assertTrue(all(r["ranking_basis"] == "count_x_margin" for r in result))
        self.assertTrue(all(r["confidence"] is None for r in result))
        self.assertTrue(all(r["expected_margin"] is None for r in result))


class TestRankingWithoutMargin(unittest.TestCase):
    """products.margin does not exist in the database yet, so every suggestion
    can arrive with margin 0.0. Ranking must fall back to likelihood rather
    than collapsing onto the product_id tiebreak."""

    def _no_margin(self, with_confidence):
        rows = [
            {"product_id": "ZEBRA-01", "co_purchase_count": 10},
            {"product_id": "ALPHA-01", "co_purchase_count": 90},
        ]
        if with_confidence:
            rows[0]["confidence"] = 0.1
            rows[1]["confidence"] = 0.9
        return {"LAPTOP-01": rows}

    def test_falls_back_to_count_when_no_margin_anywhere(self):
        results = recommend_upsell(["LAPTOP-01"], self._no_margin(False))
        # Alphabetical order would put ALPHA-01 first for the wrong reason;
        # it must be first because 90 > 10.
        self.assertEqual([r["product_id"] for r in results],
                         ["ALPHA-01", "ZEBRA-01"])
        self.assertEqual(results[0]["score"], 90.0)
        self.assertEqual(results[0]["ranking_basis"], "count_only")

    def test_falls_back_to_confidence_when_apriori_but_no_margin(self):
        results = recommend_upsell(["LAPTOP-01"], self._no_margin(True))
        self.assertEqual([r["product_id"] for r in results],
                         ["ALPHA-01", "ZEBRA-01"])
        self.assertEqual(results[0]["ranking_basis"], "confidence_only")
        self.assertIsNone(results[0]["expected_margin"])

    def test_ranking_does_not_degrade_when_any_margin_is_present(self):
        data = self._no_margin(False)
        data["LAPTOP-01"][0]["margin"] = 500.0   # ZEBRA-01: 10 * 500 = 5000
        results = recommend_upsell(["LAPTOP-01"], data)
        self.assertEqual(results[0]["product_id"], "ZEBRA-01")
        self.assertEqual(results[0]["ranking_basis"], "count_x_margin")

    def test_degraded_basis_is_reported_so_callers_can_tell(self):
        degraded = recommend_upsell(["LAPTOP-01"], self._no_margin(True))
        healthy = recommend_upsell(["LAPTOP-01"], co_occurrence())
        self.assertTrue(all(r["ranking_basis"].endswith("_only") for r in degraded))
        self.assertFalse(any(r["ranking_basis"].endswith("_only") for r in healthy))


class TestRecommendUpsellWithApriori(unittest.TestCase):
    """When the data comes from Apriori it carries confidence and lift, so
    ranking switches to expected margin."""

    def mined(self):
        return {
            "LAPTOP-01": [
                # 62% of laptop baskets take a dock -> expected margin 0.62*50 = 31.0
                {"product_id": "DOCK-01", "product_name": "Docking Station",
                 "co_purchase_count": 620, "margin": 50.0,
                 "confidence": 0.62, "lift": 2.4},
                # 71% take a mouse, but margin is 5 -> expected margin 3.55
                {"product_id": "MOUSE-01", "product_name": "Wireless Mouse",
                 "co_purchase_count": 710, "margin": 5.0,
                 "confidence": 0.71, "lift": 1.9},
                # 44% take a warranty at margin 85 -> 37.4, boosted to 46.75
                {"product_id": "WARRANTY-01", "product_name": "3yr Warranty",
                 "co_purchase_count": 440, "margin": 85.0,
                 "confidence": 0.44, "lift": 3.1,
                 "is_promoted": True, "promo_tag": "Q1 Bundle"},
                # Popular but not actually associated: lift ~1 is noise.
                {"product_id": "CABLE-01", "product_name": "USB-C Cable",
                 "co_purchase_count": 300, "margin": 3.0,
                 "confidence": 0.30, "lift": 1.02},
            ],
        }

    def test_ranks_by_expected_margin_not_raw_count(self):
        result = recommend_upsell(["LAPTOP-01"], self.mined())

        self.assertTrue(all(r["ranking_basis"] == "confidence_x_margin" for r in result))
        self.assertEqual(
            [r["product_id"] for r in result],
            ["WARRANTY-01", "DOCK-01", "MOUSE-01", "CABLE-01"],
        )
        # The mouse has the HIGHEST co-purchase count and still ranks third,
        # because 71% of a 5.00 margin is worth less than 62% of 50.00.
        mouse = next(r for r in result if r["product_id"] == "MOUSE-01")
        self.assertEqual(mouse["co_purchase_count"], 710.0)
        self.assertEqual(mouse["expected_margin"], 3.55)

    def test_expected_margin_is_confidence_times_margin(self):
        result = recommend_upsell(["LAPTOP-01"], self.mined())

        dock = next(r for r in result if r["product_id"] == "DOCK-01")
        self.assertEqual(dock["expected_margin"], 31.0)  # 0.62 * 50
        self.assertEqual(dock["score"], 31.0)  # not promoted, no boost
        self.assertEqual(dock["confidence"], 0.62)
        self.assertEqual(dock["lift"], 2.4)

    def test_promotion_boost_still_applies_on_top(self):
        result = recommend_upsell(["LAPTOP-01"], self.mined())

        warranty = result[0]
        self.assertEqual(warranty["product_id"], "WARRANTY-01")
        self.assertEqual(warranty["expected_margin"], 37.4)  # 0.44 * 85
        self.assertEqual(warranty["score"], 46.75)  # * 1.25 promotion boost

    def test_min_lift_drops_popularity_artefacts(self):
        """Lift ~1.0 means the product is just popular, not associated."""
        result = recommend_upsell(["LAPTOP-01"], self.mined(), min_lift=1.5)

        self.assertNotIn("CABLE-01", [r["product_id"] for r in result])
        self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
