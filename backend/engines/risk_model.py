"""XGBoost discount-risk model: feature extraction, training, inference.

Loaded lazily by risk_engine.score_risk(), which combines this model's
prediction with the deterministic rule floor. See risk_engine for why the
rules stay in charge of the final escalation decision.

The model artifact lives in data/risk_model.json and is produced by train.py.
If it is missing, get_default_model() returns None and score_risk() runs
rules-only -- a fresh clone with no trained artifact must never crash.
"""

from __future__ import annotations

import json
import math
import os

# Feature order is part of the artifact contract. Training and inference MUST
# build the vector in exactly this order, so it is defined once, here.
FEATURE_NAMES = [
    "blended_overage_pct",      # value-weighted avg overage (the rule's own score)
    "worst_line_overage_pct",   # largest single-line overage
    "n_lines",
    "n_flagged_lines",
    "flagged_value_share",      # fraction of order value sitting on over-limit lines
    "log_total_value",          # log1p, so 5k and 500k deals are comparable
    "thin_margin_value_share",  # Service + Subscription share of order value
    "tier_ordinal",             # Bronze 0, Silver 1, Gold 2
    "avg_discount_pct",         # value-weighted
    "max_discount_pct",
    "seniority",                # 0 junior, 1 mid, 2 principal
    "is_quarter_end",
    "discount_vs_rep_baseline", # this quote's avg discount minus the rep's own
]

LABEL_TO_BAND = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
BAND_TO_LABEL = {band: label for label, band in LABEL_TO_BAND.items()}

# Compared against _normalise_category(), so both the engine's own "Service"
# and the database's "Services" land on the same bucket. See that function.
THIN_MARGIN_CATEGORIES = {"service", "subscription"}
TIER_ORDINAL = {"Bronze": 0, "Silver": 1, "Gold": 2}

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MODEL_PATH = os.path.join(_DATA_DIR, "risk_model.json")
METADATA_PATH = os.path.join(_DATA_DIR, "risk_model_meta.json")

_MODEL_CACHE: dict = {}


def _as_float(value, default=0.0):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalise_category(value) -> str:
    """Fold a category label to a stable key for THIN_MARGIN_CATEGORIES.

    The engines were written against "Service"/"Subscription"; the database
    stores "Services"/"Subscription". A plain set membership test therefore
    missed every Services line and silently zeroed thin_margin_value_share --
    no error, just a dead feature on real data. Case and a trailing plural are
    both folded away so either spelling scores identically.
    """
    if not value:
        return ""
    key = str(value).strip().lower()
    return key[:-1] if key.endswith("s") else key


def extract_features(
    lines: list[dict],
    customer_tier: str | None = None,
    rep_avg_discount_pct: float | None = None,
    is_quarter_end: bool = False,
    seniority: int | None = None,
) -> dict:
    """Turn a quotation into the model's feature dict.

    Shared by training and inference so the two can never drift apart.

    Unknown context (no tier on the quote, a rep with no history) becomes NaN
    rather than a guessed zero. XGBoost handles missing values natively by
    learning a default branch direction at each split, so a quote with partial
    context still scores sensibly instead of being told a confident lie.

    Args:
        lines: QuotationLine dicts, same shape score_risk() takes.
        customer_tier: "Bronze" | "Silver" | "Gold", or None if unknown.
        rep_avg_discount_pct: the rep's historical average discount, or None.
        is_quarter_end: whether the quote lands in the last weeks of a quarter.
        seniority: 0/1/2, or None if unknown.

    Returns:
        {feature_name: float} covering exactly FEATURE_NAMES.
    """
    nan = float("nan")
    total_value = 0.0
    weighted_overage = 0.0
    weighted_discount = 0.0
    thin_value = 0.0
    flagged_value = 0.0
    worst_overage = 0.0
    max_discount = 0.0
    n_flagged = 0

    for line in lines or []:
        discount = _as_float(line.get("discount_pct"))
        limit = _as_float(line.get("category_limit_pct"))
        value = max(_as_float(line.get("qty")) * _as_float(line.get("unit_price")), 0.0)
        overage = max(discount - limit, 0.0)

        total_value += value
        weighted_overage += overage * value
        weighted_discount += discount * value
        if _normalise_category(line.get("category")) in THIN_MARGIN_CATEGORIES:
            thin_value += value
        if overage > 0:
            n_flagged += 1
            flagged_value += value
        worst_overage = max(worst_overage, overage)
        max_discount = max(max_discount, discount)

    n_lines = len(lines or [])
    if total_value > 0:
        blended = weighted_overage / total_value
        avg_discount = weighted_discount / total_value
        thin_share = thin_value / total_value
        flagged_share = flagged_value / total_value
    else:
        # Zero-value order: fall back to unweighted means so the signal is not
        # silently zeroed out.
        overages = [
            max(_as_float(l.get("discount_pct")) - _as_float(l.get("category_limit_pct")), 0.0)
            for l in (lines or [])
        ]
        discounts = [_as_float(l.get("discount_pct")) for l in (lines or [])]
        blended = sum(overages) / len(overages) if overages else 0.0
        avg_discount = sum(discounts) / len(discounts) if discounts else 0.0
        thin_share = 0.0
        flagged_share = 0.0

    tier_ordinal = TIER_ORDINAL.get(customer_tier, nan) if customer_tier else nan
    seniority_value = float(seniority) if seniority is not None else nan
    if rep_avg_discount_pct is None:
        discount_vs_baseline = nan
    else:
        discount_vs_baseline = avg_discount - _as_float(rep_avg_discount_pct)

    return {
        "blended_overage_pct": blended,
        "worst_line_overage_pct": worst_overage,
        "n_lines": float(n_lines),
        "n_flagged_lines": float(n_flagged),
        "flagged_value_share": flagged_share,
        "log_total_value": math.log1p(max(total_value, 0.0)),
        "thin_margin_value_share": thin_share,
        "tier_ordinal": float(tier_ordinal),
        "avg_discount_pct": avg_discount,
        "max_discount_pct": max_discount,
        "seniority": seniority_value,
        "is_quarter_end": 1.0 if is_quarter_end else 0.0,
        "discount_vs_rep_baseline": discount_vs_baseline,
    }


def features_to_vector(features: dict) -> list[float]:
    """Flatten a feature dict into FEATURE_NAMES order."""
    return [float(features.get(name, float("nan"))) for name in FEATURE_NAMES]


class RiskModel:
    """Thin wrapper over a trained XGBoost booster.

    Holds the feature order alongside the booster so a stale artifact cannot
    be silently fed a mismatched vector.
    """

    def __init__(self, booster, feature_names: list[str], metadata: dict | None = None):
        self.booster = booster
        self.feature_names = feature_names
        self.metadata = metadata or {}

    def predict(self, features: dict) -> dict:
        """Score one quotation.

        Args:
            features: output of extract_features().

        Returns:
            {
              "risk_label": int,          # 0 LOW / 1 MEDIUM / 2 HIGH
              "risk_band": str,
              "confidence": float,        # probability of the predicted band
              "probabilities": {"LOW": float, "MEDIUM": float, "HIGH": float},
            }
        """
        import numpy as np
        import xgboost as xgb

        vector = np.array([features_to_vector(features)], dtype=np.float32)
        matrix = xgb.DMatrix(vector, feature_names=self.feature_names)
        probabilities = self.booster.predict(matrix)[0]

        label = int(max(range(len(probabilities)), key=lambda i: probabilities[i]))
        return {
            "risk_label": label,
            "risk_band": LABEL_TO_BAND.get(label, "LOW"),
            "confidence": round(float(probabilities[label]), 4),
            "probabilities": {
                LABEL_TO_BAND.get(i, str(i)): round(float(p), 4)
                for i, p in enumerate(probabilities)
            },
        }

    def feature_importance(self, top_n: int = 10) -> list[tuple[str, float]]:
        """Gain-based importance, most important first. Useful for the demo."""
        scores = self.booster.get_score(importance_type="gain")
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        return [(name, round(gain, 3)) for name, gain in ranked[:top_n]]

    @classmethod
    def load(cls, model_path: str = MODEL_PATH, metadata_path: str = METADATA_PATH):
        """Load a trained artifact, or return None if it has not been trained yet."""
        if not os.path.exists(model_path):
            return None
        try:
            import xgboost as xgb

            booster = xgb.Booster()
            booster.load_model(model_path)
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as handle:
                    metadata = json.load(handle)
            feature_names = metadata.get("feature_names", FEATURE_NAMES)
            return cls(booster, feature_names, metadata)
        except Exception:
            # A corrupt or version-mismatched artifact must degrade to
            # rules-only, never take down a request.
            return None


def get_default_model(refresh: bool = False):
    """Process-wide cached model. Returns None when no artifact exists.

    Cached because score_risk() is called per request and reading the booster
    off disk every time would be wasteful.
    """
    if refresh:
        _MODEL_CACHE.clear()
    if "model" not in _MODEL_CACHE:
        _MODEL_CACHE["model"] = RiskModel.load()
    return _MODEL_CACHE["model"]


def train_risk_model(
    quotes: list[dict],
    model_path: str = MODEL_PATH,
    metadata_path: str = METADATA_PATH,
    test_size: float = 0.2,
    seed: int = 42,
    num_boost_round: int = 220,
) -> dict:
    """Train the risk model on generated quotation history and save the artifact.

    Args:
        quotes: output of synthetic_data.generate_quotation_history().
        model_path / metadata_path: where to write the artifact.
        test_size: held-out fraction for honest metrics.
        seed: RNG seed for the split and the booster.
        num_boost_round: boosting iterations.

    Returns:
        {"accuracy", "macro_f1", "n_train", "n_test", "class_distribution",
         "feature_importance", "report", "model_path"}
    """
    import numpy as np
    import xgboost as xgb
    from sklearn.metrics import accuracy_score, classification_report, f1_score
    from sklearn.model_selection import train_test_split

    rows = []
    labels = []
    for quote in quotes:
        features = extract_features(
            quote["lines"],
            customer_tier=quote.get("customer_tier"),
            rep_avg_discount_pct=quote.get("rep_avg_discount_pct"),
            is_quarter_end=quote.get("is_quarter_end", False),
            seniority=quote.get("seniority"),
        )
        rows.append(features_to_vector(features))
        labels.append(int(quote["risk_label"]))

    X = np.array(rows, dtype=np.float32)
    y = np.array(labels, dtype=np.int32)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

    train_matrix = xgb.DMatrix(X_train, label=y_train, feature_names=FEATURE_NAMES)
    test_matrix = xgb.DMatrix(X_test, label=y_test, feature_names=FEATURE_NAMES)

    params = {
        "objective": "multi:softprob",
        "num_class": 3,
        "max_depth": 5,
        "eta": 0.12,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "min_child_weight": 3,
        "eval_metric": "mlogloss",
        "seed": seed,
    }

    booster = xgb.train(
        params,
        train_matrix,
        num_boost_round=num_boost_round,
        evals=[(test_matrix, "test")],
        early_stopping_rounds=25,
        verbose_eval=False,
    )

    predictions = booster.predict(test_matrix).argmax(axis=1)
    accuracy = float(accuracy_score(y_test, predictions))
    macro_f1 = float(f1_score(y_test, predictions, average="macro"))

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    booster.save_model(model_path)

    importance = sorted(
        booster.get_score(importance_type="gain").items(), key=lambda kv: -kv[1]
    )
    metadata = {
        "feature_names": FEATURE_NAMES,
        "label_to_band": {str(k): v for k, v in LABEL_TO_BAND.items()},
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "params": params,
        "best_iteration": int(getattr(booster, "best_iteration", num_boost_round)),
        "feature_importance": [[name, round(gain, 3)] for name, gain in importance],
    }
    with open(metadata_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    get_default_model(refresh=True)

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "class_distribution": {
            LABEL_TO_BAND[i]: int((y == i).sum()) for i in sorted(LABEL_TO_BAND)
        },
        "feature_importance": [(name, round(gain, 3)) for name, gain in importance],
        "report": classification_report(
            y_test, predictions,
            target_names=[LABEL_TO_BAND[i] for i in sorted(LABEL_TO_BAND)],
            zero_division=0,
        ),
        "model_path": model_path,
    }
