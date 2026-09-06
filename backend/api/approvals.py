from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models import Approval, AuditLog, Quotation, User, get_db
from api.deps import get_current_internal_user
from api.invoices import create_invoice_if_needed
from api.schemas import ApprovalDecisionIn, ApprovalOut

router = APIRouter(tags=["approvals"])

# Stages that still need a reviewer's action -- backs wireframe screen 5's
# "Pending Only" filter and its Pending/Returned/Approved badge counts.
PENDING_STAGES = {"sales_manager", "finance"}

# PS section 3: Sales Manager decides stage 1, Finance decides stage 2.
# Admin can act at either stage as an overseer. A Sales Rep -- who has no
# role in this list for either stage -- must never be able to decide their
# own submitted quotation.
STAGE_ROLES = {
    "sales_manager": ("sales_manager", "admin"),
    "finance": ("finance", "admin"),
}


@router.get("/approvals", response_model=list[ApprovalOut])
def list_approvals(
    pending_only: bool = Query(False, description="screen 5's 'Pending Only' filter"),
    db: Session = Depends(get_db),
):
    query = db.query(Approval)
    if pending_only:
        query = query.filter(Approval.stage.in_(PENDING_STAGES))
    return query.order_by(Approval.id.desc()).all()


@router.get("/approvals/{id}", response_model=ApprovalOut)
def get_approval(id: int, db: Session = Depends(get_db)):
    approval = db.get(Approval, id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.post("/approvals/{id}/decision", response_model=ApprovalOut)
def decide_approval(
    id: int, payload: ApprovalDecisionIn, db: Session = Depends(get_db),
    reviewer=Depends(get_current_internal_user),
):
    """The reviewer recorded on the audit trail (PDF A3: "logged with user,
    timestamp, and reason") is the authenticated internal user making this
    call, resolved server-side from the JWT -- never the client-sent
    payload.user/user_id, which could otherwise be spoofed to attribute a
    decision to anyone.
    """
    approval = db.get(Approval, id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if payload.action not in ("approve", "reject", "return"):
        raise HTTPException(status_code=400, detail="action must be approve, reject, or return")

    # Idempotency / duplicate-click guard: once a stage is resolved
    # (confirmed/rejected/returned), a second decision call -- a race from a
    # double-click, or a replayed request -- must not re-process it.
    if approval.stage not in PENDING_STAGES:
        raise HTTPException(status_code=400, detail="This approval has already been resolved")

    allowed_roles = STAGE_ROLES.get(approval.stage, ())
    if reviewer.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Only {' or '.join(allowed_roles)} can act on a {approval.stage.replace('_', ' ')} approval",
        )

    reviewer_user = db.get(User, int(reviewer["sub"]))
    reviewer_name = reviewer_user.name if reviewer_user else "Unknown reviewer"

    quotation = db.get(Quotation, approval.quotation_id)
    stage_before = approval.stage

    history = list(approval.history or [])
    history.append(
        {
            "user": reviewer_name,
            "action": payload.action,
            "note": payload.note,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    approval.history = history

    if payload.action == "reject":
        approval.stage = "rejected"
        quotation.status = "rejected"
    elif payload.action == "return":
        approval.stage = "returned"
        quotation.status = "draft"
    elif payload.action == "approve":
        if approval.stage == "sales_manager" and approval.blended_risk == "HIGH":
            approval.stage = "finance"
        else:
            approval.stage = "confirmed"
            quotation.status = "approved"
            create_invoice_if_needed(db, quotation)

    # PDF A3: "All approvals, rejections, and edits must be logged with user,
    # timestamp, and reason." Approval.history already carries this for the
    # approval screen itself; mirroring it into AuditLog puts approval
    # decisions in the same cross-entity audit trail as line edits.
    db.add(AuditLog(
        entity_type="approval", entity_id=approval.id, action=payload.action,
        user_id=reviewer_user.id if reviewer_user else None, reason=payload.note,
        before={"stage": stage_before}, after={"stage": approval.stage, "actor": reviewer_name},
    ))

    db.commit()
    db.refresh(approval)
    return approval
