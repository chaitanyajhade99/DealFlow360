"""PDF A7: Reporting & Dashboard Configuration.

PDF/XLS export is intentionally NOT implemented here — that needs an export
library decision (reportlab/openpyxl) the team hasn't made; deferred rather
than faked. This endpoint covers the filtering + summary stats the export
would be built from.
"""
from collections import Counter
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from models import Approval, Quotation, get_db
from api.schemas import ReportSummaryOut

router = APIRouter(tags=["reports"])


@router.get("/reports/summary", response_model=ReportSummaryOut)
def get_report_summary(
    db: Session = Depends(get_db),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    sales_rep_id: int | None = Query(default=None),
    approval_status: str | None = Query(default=None, description="quotation status, e.g. pending_approval"),
    category: str | None = Query(default=None, description="filter to quotations containing a line in this category"),
):
    quotations = db.query(Quotation).all()

    def matches(q: Quotation) -> bool:
        created = q.created_at if q.created_at.tzinfo else q.created_at.replace(tzinfo=timezone.utc)
        if date_from and created.date() < date_from:
            return False
        if date_to and created.date() > date_to:
            return False
        if sales_rep_id is not None and q.sales_rep_id != sales_rep_id:
            return False
        if approval_status and q.status != approval_status:
            return False
        if category and not any(line.category == category for line in q.lines):
            return False
        return True

    filtered = [q for q in quotations if matches(q)]

    approval_durations_hours = []
    for q in filtered:
        approvals = (
            db.query(Approval)
            .filter(Approval.quotation_id == q.id)
            .order_by(Approval.id.asc())
            .all()
        )
        for a in approvals:
            history = a.history or []
            flagged_at = next((h["at"] for h in history if h.get("action") == "flagged"), None)
            resolved_at = next((h["at"] for h in reversed(history) if h.get("action") in ("approve", "reject")), None)
            if flagged_at and resolved_at:
                delta = datetime.fromisoformat(resolved_at) - datetime.fromisoformat(flagged_at)
                approval_durations_hours.append(delta.total_seconds() / 3600)

    product_counter = Counter()
    for q in filtered:
        for line in q.lines:
            product_counter[line.product_id] += float(line.discount_pct)
    top_product = product_counter.most_common(1)[0][0] if product_counter else None

    return ReportSummaryOut(
        quotes_created=len(filtered),
        avg_approval_time_hours=(
            round(sum(approval_durations_hours) / len(approval_durations_hours), 2)
            if approval_durations_hours else None
        ),
        top_discounted_product=top_product,
        matching_quotations=[
            {"id": q.id, "customer_name": q.customer_name, "status": q.status, "created_at": q.created_at.isoformat()}
            for q in filtered
        ],
    )
