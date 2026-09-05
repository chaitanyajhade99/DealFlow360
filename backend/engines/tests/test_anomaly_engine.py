"""detect_anomalies tests."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anomaly_engine import Z_SCORE_CAP, detect_anomalies  # noqa: E402

# A rep who normally discounts 5-7 percent.
REP_HISTORY = [5.0, 6.0, 5.0, 7.0, 6.0, 5.0]  # mean 5.67, sample sd 0.82


class TestDetectAnomalies(unittest.TestCase):
    def test_discount_far_above_rep_baseline_is_flagged(self):
        result = detect_anomalies(REP_HISTORY, 25.0)

        self.assertTrue(result["is_anomaly"])
        self.assertEqual(result["mean"], 5.67)
        self.assertEqual(result["stddev"], 0.82)
        self.assertEqual(result["threshold"], 7.3)  # 5.67 + 2 * 0.82
        self.assertEqual(result["z_score"], 23.68)
        self.assertEqual(result["sample_size"], 6)

    def test_above_average_but_within_two_sigma_is_not_flagged(self):
        """7.0 beats this rep's mean but sits under the 7.3 threshold."""
        result = detect_anomalies(REP_HISTORY, 7.0)

        self.assertFalse(result["is_anomaly"])
        self.assertGreater(result["current_discount"], result["mean"])
        self.assertEqual(result["z_score"], 1.63)

    def test_zero_variance_history_reports_capped_score(self):
        """A rep who always gave exactly 10 percent: true z is infinite.

        float('inf') is not valid JSON, so the cap is reported instead.
        """
        result = detect_anomalies([10.0, 10.0, 10.0], 12.0)

        self.assertTrue(result["is_anomaly"])
        self.assertEqual(result["z_score"], Z_SCORE_CAP)
        self.assertEqual(result["stddev"], 0.0)

    def test_zero_variance_history_at_or_below_mean_is_clean(self):
        result = detect_anomalies([10.0, 10.0, 10.0], 10.0)

        self.assertFalse(result["is_anomaly"])
        self.assertEqual(result["z_score"], 0.0)

    def test_no_history_is_never_an_anomaly(self):
        """A brand-new rep has no baseline to deviate from."""
        result = detect_anomalies([], 40.0)

        self.assertFalse(result["is_anomaly"])
        self.assertEqual(result["z_score"], 0.0)
        self.assertEqual(result["sample_size"], 0)

    def test_single_history_entry_has_no_baseline(self):
        result = detect_anomalies([5.0], 40.0)

        self.assertFalse(result["is_anomaly"])
        self.assertEqual(result["sample_size"], 1)
        self.assertEqual(result["mean"], 5.0)


if __name__ == "__main__":
    unittest.main()
