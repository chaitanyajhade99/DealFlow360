"""Blended discount risk scoring (PDF section 10).

Hybrid: a deterministic rule engine sets a policy FLOOR, and an XGBoost model
(risk_model.py) may ESCALATE above it. The final band is the worse of the two.

Why not pure ML? Three reasons, all of them from the PDF:

  * Section 10 states an exact expected outcome for its worked example. A
    learned model cannot *guarantee* that; a rule can.
  * A3 requires every approval logged "with user, timestamp, and reason".
    A softmax probability is not a reason. The rules produce the reason.
  * Section 7 requires real governance logic, not a demo prop. Rules that
    always fire on a ceiling breach are exactly that.

Why not pure rules? The rules only see "how far is each line over its own
ceiling". They cannot see that this rep is junior, that the overage sits
entirely on thin-margin Service lines, that it is quarter end, or that the
deal is ten times the usual size. The model learns those patterns from
history and catches quotes the rules would wave through.

So: rules can only raise the floor, the model can only raise it further.
Neither can lower the other. score_risk(..., use_model=False) gives the pure
rule engine, which is what the deterministic tests assert against.

Pure function layer. No DB access, no imports from models/ or api/.
Percentages are percentage POINTS (12.0 means "12 percent"), never fractions.
"""

from __future__ import annotations

try:  # package import: from backend.engines import score_risk
    from . import risk_model as _risk_model_module
except ImportError:  # flat import: tests and demo.py put this dir on sys.path
    import risk_model as _risk_model_module

# --- Tunables ------------------------------------------------------------
# Fail-closed default: a line that arrives with no category_limit_pct is
# treated as having a 0% ceiling, so it flags instead of silently passing.
# Governance systems should never let a data gap wave a discount through.
DEFAULT_CATEGORY_LIMIT_PCT = 0.0

# A single line this far over its own ceiling escalates the whole quote.
# This is what makes the PDF's worked example land on HIGH: one Service line
# 8 points over, even though the value-weighted blend is only ~1.1 points.
SINGLE_LINE_HIGH_PCT = 5.0

# Value-weighted average overage across the order. This is the "blended"
# half: many lines each a little over add up here even when no single line
# trips SINGLE_LINE_HIGH_PCT.
BLENDED_HIGH_PCT = 3.0

# The model must be at least this confident before it is allowed to escalate.
# Below this it is guessing, and a spurious escalation wastes a manager's time.
MODEL_ESCALATION_MIN_CONFIDENCE = 0.55

BAND_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
APPROVAL_CHAINS = {
    "LOW": [],
    "MEDIUM": ["Sales Manager"],
    "HIGH": ["Sales Manager", "Finance"],
}

# Column order for wireframe screen 6, "Why This Quote Was Flagged".
# (dict key -> display header). Person 3 can render the header row from this
# directly rather than hardcoding labels a second time.
FLAGGED_LINE_COLUMNS = [
    ("line", "Line"),
    ("discount_given_pct", "Discount Given"),
    ("limit_allowed_pct", "Limit Allowed"),
    ("over_by_pct", "Over By"),
]


def _as_float(value, default: float = 0.0) -> float:
    """Coerce seed/JSON data to float without exploding on None or ''."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _line_label(line: dict) -> str:
    """Display value for screen 6's 'Line' column."""
    for key in ("product_name", "name", "product_id"):
        label = line.get(key)
        if label:
            return str(label)
    if line.get("id") is not None:
        return f"Line {line['id']}"
    return "Unknown line"


def score_rules_only(lines: list[dict]) -> dict:
    """The deterministic half: every line against its own ceiling.

    Two independent rules, worse one wins:

      1. Worst single line - one line >= SINGLE_LINE_HIGH_PCT points over its
         own ceiling flags the whole quote (the PDF's Laptop/Setup Service
         example: the Service line alone forces review).
      2. Blended overage - line-value-weighted average overage across the
         order, so "2 over here, 3 over there, 2 over there" cannot slip
         through unnoticed.

    Neither alone is enough. In the PDF's own example the blend is only 1.14
    points -- the large clean Laptop line dilutes the bad Service line -- so
    rule 2 alone would pass it. And rule 1 alone is just max(), which the
    PDF's "why blended?" paragraph says is insufficient.

    Args:
        lines: QuotationLine dicts. Reads qty, unit_price, discount_pct,
            category_limit_pct, and for labelling product_name / product_id /
            id / category. A missing category_limit_pct is treated as
            DEFAULT_CATEGORY_LIMIT_PCT (fail-closed).

    Returns:
        {"risk", "flagged_lines", "blended_score_pct", "worst_line_over_pct",
         "total_line_value"}. Line value is GROSS list value (qty * unit_price),
        the revenue exposed at that discount, not the post-discount net.
    """
    flagged: list[dict] = []
    total_value = 0.0
    weighted_overage = 0.0
    overages: list[float] = []
    worst_overage = 0.0

    for line in lines or []:
        discount = _as_float(line.get("discount_pct"))
        limit = _as_float(line.get("category_limit_pct"), DEFAULT_CATEGORY_LIMIT_PCT)
        qty = _as_float(line.get("qty"))
        unit_price = _as_float(line.get("unit_price"))

        line_value = max(qty * unit_price, 0.0)
        # Only overages count. A line under its ceiling does not earn credit
        # that offsets another line's violation.
        overage = max(discount - limit, 0.0)

        total_value += line_value
        weighted_overage += overage * line_value
        overages.append(overage)
        worst_overage = max(worst_overage, overage)

        if overage > 0:
            flagged.append(
                {
                    "line": _line_label(line),
                    "discount_given_pct": round(discount, 2),
                    "limit_allowed_pct": round(limit, 2),
                    "over_by_pct": round(overage, 2),
                    "line_id": line.get("id"),
                    "product_id": line.get("product_id"),
                    "category": line.get("category"),
                    "line_value": round(line_value, 2),
                }
            )

    if total_value > 0:
        blended = weighted_overage / total_value
    elif overages:
        # Every line is zero-value (qty 0, or a free line). Weighting is
        # meaningless here, so fall back to a plain mean rather than 0.0,
        # which would hide real overages.
        blended = sum(overages) / len(overages)
    else:
        blended = 0.0

    if worst_overage >= SINGLE_LINE_HIGH_PCT or blended >= BLENDED_HIGH_PCT:
        risk = "HIGH"
    elif worst_overage > 0:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    flagged.sort(key=lambda row: row["over_by_pct"], reverse=True)

    return {
        "risk": risk,
        "flagged_lines": flagged,
        "blended_score_pct": round(blended, 2),
        "worst_line_over_pct": round(worst_overage, 2),
        "total_line_value": round(total_value, 2),
    }


def _build_reason(rule_result: dict, rule_risk: str, model: dict | None,
                  final_risk: str, escalated: bool) -> str:
    """Plain-language justification for the audit trail (PDF A3)."""
    flagged = rule_result["flagged_lines"]
    if flagged:
        worst = flagged[0]
        parts = [
            f"{worst['line']} discounted {worst['discount_given_pct']}% against a "
            f"{worst['limit_allowed_pct']}% ceiling ({worst['over_by_pct']} pts over)"
        ]
        if len(flagged) > 1:
            parts.append(f"{len(flagged)} lines over their ceiling")
        parts.append(f"blended overage {rule_result['blended_score_pct']} pts")
        reason = "Policy rules: " + "; ".join(parts) + "."
    else:
        reason = "Policy rules: every line within its category ceiling."

    if escalated and model:
        reason += (
            f" Risk model escalated {rule_risk} -> {final_risk} "
            f"(confidence {model['confidence']:.2f}) on contextual patterns "
            f"beyond line-level ceilings."
        )
    elif model:
        reason += f" Risk model agreed at or below the rule band ({model['risk_band']})."
    return reason


def score_risk(
    lines: list[dict],
    *,
    customer_tier: str | None = None,
    rep_avg_discount_pct: float | None = None,
    is_quarter_end: bool = False,
    seniority: int | None = None,
    use_model: bool = True,
) -> dict:
    """Score a quotation's discount risk and say which lines broke their ceiling.

    Runs the deterministic rules, then lets the trained XGBoost model escalate
    the band if it is confident the quote is riskier than the rules can see.
    The model can never LOWER the band.

    Args:
        lines: QuotationLine dicts (see score_rules_only).
        customer_tier: keyword-only. "Bronze" | "Silver" | "Gold". Model
            context; omit if unknown and the model treats it as missing.
        rep_avg_discount_pct: keyword-only. The rep's historical average
            discount, for the "is this unusual for them" feature.
        is_quarter_end: keyword-only. Quarter-end quotes discount harder.
        seniority: keyword-only. 0 junior / 1 mid / 2 principal.
        use_model: keyword-only. False runs the pure rule engine -- use it
            when you need fully deterministic behaviour (tests, or a demo
            where the artifact may not be trained).

    Returns:
        {
          "blended_risk": "LOW" | "MEDIUM" | "HIGH",   # API_CONTRACT key
          "flagged_lines": [ ... ],                    # API_CONTRACT key
          # --- additive, beyond the contract; safe to ignore ---
          "blended_score_pct": float,   # value-weighted avg overage, 2dp
          "worst_line_over_pct": float, # single largest overage, 2dp
          "total_line_value": float,
          "approval_chain": list[str],  # [] | ["Sales Manager"] | [..., "Finance"]
          "reason": str,                # audit-trail justification (PDF A3)
          "rule_risk": str,             # band from rules alone
          "model_risk": str | None,     # band the model predicted
          "model_confidence": float | None,
          "model_probabilities": dict | None,
          "model_available": bool,      # False when no artifact is trained
          "escalated_by_model": bool,
        }

        Each flagged_lines entry carries the four screen-6 columns (see
        FLAGGED_LINE_COLUMNS) plus line_id / product_id / category /
        line_value for linking. Sorted worst overage first.

    Notes:
        - With no trained artifact in data/, model_available is False and the
          result is exactly the rule engine's. A fresh clone never crashes.
        - The model only escalates above MODEL_ESCALATION_MIN_CONFIDENCE;
          below that it is guessing and a manager's time is worth more.
    """
    rule_result = score_rules_only(lines)
    rule_risk = rule_result["risk"]

    model_prediction = None
    model_available = False

    if use_model and lines:
        model = _risk_model_module.get_default_model()
        if model is not None:
            model_available = True
            try:
                features = _risk_model_module.extract_features(
                    lines,
                    customer_tier=customer_tier,
                    rep_avg_discount_pct=rep_avg_discount_pct,
                    is_quarter_end=is_quarter_end,
                    seniority=seniority,
                )
                model_prediction = model.predict(features)
            except Exception:
                # Inference must never break quoting. Fall back to rules.
                model_prediction = None
                model_available = False

    final_risk = rule_risk
    escalated = False
    if (
        model_prediction
        and model_prediction["confidence"] >= MODEL_ESCALATION_MIN_CONFIDENCE
        and BAND_ORDER[model_prediction["risk_band"]] > BAND_ORDER[rule_risk]
    ):
        final_risk = model_prediction["risk_band"]
        escalated = True

    return {
        "blended_risk": final_risk,
        "flagged_lines": rule_result["flagged_lines"],
        "blended_score_pct": rule_result["blended_score_pct"],
        "worst_line_over_pct": rule_result["worst_line_over_pct"],
        "total_line_value": rule_result["total_line_value"],
        "approval_chain": APPROVAL_CHAINS[final_risk],
        "reason": _build_reason(
            rule_result, rule_risk, model_prediction, final_risk, escalated
        ),
        "rule_risk": rule_risk,
        "model_risk": model_prediction["risk_band"] if model_prediction else None,
        "model_confidence": model_prediction["confidence"] if model_prediction else None,
        "model_probabilities": (
            model_prediction["probabilities"] if model_prediction else None
        ),
        "model_available": model_available,
        "escalated_by_model": escalated,
    }
