"""FastAPI transport layer over the four contract engines.

The engines themselves stay pure -- plain dicts in, plain dicts out, no DB, no
framework. This module is the only place that knows HTTP exists, so the engines
remain directly importable and unit-testable exactly as before.

Two ways to use it:

  1. Mounted into Person 1's app (preferred -- one service, one /docs):

         from backend.engines.api import router
         app.include_router(router)

  2. Standalone, to develop or demo the engines with no database at all:

         uvicorn backend.engines.api:app --reload
         # -> http://127.0.0.1:8000/docs

Every route is stateless. Nothing here reads or writes the database: the caller
passes the rows it already loaded, which is what keeps these endpoints safe to
call from anywhere and trivial to test.

Pydantic v1 (the installed version, 1.10.x) -- so `class Config`, not
`model_config`, and `.dict()`, not `.model_dump()`.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, Field, validator

from .anomaly_engine import Z_SCORE_CAP, Z_THRESHOLD, detect_anomalies
from .fulfillment_engine import split_warehouse
from .risk_engine import (
    BLENDED_HIGH_PCT,
    DEFAULT_CATEGORY_LIMIT_PCT,
    MODEL_ESCALATION_MIN_CONFIDENCE,
    SINGLE_LINE_HIGH_PCT,
    score_risk,
)
from .risk_model import FEATURE_NAMES, get_default_model
from .upsell_engine import PROMOTION_BOOST, recommend_upsell

router = APIRouter(prefix="/engines", tags=["engines"])

# Last two weeks of a calendar quarter. The engine takes is_quarter_end as a
# plain bool and never derives it; this is a convenience for callers holding
# only quotations.created_at, and it is a convention chosen here, not something
# the PDF pins down. Pass is_quarter_end explicitly to override it.
QUARTER_END_WINDOW_DAYS = 14


def _is_quarter_end(day: date) -> bool:
    quarter_end_month = 3 * ((day.month - 1) // 3) + 3
    if day.month != quarter_end_month:
        return False
    if quarter_end_month == 12:
        last_day = date(day.year, 12, 31)
    else:
        last_day = date(day.year, quarter_end_month + 1, 1) - timedelta(days=1)
    return (last_day - day).days < QUARTER_END_WINDOW_DAYS


# --------------------------------------------------------------------------
# Shared line model
# --------------------------------------------------------------------------


class QuotationLineIn(BaseModel):
    """One row of `quotation_lines`, as the database hands it back.

    numeric() columns arrive as Decimal over psycopg2; declaring them float
    lets pydantic coerce once here so the engines never see a Decimal.
    """

    id: Optional[int] = Field(None, description="quotation_lines.id")
    product_id: Optional[str] = Field(None, description="free-text product code")
    product_name: Optional[str] = Field(
        None,
        description="join products.name ON product_code = product_id; "
        "without it the flagged-lines table shows the raw code",
    )
    category: Optional[str] = Field(
        None,
        description='"Hardware" | "Services" | "Subscription". '
        'Both "Services" and "Service" are accepted.',
    )
    qty: float = 0.0
    unit_price: float = 0.0
    discount_pct: float = Field(0.0, description="percentage POINTS, so 12.0 means 12%")
    category_limit_pct: Optional[float] = Field(
        None,
        description="omit and the line is scored against a "
        f"{DEFAULT_CATEGORY_LIMIT_PCT}% ceiling (fail-closed, so it flags "
        "rather than silently passing)",
    )

    class Config:
        schema_extra = {
            "example": {
                "id": 2,
                "product_id": "SETUP-SVC",
                "product_name": "Setup Service",
                "category": "Services",
                "qty": 1,
                "unit_price": 2000.00,
                "discount_pct": 18.0,
                "category_limit_pct": 10.0,
            }
        }


# --------------------------------------------------------------------------
# 1. score_risk
# --------------------------------------------------------------------------


class RiskRequest(BaseModel):
    lines: List[QuotationLineIn] = Field(..., min_items=1)
    customer_tier: Optional[str] = Field(
        None, description='"Bronze" | "Silver" | "Gold" (case-insensitive)'
    )
    rep_avg_discount_pct: Optional[float] = Field(
        None, description="the rep's historical average discount, in points"
    )
    is_quarter_end: Optional[bool] = Field(
        None, description="omit and it is derived from quote_date, if given"
    )
    quote_date: Optional[date] = Field(
        None,
        description="quotations.created_at. Only used to derive is_quarter_end "
        "when that is not supplied.",
    )
    seniority: Optional[int] = Field(
        None, ge=0, le=2, description="0 junior, 1 mid, 2 principal"
    )
    use_model: bool = Field(
        True, description="false runs the deterministic rules only"
    )

    @validator("customer_tier")
    def _normalise_tier(cls, value):
        # The engine looks the tier up in an exact-match dict, so fold case
        # here rather than silently scoring "gold" as unknown.
        return value.strip().title() if value else value

    class Config:
        schema_extra = {
            "example": {
                "lines": [
                    {
                        "product_name": "Laptop",
                        "category": "Hardware",
                        "qty": 10,
                        "unit_price": 1200.0,
                        "discount_pct": 12.0,
                        "category_limit_pct": 15.0,
                    },
                    {
                        "product_name": "Setup Service",
                        "category": "Services",
                        "qty": 1,
                        "unit_price": 2000.0,
                        "discount_pct": 18.0,
                        "category_limit_pct": 10.0,
                    },
                ],
                "customer_tier": "Gold",
                "seniority": 0,
            }
        }


class FlaggedLineOut(BaseModel):
    line: str = Field(..., description="screen 6 column: Line")
    discount_given_pct: float = Field(..., description="screen 6: Discount Given")
    limit_allowed_pct: float = Field(..., description="screen 6: Limit Allowed")
    over_by_pct: float = Field(..., description="screen 6: Over By")
    line_id: Optional[int] = None
    product_id: Optional[str] = None
    category: Optional[str] = None
    line_value: float = Field(..., description="gross list value, qty * unit_price")


class RiskResponse(BaseModel):
    blended_risk: str = Field(..., description='"LOW" | "MEDIUM" | "HIGH"')
    flagged_lines: List[FlaggedLineOut] = Field(
        ...,
        description="worst overage first. Can be EMPTY on a HIGH band when the "
        "model escalated -- that is the interesting case, not a bug.",
    )
    blended_score_pct: float
    worst_line_over_pct: float
    total_line_value: float
    approval_chain: List[str] = Field(
        ..., description='[] | ["Sales Manager"] | ["Sales Manager", "Finance"]'
    )
    reason: str = Field(
        ..., description="plain-language justification -- store this on the "
        "Approval record, it is PDF A3's required reason field"
    )
    rule_risk: str
    model_risk: Optional[str] = None
    model_confidence: Optional[float] = None
    model_probabilities: Optional[Dict[str, float]] = None
    model_available: bool = Field(
        ..., description="false when no artifact is trained; result is rules-only"
    )
    escalated_by_model: bool


@router.post(
    "/risk/score",
    response_model=RiskResponse,
    summary="Score a quotation's discount risk",
)
def risk_score(payload: RiskRequest) -> dict:
    """Deterministic rule floor, with the trained model allowed to escalate.

    The model can raise the band but never lower it, and only above
    MODEL_ESCALATION_MIN_CONFIDENCE. With no trained artifact this degrades to
    rules-only and reports `model_available: false` rather than failing.

    Backs wireframe screen 6 ("Why This Quote Was Flagged").
    """
    quarter_end = payload.is_quarter_end
    if quarter_end is None:
        quarter_end = _is_quarter_end(payload.quote_date) if payload.quote_date else False

    return score_risk(
        [line.dict() for line in payload.lines],
        customer_tier=payload.customer_tier,
        rep_avg_discount_pct=payload.rep_avg_discount_pct,
        is_quarter_end=quarter_end,
        seniority=payload.seniority,
        use_model=payload.use_model,
    )


# --------------------------------------------------------------------------
# 2. split_warehouse
# --------------------------------------------------------------------------


class StockEntryIn(BaseModel):
    product_id: str
    qty: int


class WarehouseIn(BaseModel):
    """One row of `warehouses`. Pass the `stock` jsonb straight through."""

    id: Any = Field(..., description="warehouses.id")
    name: Optional[str] = None
    stock: Union[List[StockEntryIn], Dict[str, int]] = Field(
        ...,
        description='the jsonb column as-is: [{"product_id": "P1", "qty": 10}], '
        'or the shorthand map {"P1": 10}',
    )
    shipping_cost_per_unit: Optional[float] = Field(
        None, description="no such column yet -- cost reads 0.00 until it exists"
    )
    shipment_fixed_cost: Optional[float] = Field(
        None, description="no such column yet -- cost reads 0.00 until it exists"
    )

    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "name": "Main Warehouse",
                "stock": [{"product_id": "LAPTOP-PRO-14", "qty": 50}],
            }
        }


class FulfillmentRequest(BaseModel):
    product_id: str
    qty: int = Field(..., description="units required; <= 0 returns an empty list")
    warehouses: List[WarehouseIn]


class SplitRowOut(BaseModel):
    warehouse_id: Any = Field(..., description="null on the backorder row")
    qty: int = Field(..., description="screen 8: Qty Fulfilled")
    cost: float = Field(..., description="screen 8: Cost")
    warehouse: str = Field(..., description="screen 8: Warehouse")
    est_shipments: int = Field(..., description="screen 8: Est. Shipments")
    is_backorder: bool = Field(
        ...,
        description="present on EVERY row, so a plain row['is_backorder'] never "
        "raises. Filter these out before persisting FulfillmentSplit.splits.",
    )


@router.post(
    "/fulfillment/split",
    response_model=List[SplitRowOut],
    summary="Allocate one product across warehouses",
)
def fulfillment_split(payload: FulfillmentRequest) -> list:
    """Greedy, deepest-stock-first, which is what minimises shipments.

    If stock cannot cover the qty, a final row carries the shortfall with
    `is_backorder: true` and `warehouse_id: null` -- that row drives B6's
    "Consolidate Remaining Backorder" prompt and must be filtered out before
    persisting the split.

    Backs wireframe screen 8.
    """
    return split_warehouse(
        payload.product_id,
        payload.qty,
        [warehouse.dict() for warehouse in payload.warehouses],
    )


# --------------------------------------------------------------------------
# 3. detect_anomalies
# --------------------------------------------------------------------------


class AnomalyRequest(BaseModel):
    rep_discount_history: List[float] = Field(
        ...,
        description="this rep's PAST discounts in points, excluding the quote "
        "under review. Order does not matter.",
    )
    current_discount: float = Field(..., description="in points")

    class Config:
        schema_extra = {
            "example": {
                "rep_discount_history": [5.0, 6.0, 5.0, 7.0, 6.0, 5.0],
                "current_discount": 18.0,
            }
        }


class AnomalyResponse(BaseModel):
    is_anomaly: bool
    z_score: float = Field(
        ..., description=f"capped at {Z_SCORE_CAP} when history has zero variance"
    )
    mean: float
    stddev: float
    threshold: float
    current_discount: float
    sample_size: int = Field(
        ...,
        description="usable history entries. 0 or 1 means there is no baseline "
        "yet -- render 'not enough history', not 'clean'.",
    )


@router.post(
    "/anomalies/detect",
    response_model=AnomalyResponse,
    summary="Flag a discount unusual for this rep",
)
def anomalies_detect(payload: AnomalyRequest) -> dict:
    """Per-rep z-score against the rep's own history, sample stddev (n-1).

    The baseline is per-rep on purpose: 18% is routine for one rep and alarming
    for another. Fewer than 2 history entries is never an anomaly.

    Backs wireframe screen 14.
    """
    return detect_anomalies(payload.rep_discount_history, payload.current_discount)


# --------------------------------------------------------------------------
# 4. recommend_upsell
# --------------------------------------------------------------------------


class UpsellRequest(BaseModel):
    cart_items: List[str] = Field(
        ..., description="product ids already quoted; never suggested back"
    )
    co_occurrence_data: Dict[str, List[Dict[str, Any]]] = Field(
        ...,
        description="{cart_product_id: [suggestion, ...]}. Left as a loose dict "
        "on purpose -- the engine accepts several key spellings "
        "(count/co_occurrence, margin/margin_delta/margin_impact), and modelling "
        "it strictly here would throw those away.",
    )
    min_margin: float = 0.0
    min_lift: float = Field(
        0.0, description="1.0 keeps only pairings beating the product's base rate"
    )
    limit: Optional[int] = Field(None, ge=0)

    class Config:
        schema_extra = {
            "example": {
                "cart_items": ["LAPTOP-01"],
                "co_occurrence_data": {
                    "LAPTOP-01": [
                        {
                            "product_id": "DOCK-01",
                            "product_name": "Docking Station",
                            "co_purchase_count": 40,
                            "margin": 50.0,
                            "confidence": 0.597,
                            "lift": 1.81,
                        }
                    ]
                },
                "min_margin": 20.0,
            }
        }


class UpsellRowOut(BaseModel):
    product_id: str
    margin_delta: float
    co_purchase_count: float
    score: float
    ranking_basis: str = Field(
        ...,
        description='"confidence_x_margin" | "count_x_margin" | "confidence_only" '
        '| "count_only". The _only forms mean no margin data was available and '
        "the ranking is likelihood-only -- degraded, but honest.",
    )
    confidence: Optional[float] = None
    lift: Optional[float] = None
    expected_margin: Optional[float] = None
    is_promoted: bool
    promo_tag: Optional[str] = Field(None, description="null when not promoted")
    product_name: str


@router.post(
    "/upsell/recommend",
    response_model=List[UpsellRowOut],
    summary="Rank cross-sell suggestions for a cart",
)
def upsell_recommend(payload: UpsellRequest) -> list:
    """Ranked by expected margin (confidence x margin), best first.

    Expected margin is the right ranking for a rep: a cheap accessory in 70% of
    baskets is worth less than a 50-margin dock in 60% of them.

    Backs wireframe screen 4.
    """
    return recommend_upsell(
        payload.cart_items,
        payload.co_occurrence_data,
        min_margin=payload.min_margin,
        min_lift=payload.min_lift,
        limit=payload.limit,
    )


# --------------------------------------------------------------------------
# Health and config
# --------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    model_available: bool
    model_metrics: Optional[Dict[str, Any]] = None
    top_features: Optional[List[List[Any]]] = None
    feature_names: List[str]


@router.get("/health", response_model=HealthResponse, summary="Engine and model status")
def health() -> dict:
    """Whether a trained artifact is loaded, and how good it is.

    `model_available: false` is a healthy state, not an error -- scoring falls
    back to the deterministic rules. Run `python backend/engines/train.py` to
    produce the artifact.
    """
    model = get_default_model()
    if model is None:
        return {
            "status": "ok",
            "model_available": False,
            "model_metrics": None,
            "top_features": None,
            "feature_names": FEATURE_NAMES,
        }
    metadata = model.metadata or {}
    return {
        "status": "ok",
        "model_available": True,
        "model_metrics": {
            key: metadata.get(key)
            for key in ("accuracy", "macro_f1", "n_train", "n_test")
            if metadata.get(key) is not None
        },
        "top_features": [list(pair) for pair in model.feature_importance(6)],
        "feature_names": model.feature_names,
    }


class ConfigResponse(BaseModel):
    single_line_high_pct: float
    blended_high_pct: float
    default_category_limit_pct: float
    model_escalation_min_confidence: float
    z_threshold: float
    z_score_cap: float
    promotion_boost: float


@router.get("/config", response_model=ConfigResponse, summary="Engine tunables")
def config() -> dict:
    """The thresholds every engine reads, for the admin config screens (A3/A6).

    Read-only. These are module constants, so changing them is a deploy, not a
    request -- surface them so the config screen can display what is actually
    in force rather than hard-coding a second copy.
    """
    return {
        "single_line_high_pct": SINGLE_LINE_HIGH_PCT,
        "blended_high_pct": BLENDED_HIGH_PCT,
        "default_category_limit_pct": DEFAULT_CATEGORY_LIMIT_PCT,
        "model_escalation_min_confidence": MODEL_ESCALATION_MIN_CONFIDENCE,
        "z_threshold": Z_THRESHOLD,
        "z_score_cap": Z_SCORE_CAP,
        "promotion_boost": PROMOTION_BOOST,
    }


# --------------------------------------------------------------------------
# Standalone app
# --------------------------------------------------------------------------

app = FastAPI(
    title="DealFlow360 — engines",
    version="1.0.0",
    description=(
        "Stateless HTTP wrappers over the four algorithm engines. No database "
        "access: the caller passes the rows it already loaded. Mount `router` "
        "into the main app, or run this standalone to work on the engines "
        "without a database."
    ),
)
app.include_router(router)


@app.get("/", include_in_schema=False)
def index() -> dict:
    return {"service": "dealflow360-engines", "docs": "/docs"}
