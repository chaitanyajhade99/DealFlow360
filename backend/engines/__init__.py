"""DealFlow360 algorithm layer (Person 2).

Pure functions: plain data in, plain dict/list out. No DB access, no imports
from backend/models/ or backend/api/. Every engine is safe to call from a
request handler or a test with hand-written dicts.

The four contract functions (API_CONTRACT.md, "Engine function signatures"):

    from backend.engines import (
        score_risk, split_warehouse, detect_anomalies, recommend_upsell,
    )

Algorithms behind them:

    score_risk        deterministic rule floor + XGBoost escalation (hybrid)
    split_warehouse   greedy deepest-stock-first allocation
    detect_anomalies  per-rep 2-sigma z-score
    recommend_upsell  Apriori association rules, ranked by expected margin

The two models train from synthetic data:  python backend/engines/train.py
Neither is required at import time -- with no trained artifact, score_risk
runs rules-only and recommend_upsell falls back to count-based ranking.

xgboost/numpy are imported lazily inside functions, so importing this package
stays cheap for API code paths that never score a quote.
"""

from .anomaly_engine import Z_SCORE_CAP, Z_THRESHOLD, detect_anomalies
from .stalled_engine import DEFAULT_STALE_DAYS, TERMINAL_STATUSES, detect_stalled
from .apriori import (
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_MIN_LIFT,
    DEFAULT_MIN_SUPPORT,
    build_co_occurrence,
    find_frequent_itemsets,
    generate_rules,
)
from .fulfillment_engine import split_warehouse
from .risk_engine import (
    BLENDED_HIGH_PCT,
    DEFAULT_CATEGORY_LIMIT_PCT,
    FLAGGED_LINE_COLUMNS,
    MODEL_ESCALATION_MIN_CONFIDENCE,
    SINGLE_LINE_HIGH_PCT,
    score_risk,
    score_rules_only,
)
from .risk_model import (
    FEATURE_NAMES,
    RiskModel,
    extract_features,
    get_default_model,
    train_risk_model,
)
from .synthetic_data import (
    CATEGORY_LIMITS,
    PRODUCT_CATALOG,
    TIER_LIMITS,
    generate_quotation_history,
    generate_rep_discount_histories,
    generate_transactions,
    product_margins,
)
from .upsell_engine import PROMOTION_BOOST, recommend_upsell

__all__ = [
    # --- API_CONTRACT.md engine functions ---
    "score_risk",
    "split_warehouse",
    "detect_anomalies",
    "detect_stalled",
    "recommend_upsell",
    # --- risk: rules, model, hybrid ---
    "score_rules_only",
    "RiskModel",
    "extract_features",
    "get_default_model",
    "train_risk_model",
    "FEATURE_NAMES",
    # --- cross-sell: Apriori ---
    "find_frequent_itemsets",
    "generate_rules",
    "build_co_occurrence",
    # --- synthetic data ---
    "generate_quotation_history",
    "generate_transactions",
    "generate_rep_discount_histories",
    "product_margins",
    "PRODUCT_CATALOG",
    "CATEGORY_LIMITS",
    "TIER_LIMITS",
    # --- tunables, so config screens can display or override them ---
    "FLAGGED_LINE_COLUMNS",
    "DEFAULT_CATEGORY_LIMIT_PCT",
    "SINGLE_LINE_HIGH_PCT",
    "BLENDED_HIGH_PCT",
    "MODEL_ESCALATION_MIN_CONFIDENCE",
    "Z_THRESHOLD",
    "Z_SCORE_CAP",
    "DEFAULT_STALE_DAYS",
    "TERMINAL_STATUSES",
    "PROMOTION_BOOST",
    "DEFAULT_MIN_SUPPORT",
    "DEFAULT_MIN_CONFIDENCE",
    "DEFAULT_MIN_LIFT",
]
