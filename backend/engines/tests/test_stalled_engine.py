"""detect_stalled tests.

Every test passes a fixed ``now`` so results are fully deterministic.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stalled_engine import DEFAULT_STALE_DAYS, TERMINAL_STATUSES, detect_stalled  # noqa: E402

# A fixed "now" so tests never depend on wall-clock time.
NOW = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)


def _quote(
    id_,
    customer,
    status,
    days_ago,
    amount=None,
    name=None,
):
    """Helper to build a minimal quotation dict."""
    ts = NOW - timedelta(days=days_ago)
    return {
        "id": id_,
        "name": name or f"Q-{id_:05d}",
        "customer_name": customer,
        "status": status,
        "last_updated_at": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "amount_total": amount,
    }


class TestDetectStalled(unittest.TestCase):
    def test_stale_quote_is_flagged(self):
        """A draft quotation inactive for 10 days (threshold 7) must appear."""
        quotes = [_quote(1, "Acme Corp", "draft", days_ago=10, amount=15000.0)]

        result = detect_stalled(quotes, stale_days=7, now=NOW)

        self.assertEqual(result["total_stalled"], 1)
        self.assertEqual(result["total_active"], 1)
        row = result["stalled"][0]
        self.assertEqual(row["quotation_id"], 1)
        self.assertEqual(row["customer_name"], "Acme Corp")
        self.assertEqual(row["days_stalled"], 10)
        self.assertEqual(row["status"], "draft")
        self.assertEqual(row["amount_total"], 15000.0)

    def test_recently_active_quote_is_not_flagged(self):
        """A quote touched 3 days ago is fine against a 7-day threshold."""
        quotes = [_quote(2, "Beta Industries", "pending_approval", days_ago=3)]

        result = detect_stalled(quotes, stale_days=7, now=NOW)

        self.assertEqual(result["total_stalled"], 0)
        self.assertEqual(result["total_active"], 1)
        self.assertEqual(result["stalled"], [])

    def test_confirmed_quote_is_never_stalled(self):
        """Terminal status → excluded from active count entirely."""
        quotes = [
            _quote(3, "Gamma Ltd", "confirmed", days_ago=30),
            _quote(4, "Delta Inc", "cancelled", days_ago=30),
            _quote(5, "Epsilon SA", "invoiced", days_ago=30),
        ]

        result = detect_stalled(quotes, stale_days=7, now=NOW)

        self.assertEqual(result["total_active"], 0)
        self.assertEqual(result["total_stalled"], 0)

    def test_sorted_worst_first(self):
        """Screen 14 must show the most stuck deals at the top."""
        quotes = [
            _quote(1, "A", "draft", days_ago=8),
            _quote(2, "B", "draft", days_ago=20),   # worst
            _quote(3, "C", "draft", days_ago=15),
        ]

        result = detect_stalled(quotes, stale_days=7, now=NOW)

        self.assertEqual(result["total_stalled"], 3)
        self.assertEqual(
            [row["quotation_id"] for row in result["stalled"]],
            [2, 3, 1],  # 20, 15, 8 days — descending
        )

    def test_exact_threshold_day_is_stalled(self):
        """A quote inactive for exactly stale_days days is stalled (>=)."""
        quotes = [_quote(1, "Exact", "draft", days_ago=7)]

        result = detect_stalled(quotes, stale_days=7, now=NOW)

        self.assertEqual(result["total_stalled"], 1)

    def test_one_day_under_threshold_is_clean(self):
        quotes = [_quote(1, "Close", "draft", days_ago=6)]

        result = detect_stalled(quotes, stale_days=7, now=NOW)

        self.assertEqual(result["total_stalled"], 0)

    def test_mixed_active_and_terminal_quotes(self):
        """Three stalled, two terminal, one active — counts must all be correct."""
        quotes = [
            _quote(1, "A", "draft", days_ago=9),
            _quote(2, "B", "pending_approval", days_ago=12),
            _quote(3, "C", "sent", days_ago=3),          # active but not stalled
            _quote(4, "D", "confirmed", days_ago=30),    # terminal
            _quote(5, "E", "cancelled", days_ago=30),    # terminal
            _quote(6, "F", "draft", days_ago=8),
        ]

        result = detect_stalled(quotes, stale_days=7, now=NOW)

        self.assertEqual(result["total_active"], 4)    # 1,2,3,6 — not 4,5
        self.assertEqual(result["total_stalled"], 3)   # 1,2,6
        self.assertEqual(result["stale_days_threshold"], 7)

    def test_missing_timestamp_skips_gracefully(self):
        """A quotation with no timestamp must not crash or false-positive."""
        quotes = [
            {"id": 1, "customer_name": "No-Date Corp", "status": "draft"},
        ]

        result = detect_stalled(quotes, stale_days=7, now=NOW)

        # It is counted as active (not terminal) but not stalled (no date).
        self.assertEqual(result["total_active"], 1)
        self.assertEqual(result["total_stalled"], 0)

    def test_empty_list_returns_zeros(self):
        result = detect_stalled([], now=NOW)

        self.assertEqual(result["total_stalled"], 0)
        self.assertEqual(result["total_active"], 0)
        self.assertEqual(result["stalled"], [])

    def test_iso_string_and_epoch_timestamps_both_parse(self):
        """Timestamps arrive as ISO strings or Unix epoch — both must work."""
        ts_epoch = (NOW - timedelta(days=10)).timestamp()
        quotes = [
            # ISO string
            _quote(1, "A", "draft", days_ago=10),
            # Unix epoch float
            {
                "id": 2,
                "customer_name": "B",
                "status": "draft",
                "last_updated_at": ts_epoch,
            },
        ]

        result = detect_stalled(quotes, stale_days=7, now=NOW)

        self.assertEqual(result["total_stalled"], 2)
        # Both should report 10 days stalled.
        self.assertTrue(all(row["days_stalled"] == 10 for row in result["stalled"]))

    def test_default_stale_days_constant_is_used_when_not_given(self):
        """Calling without stale_days uses DEFAULT_STALE_DAYS."""
        quotes = [_quote(1, "X", "draft", days_ago=DEFAULT_STALE_DAYS + 1)]

        result = detect_stalled(quotes, now=NOW)

        self.assertEqual(result["total_stalled"], 1)
        self.assertEqual(result["stale_days_threshold"], DEFAULT_STALE_DAYS)

    def test_terminal_statuses_are_exported(self):
        """Person 3 can render the exclusion list without hardcoding it."""
        self.assertIn("confirmed", TERMINAL_STATUSES)
        self.assertIn("cancelled", TERMINAL_STATUSES)


if __name__ == "__main__":
    unittest.main()
