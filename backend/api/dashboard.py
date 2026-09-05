"""PDF wireframe screen 2 (Sales Dashboard / Home): pending approvals count,
open quotations count, at-risk deals count, and a merged recent-activity feed.

Nothing else in the API aggregates these in one call -- without this,
Person 3 would need 3+ round trips and would still have nowhere to source
"Recent Activity" (it isn't stored as one table; it's a merge of AuditLog,
Approval.history, and NegotiationRequest).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deal_health import TERMINAL_STATUSES, compute_deal_health
from api.schemas import DashboardSummaryOut
from models import Approval, AuditLog, NegotiationRequest, Quotation, get_db

router = APIRouter(tags=["dashboard"])


def _iso(dt) -> str:
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


@router.get("/dashboard/summary", response_model=DashboardSummaryOut)
def dashboard_summary(activity_limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    pending_approvals = (
        db.query(Approval).filter(Approval.stage.in_({"sales_manager", "finance"})).count()
    )
    open_quotations = (
        db.query(Quotation).filter(~Quotation.status.in_(TERMINAL_STATUSES)).count()
    )
    health = compute_deal_health(db)
    at_risk_ids = {row["quotation_id"] for row in health["stalled_deals"]}
    at_risk_ids |= {row["quotation_id"] for row in health["discount_anomalies"]}
    at_risk_ids |= {row["quotation_id"] for row in health["delivery_slippage"]}

    quotations_by_id = {q.id: q for q in db.query(Quotation).all()}
    activity: list[dict] = []

    ACTION_VERBS = {
        "create": "created", "edit": "edited", "delete": "deleted",
        "approve": "approved", "reject": "rejected", "return": "returned",
        "nudge": "nudged", "escalate": "escalated",
    }

    for log in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(50).all():
        actor = (log.after or {}).get("actor") if isinstance(log.after, dict) else None
        who = actor or (f"user #{log.user_id}" if log.user_id else "system")
        verb = ACTION_VERBS.get(log.action, f"{log.action}d")
        activity.append({
            "type": f"{log.entity_type}_{log.action}",
            "description": f"{who} {verb} {log.entity_type} #{log.entity_id}"
            + (f" ({log.reason})" if log.reason else ""),
            "at": _iso(log.created_at),
        })

    for approval in db.query(Approval).order_by(Approval.id.desc()).limit(50).all():
        quotation = quotations_by_id.get(approval.quotation_id)
        customer = quotation.customer_name if quotation else f"quotation #{approval.quotation_id}"
        for entry in approval.history or []:
            activity.append({
                "type": "approval_" + str(entry.get("action")),
                "description": f"{entry.get('user', 'system')} {entry.get('action')} "
                f"{customer}'s quotation" + (f" -- {entry.get('note')}" if entry.get("note") else "")
                + (f" -- {entry.get('reason')}" if entry.get("reason") else ""),
                "at": _iso(entry.get("at")),
            })

    for negotiation in db.query(NegotiationRequest).order_by(NegotiationRequest.id.desc()).limit(50).all():
        quotation = quotations_by_id.get(negotiation.quotation_id)
        customer = quotation.customer_name if quotation else f"quotation #{negotiation.quotation_id}"
        activity.append({
            "type": "negotiation_" + negotiation.status,
            "description": f"{customer} requested a change" +
            (f": counter {negotiation.counter_discount_pct}% off" if negotiation.counter_discount_pct is not None else ""),
            "at": _iso(negotiation.created_at),
        })

    activity.sort(key=lambda row: row["at"], reverse=True)

    return DashboardSummaryOut(
        pending_approvals=pending_approvals,
        open_quotations=open_quotations,
        at_risk_deals=len(at_risk_ids),
        recent_activity=activity[:activity_limit],
    )
