from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models import Approval, AuditLog, Quotation, get_db
from api.invoices import create_invoice_if_needed
from api.schemas import ApprovalDecisionIn, ApprovalOut

router = APIRouter(tags=["approvals"])

# Stages that still need a reviewer's action -- backs wireframe screen 5's
# "Pending Only" filter and its Pending/Returned/Approved badge counts.
PENDING_STAGES = {"sales_manager", "finance"}


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
def decide_approval(id: int, payload: ApprovalDecisionIn, db: Session = Depends(get_db)):
    approval = db.get(Approval, id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if payload.action not in ("approve", "reject", "return"):
        raise HTTPException(status_code=400, detail="action must be approve, reject, or return")

    quotation = db.get(Quotation, approval.quotation_id)
    stage_before = approval.stage

    history = list(approval.history or [])
    history.append(
        {
            "user": payload.user,
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
        user_id=payload.user_id, reason=payload.note,
        before={"stage": stage_before}, after={"stage": approval.stage, "actor": payload.user},
    ))

    db.commit()
    db.refresh(approval)
    return approval
