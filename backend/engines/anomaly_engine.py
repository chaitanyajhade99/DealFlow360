"""Discount anomaly detection (PDF B9, wireframe screen 14).

Pure function layer. No DB access, no imports from models/ or api/.
Person 1 calls detect_anomalies() from GET /deal-health.
"""

from __future__ import annotations

import statistics

# A discount more than this many standard deviations above the rep's own
# historical mean is "well above their average" (PDF B9).
Z_THRESHOLD = 2.0

# When a rep's history has zero variance the true z-score is infinite.
# float('inf') is not valid JSON, so report this sentinel instead: still
# sortable, still obviously off-the-scale on screen 14.
Z_SCORE_CAP = 99.0


def _as_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def detect_anomalies(rep_discount_history: list[float], current_discount: float) -> dict:
    """Flag a discount that is far above this rep's own historical pattern.

    Anomaly when current_discount > mean(history) + Z_THRESHOLD * stddev(history).
    The baseline is per-rep on purpose: 18% is routine for a rep who lives in
    enterprise deals and alarming for one who never exceeds 8%.

    Sample standard deviation (n-1) is used, since a rep's past quotes are a
    sample of their behaviour rather than a complete population.

    Args:
        rep_discount_history: this rep's past discount percentages, in points
            (e.g. [5.0, 6.0, 5.5]). Order does not matter. Unparseable entries
            are dropped.
        current_discount: the discount on the quote under review, in points.

    Returns:
        {
          "is_anomaly": bool,     # API_CONTRACT key
          "z_score": float,       # API_CONTRACT key, 2dp
          # --- additive, beyond the contract; feeds screen 14's card ---
          "mean": float,          # rep's historical average, 2dp
          "stddev": float,        # 2dp
          "threshold": float,     # mean + Z_THRESHOLD * stddev, 2dp
          "current_discount": float,
          "sample_size": int,     # usable history entries
        }

    Notes:
        - Fewer than 2 history entries: there is no baseline to deviate from,
          so is_anomaly is False and z_score 0.0. A brand-new rep is not an
          anomaly. sample_size lets screen 14 say "not enough history yet"
          instead of implying the quote is clean.
        - Zero-variance history (rep always gave exactly 10%): any strictly
          higher discount is an anomaly and reports z_score = Z_SCORE_CAP.
          A discount at or below the mean is not.
    """
    history = [_as_float(value, None) for value in (rep_discount_history or [])]
    history = [value for value in history if value is not None]
    current = _as_float(current_discount)

    if len(history) < 2:
        mean = round(history[0], 2) if history else 0.0
        return {
            "is_anomaly": False,
            "z_score": 0.0,
            "mean": mean,
            "stddev": 0.0,
            "threshold": mean,
            "current_discount": round(current, 2),
            "sample_size": len(history),
        }

    mean = statistics.fmean(history)
    stddev = statistics.stdev(history)  # sample stddev, n-1

    if stddev == 0:
        is_anomaly = current > mean
        z_score = Z_SCORE_CAP if is_anomaly else 0.0
        threshold = mean
    else:
        threshold = mean + Z_THRESHOLD * stddev
        is_anomaly = current > threshold
        z_score = (current - mean) / stddev

    return {
        "is_anomaly": is_anomaly,
        "z_score": round(z_score, 2),
        "mean": round(mean, 2),
        "stddev": round(stddev, 2),
        "threshold": round(threshold, 2),
        "current_discount": round(current, 2),
        "sample_size": len(history),
    }
