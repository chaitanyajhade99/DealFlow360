from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import Approval, Quotation, get_db
from api.invoices import create_invoice_if_needed
from api.schemas import ApprovalDecisionIn, ApprovalOut

router = APIRouter(tags=["approvals"])


@router.post("/approvals/{id}/decision", response_model=ApprovalOut)
def decide_approval(id: int, payload: ApprovalDecisionIn, db: Session = Depends(get_db)):
    approval = db.get(Approval, id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if payload.action not in ("approve", "reject", "return"):
        raise HTTPException(status_code=400, detail="action must be approve, reject, or return")

    quotation = db.get(Quotation, approval.quotation_id)

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

    db.commit()
    db.refresh(approval)
    return approval
