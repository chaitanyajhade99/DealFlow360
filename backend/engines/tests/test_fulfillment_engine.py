"""split_warehouse tests."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fulfillment_engine import split_warehouse  # noqa: E402


def warehouses():
    """Main Warehouse is deeper but pricier per unit; East Depot is shallower."""
    return [
        {
            "id": "WH-EAST",
            "name": "East Depot",
            "stock": [{"product_id": "LAPTOP-01", "qty": 30}],
            "shipping_cost_per_unit": 3.0,
            "shipment_fixed_cost": 20.0,
        },
        {
            "id": "WH-MAIN",
            "name": "Main Warehouse",
            "stock": [{"product_id": "LAPTOP-01", "qty": 50}],
            "shipping_cost_per_unit": 2.0,
            "shipment_fixed_cost": 25.0,
        },
    ]


class TestSplitWarehouse(unittest.TestCase):
    def test_single_warehouse_covers_order_in_one_shipment(self):
        """Deepest warehouse first, so no split when one can cover the qty."""
        result = split_warehouse("LAPTOP-01", 20, warehouses())

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["warehouse_id"], "WH-MAIN")
        self.assertEqual(result[0]["warehouse"], "Main Warehouse")
        self.assertEqual(result[0]["qty"], 20)
        self.assertEqual(result[0]["est_shipments"], 1)
        self.assertEqual(result[0]["cost"], 65.0)  # 25 fixed + 2 * 20
        self.assertFalse(result[0]["is_backorder"])

    def test_splits_across_two_warehouses_when_one_cannot_cover(self):
        result = split_warehouse("LAPTOP-01", 70, warehouses())

        self.assertEqual(len(result), 2)
        self.assertEqual(
            [(row["warehouse"], row["qty"]) for row in result],
            [("Main Warehouse", 50), ("East Depot", 20)],
        )
        self.assertEqual(result[0]["cost"], 125.0)  # 25 + 2 * 50
        self.assertEqual(result[1]["cost"], 80.0)  # 20 + 3 * 20
        self.assertEqual(sum(row["est_shipments"] for row in result), 2)
        self.assertFalse(any(row["is_backorder"] for row in result))

    def test_shortfall_becomes_a_backorder_row(self):
        """Drives B6's 'Consolidate Remaining Backorder' prompt."""
        result = split_warehouse("LAPTOP-01", 100, warehouses())

        self.assertEqual(len(result), 3)
        backorder = result[-1]
        self.assertTrue(backorder["is_backorder"])
        self.assertIsNone(backorder["warehouse_id"])
        self.assertEqual(backorder["qty"], 20)  # 100 needed, 80 on hand
        self.assertEqual(backorder["est_shipments"], 0)
        # Person 1 persists only the real allocations.
        real = [row for row in result if not row["is_backorder"]]
        self.assertEqual(sum(row["qty"] for row in real), 80)

    def test_no_stock_anywhere_is_all_backorder(self):
        result = split_warehouse("GHOST-01", 5, warehouses())

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["is_backorder"])
        self.assertEqual(result[0]["qty"], 5)

    def test_zero_or_negative_qty_allocates_nothing(self):
        self.assertEqual(split_warehouse("LAPTOP-01", 0, warehouses()), [])
        self.assertEqual(split_warehouse("LAPTOP-01", -3, warehouses()), [])

    def test_accepts_dict_shaped_stock(self):
        """Seed data sometimes uses {product_id: qty} instead of a list."""
        result = split_warehouse(
            "LAPTOP-01",
            10,
            [{"id": "WH-MAIN", "name": "Main Warehouse", "stock": {"LAPTOP-01": 40}}],
        )

        self.assertEqual(result[0]["qty"], 10)
        self.assertEqual(result[0]["cost"], 0.0)  # no shipping config -> free

    def test_equal_stock_breaks_tie_on_cheaper_shipping(self):
        tied = [
            {"id": "WH-B", "name": "B", "stock": {"P1": 10},
             "shipping_cost_per_unit": 5.0},
            {"id": "WH-A", "name": "A", "stock": {"P1": 10},
             "shipping_cost_per_unit": 1.0},
        ]

        result = split_warehouse("P1", 5, tied)

        self.assertEqual(result[0]["warehouse_id"], "WH-A")


if __name__ == "__main__":
    unittest.main()
