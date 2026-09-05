"""End-to-end tests through the FastAPI stack.

These go through real request validation and response serialization, so they
catch what the engine unit tests cannot: a response_model that silently drops
a key, a Decimal that fails to coerce, a 422 on a payload the database would
actually produce.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

try:
    from fastapi.testclient import TestClient
    from backend.engines.api import app
    CLIENT = TestClient(app)
    AVAILABLE = True
except Exception:  # pragma: no cover - fastapi not installed
    AVAILABLE = False
    CLIENT = None


PDF_EXAMPLE = {
    "lines": [
        {"product_name": "Laptop", "category": "Hardware", "qty": 10,
         "unit_price": 1200.0, "discount_pct": 12.0, "category_limit_pct": 15.0},
        # "Services" plural, as the database actually stores it.
        {"product_name": "Setup Service", "category": "Services", "qty": 1,
         "unit_price": 2000.0, "discount_pct": 18.0, "category_limit_pct": 10.0},
    ],
    "customer_tier": "Gold",
}


@unittest.skipUnless(AVAILABLE, "fastapi not installed")
class TestRiskRoute(unittest.TestCase):
    def test_pdf_example_scores_high(self):
        response = CLIENT.post("/engines/risk/score", json=PDF_EXAMPLE)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["blended_risk"], "HIGH")
        self.assertEqual(body["total_line_value"], 14000.0)
        self.assertEqual(body["approval_chain"], ["Sales Manager", "Finance"])

    def test_response_model_keeps_every_additive_key(self):
        # A response_model that forgot a field would drop it silently, which is
        # exactly the kind of break the unit tests cannot see.
        body = CLIENT.post("/engines/risk/score", json=PDF_EXAMPLE).json()
        for key in ("blended_risk", "flagged_lines", "blended_score_pct",
                    "worst_line_over_pct", "total_line_value", "approval_chain",
                    "reason", "rule_risk", "model_risk", "model_confidence",
                    "model_probabilities", "model_available",
                    "escalated_by_model"):
            self.assertIn(key, body, f"response_model dropped {key}")

    def test_flagged_line_carries_screen6_columns(self):
        body = CLIENT.post("/engines/risk/score", json=PDF_EXAMPLE).json()
        self.assertEqual(len(body["flagged_lines"]), 1)
        row = body["flagged_lines"][0]
        self.assertEqual(row["line"], "Setup Service")
        self.assertEqual(row["discount_given_pct"], 18.0)
        self.assertEqual(row["limit_allowed_pct"], 10.0)
        self.assertEqual(row["over_by_pct"], 8.0)

    def test_tier_case_is_folded(self):
        payload = dict(PDF_EXAMPLE, customer_tier="gold")
        self.assertEqual(
            CLIENT.post("/engines/risk/score", json=payload).status_code, 200)

    def test_use_model_false_is_deterministic(self):
        payload = dict(PDF_EXAMPLE, use_model=False)
        body = CLIENT.post("/engines/risk/score", json=payload).json()
        self.assertEqual(body["blended_risk"], body["rule_risk"])
        self.assertFalse(body["escalated_by_model"])

    def test_quarter_end_derived_from_quote_date(self):
        # 2026-09-30 is the last day of Q3; 2026-08-01 is not near a boundary.
        near = dict(PDF_EXAMPLE, quote_date="2026-09-30")
        far = dict(PDF_EXAMPLE, quote_date="2026-08-01")
        self.assertEqual(CLIENT.post("/engines/risk/score", json=near).status_code, 200)
        self.assertEqual(CLIENT.post("/engines/risk/score", json=far).status_code, 200)

    def test_empty_lines_rejected(self):
        response = CLIENT.post("/engines/risk/score", json={"lines": []})
        self.assertEqual(response.status_code, 422)

    def test_missing_category_limit_fails_closed(self):
        payload = {"lines": [{"product_name": "Mystery", "qty": 1,
                              "unit_price": 100.0, "discount_pct": 5.0}]}
        body = CLIENT.post("/engines/risk/score", json=payload).json()
        # No ceiling given -> scored against 0%, so it flags rather than passing.
        self.assertEqual(len(body["flagged_lines"]), 1)

    def test_seniority_out_of_range_rejected(self):
        payload = dict(PDF_EXAMPLE, seniority=7)
        self.assertEqual(
            CLIENT.post("/engines/risk/score", json=payload).status_code, 422)


@unittest.skipUnless(AVAILABLE, "fastapi not installed")
class TestFulfillmentRoute(unittest.TestCase):
    WAREHOUSES = [
        {"id": 1, "name": "Main Warehouse",
         "stock": [{"product_id": "LAPTOP-PRO-14", "qty": 50}]},
        {"id": 2, "name": "East Depot",
         "stock": [{"product_id": "LAPTOP-PRO-14", "qty": 30}]},
    ]

    def _post(self, qty):
        return CLIENT.post("/engines/fulfillment/split", json={
            "product_id": "LAPTOP-PRO-14", "qty": qty,
            "warehouses": self.WAREHOUSES}).json()

    def test_single_warehouse_covers_order(self):
        rows = self._post(20)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["qty"], 20)

    def test_splits_deepest_first(self):
        self.assertEqual([r["qty"] for r in self._post(70)], [50, 20])

    def test_backorder_row_present_and_flagged(self):
        rows = self._post(100)
        backorder = [r for r in rows if r["is_backorder"]]
        self.assertEqual(len(backorder), 1)
        self.assertEqual(backorder[0]["qty"], 20)
        self.assertIsNone(backorder[0]["warehouse_id"])

    def test_is_backorder_on_every_row(self):
        self.assertTrue(all("is_backorder" in r for r in self._post(100)))

    def test_shorthand_stock_map_accepted(self):
        rows = CLIENT.post("/engines/fulfillment/split", json={
            "product_id": "P1", "qty": 5,
            "warehouses": [{"id": 9, "name": "Shorthand", "stock": {"P1": 10}}]
        }).json()
        self.assertEqual(rows[0]["qty"], 5)


@unittest.skipUnless(AVAILABLE, "fastapi not installed")
class TestAnomalyRoute(unittest.TestCase):
    def test_detects_outlier(self):
        body = CLIENT.post("/engines/anomalies/detect", json={
            "rep_discount_history": [5.0, 6.0, 5.0, 7.0, 6.0, 5.0],
            "current_discount": 18.0}).json()
        self.assertTrue(body["is_anomaly"])
        self.assertEqual(body["sample_size"], 6)

    def test_new_rep_is_not_an_anomaly(self):
        body = CLIENT.post("/engines/anomalies/detect", json={
            "rep_discount_history": [], "current_discount": 18.0}).json()
        self.assertFalse(body["is_anomaly"])
        self.assertEqual(body["sample_size"], 0)

    def test_z_score_is_json_finite(self):
        # Zero-variance history would give an infinite true z, which is not
        # valid JSON -- the engine caps it, and this asserts it survives
        # serialization rather than emitting bare Infinity.
        raw = CLIENT.post("/engines/anomalies/detect", json={
            "rep_discount_history": [10.0, 10.0, 10.0],
            "current_discount": 25.0})
        self.assertNotIn("Infinity", raw.text)
        self.assertTrue(raw.json()["is_anomaly"])


@unittest.skipUnless(AVAILABLE, "fastapi not installed")
class TestUpsellRoute(unittest.TestCase):
    DATA = {"LAPTOP-01": [
        {"product_id": "DOCK-01", "product_name": "Docking Station",
         "co_purchase_count": 40, "margin": 50.0},
        {"product_id": "MOUSE-01", "product_name": "Wireless Mouse",
         "co_purchase_count": 90, "margin": 5.0},
    ]}

    def test_ranks_by_expected_margin_not_count(self):
        rows = CLIENT.post("/engines/upsell/recommend", json={
            "cart_items": ["LAPTOP-01"], "co_occurrence_data": self.DATA}).json()
        self.assertEqual(rows[0]["product_id"], "DOCK-01")

    def test_key_aliases_survive_the_loose_dict(self):
        # margin_impact / co_occurrence are alias spellings the engine accepts;
        # a strict pydantic model would have thrown them away.
        rows = CLIENT.post("/engines/upsell/recommend", json={
            "cart_items": ["LAPTOP-01"],
            "co_occurrence_data": {"LAPTOP-01": [
                {"product_id": "X-01", "co_occurrence": 10, "margin_impact": 99.0}]}
        }).json()
        self.assertEqual(rows[0]["margin_delta"], 99.0)
        self.assertEqual(rows[0]["co_purchase_count"], 10.0)

    def test_cart_item_never_suggested_back(self):
        rows = CLIENT.post("/engines/upsell/recommend", json={
            "cart_items": ["LAPTOP-01", "DOCK-01"],
            "co_occurrence_data": self.DATA}).json()
        self.assertNotIn("DOCK-01", [r["product_id"] for r in rows])

    def test_min_margin_filters(self):
        rows = CLIENT.post("/engines/upsell/recommend", json={
            "cart_items": ["LAPTOP-01"], "co_occurrence_data": self.DATA,
            "min_margin": 20.0}).json()
        self.assertEqual([r["product_id"] for r in rows], ["DOCK-01"])

    def test_limit_caps_results(self):
        rows = CLIENT.post("/engines/upsell/recommend", json={
            "cart_items": ["LAPTOP-01"], "co_occurrence_data": self.DATA,
            "limit": 1}).json()
        self.assertEqual(len(rows), 1)


@unittest.skipUnless(AVAILABLE, "fastapi not installed")
class TestHealthAndConfig(unittest.TestCase):
    def test_health_reports_model_state(self):
        body = CLIENT.get("/engines/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("model_available", body)
        self.assertEqual(len(body["feature_names"]), 13)

    def test_config_exposes_tunables(self):
        body = CLIENT.get("/engines/config").json()
        self.assertEqual(body["single_line_high_pct"], 5.0)
        self.assertEqual(body["blended_high_pct"], 3.0)
        self.assertEqual(body["z_threshold"], 2.0)

    def test_openapi_schema_builds(self):
        # A bad response_model surfaces here rather than at request time.
        response = CLIENT.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/engines/risk/score", response.json()["paths"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
