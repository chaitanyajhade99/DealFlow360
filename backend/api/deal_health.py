from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from engines import detect_anomalies
from models import AuditLog, Quotation, User, get_db
from api.deps import get_current_internal_user
from api.schemas import DealHealthActionIn, DealHealthActionOut, DealHealthOut

router = APIRouter(tags=["deal-health"])

STALLED_AFTER_DAYS = 5
TERMINAL_STATUSES = {"rejected", "confirmed", "cancelled"}


def _avg_discount(quotation: Quotation) -> float:
    if not quotation.lines:
        return 0.0
    return sum(float(line.discount_pct) for line in quotation.lines) / len(quotation.lines)


def compute_deal_health(db: Session) -> dict:
    """Shared by GET /deal-health and GET /dashboard/summary's at_risk_deals
    count, so both read the exact same definition of "at risk".
    """
    quotations = db.query(Quotation).all()
    now = datetime.now(timezone.utc)

    stalled_deals = []
    for q in quotations:
        if q.status in TERMINAL_STATUSES:
            continue
        created_at = q.created_at if q.created_at.tzinfo else q.created_at.replace(tzinfo=timezone.utc)
        if now - created_at > timedelta(days=STALLED_AFTER_DAYS):
            stalled_deals.append(
                {
                    "quotation_id": q.id,
                    "customer_name": q.customer_name,
                    "status": q.status,
                    "days_inactive": (now - created_at).days,
                }
            )

    discount_anomalies = []
    for q in quotations:
        if q.status in TERMINAL_STATUSES or not q.lines:
            continue
        current_discount = _avg_discount(q)
        history = [
            _avg_discount(other)
            for other in quotations
            if other.id != q.id and other.customer_tier == q.customer_tier and other.lines
        ]
        result = detect_anomalies(history, current_discount)
        if result["is_anomaly"]:
            discount_anomalies.append(
                {
                    "quotation_id": q.id,
                    "customer_name": q.customer_name,
                    "current_discount": current_discount,
                    "z_score": result["z_score"],
                }
            )

    delivery_slippage = []
    today = date.today()
    for q in quotations:
        if not q.expected_delivery_date or q.actual_delivery_date:
            continue
        if q.expected_delivery_date < today:
            delivery_slippage.append(
                {
                    "quotation_id": q.id,
                    "customer_name": q.customer_name,
                    "expected_delivery_date": q.expected_delivery_date.isoformat(),
                    "days_late": (today - q.expected_delivery_date).days,
                }
            )

    return {
        "stalled_deals": stalled_deals,
        "discount_anomalies": discount_anomalies,
        "delivery_slippage": delivery_slippage,
    }


@router.get("/deal-health", response_model=DealHealthOut)
def get_deal_health(db: Session = Depends(get_db)):
    return DealHealthOut(**compute_deal_health(db))


# PDF B9: "an automated nudge or escalation action can be triggered from an
# alert". Both write to AuditLog so the action shows up in the dashboard's
# recent-activity feed and in any per-quotation history view.

def _reviewer_name(db: Session, reviewer: dict) -> str:
    """Same rule as api.approvals.decide_approval: the actor recorded on the
    audit trail is the authenticated caller resolved from the JWT, never a
    client-sent name that could be spoofed.
    """
    user = db.get(User, int(reviewer["sub"]))
    return user.name if user else "Unknown reviewer"


@router.post("/deal-health/{quotation_id}/nudge", response_model=DealHealthActionOut)
def nudge_quotation(
    quotation_id: int, payload: DealHealthActionIn, db: Session = Depends(get_db),
    reviewer=Depends(get_current_internal_user),
):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    db.add(AuditLog(
        entity_type="quotation", entity_id=quotation_id, action="nudge",
        reason=payload.note or "Nudged from Deal Health dashboard",
        after={"actor": _reviewer_name(db, reviewer)},
    ))
    db.commit()
    return DealHealthActionOut(status="ok", action="nudge", quotation_id=quotation_id)


@router.post("/deal-health/{quotation_id}/escalate", response_model=DealHealthActionOut)
def escalate_quotation(
    quotation_id: int, payload: DealHealthActionIn, db: Session = Depends(get_db),
    reviewer=Depends(get_current_internal_user),
):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    db.add(AuditLog(
        entity_type="quotation", entity_id=quotation_id, action="escalate",
        reason=payload.note or "Escalated from Deal Health dashboard",
        after={"actor": _reviewer_name(db, reviewer)},
    ))
    db.commit()
    return DealHealthActionOut(status="ok", action="escalate", quotation_id=quotation_id)
