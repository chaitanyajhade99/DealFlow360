"""PDF A7: Reporting & Dashboard Configuration."""
import io
from collections import Counter
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from openpyxl import Workbook
from sqlalchemy.orm import Session

from models import Approval, Quotation, get_db
from api.schemas import ReportSummaryOut

router = APIRouter(tags=["reports"])


def _filtered_quotations_and_stats(
    db: Session, date_from, date_to, sales_rep_id, approval_status, category
):
    """Shared by /reports/summary and both export endpoints so the numbers on
    screen and the numbers in the downloaded file are always computed the
    same way -- never two parallel implementations that could drift apart.
    """
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

    avg_hours = (
        round(sum(approval_durations_hours) / len(approval_durations_hours), 2)
        if approval_durations_hours else None
    )
    return filtered, avg_hours, top_product


@router.get("/reports/summary", response_model=ReportSummaryOut)
def get_report_summary(
    db: Session = Depends(get_db),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    sales_rep_id: int | None = Query(default=None),
    approval_status: str | None = Query(default=None, description="quotation status, e.g. pending_approval"),
    category: str | None = Query(default=None, description="filter to quotations containing a line in this category"),
):
    filtered, avg_hours, top_product = _filtered_quotations_and_stats(
        db, date_from, date_to, sales_rep_id, approval_status, category
    )
    return ReportSummaryOut(
        quotes_created=len(filtered),
        avg_approval_time_hours=avg_hours,
        top_discounted_product=top_product,
        matching_quotations=[
            {"id": q.id, "customer_name": q.customer_name, "status": q.status, "created_at": q.created_at.isoformat()}
            for q in filtered
        ],
    )


@router.get("/reports/export.pdf")
def export_report_pdf(
    db: Session = Depends(get_db),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    sales_rep_id: int | None = Query(default=None),
    approval_status: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    """PDF A7: "Export options: PDF / XLS" -- was previously undeclared scope
    ("needs a library decision the team hasn't made"). Uses reportlab, same
    as the quotation PDF export, over exactly the filtered set
    /reports/summary itself returns.
    """
    filtered, avg_hours, top_product = _filtered_quotations_and_stats(
        db, date_from, date_to, sales_rep_id, approval_status, category
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=16 * mm, bottomMargin=16 * mm, leftMargin=14 * mm, rightMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("DealFlow360 — Sales Report", styles["Title"]),
        Spacer(1, 4),
        Paragraph(
            f"Filters — From: {date_from or 'any'} · To: {date_to or 'any'} · "
            f"Approval Status: {approval_status or 'all'} · Category: {category or 'all'}",
            styles["Normal"],
        ),
        Spacer(1, 10),
        Paragraph(f"<b>Quotes Created:</b> {len(filtered)}", styles["Normal"]),
        Paragraph(f"<b>Avg Approval Time:</b> {avg_hours if avg_hours is not None else '—'} hrs", styles["Normal"]),
        Paragraph(f"<b>Top Discounted Product:</b> {top_product or '—'}", styles["Normal"]),
        Spacer(1, 12),
    ]

    rows = [["Quotation", "Customer", "Tier", "Status", "Created", "Sales Rep ID"]]
    for q in filtered:
        rows.append([
            f"Q-{q.id:04d}", q.customer_name, q.customer_tier, q.status.replace("_", " "),
            q.created_at.strftime("%Y-%m-%d"), str(q.sales_rep_id or "—"),
        ])
    table = Table(rows, colWidths=[28 * mm, 55 * mm, 22 * mm, 32 * mm, 28 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0c5a96")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="dealflow360-report.pdf"'},
    )


@router.get("/reports/export.xlsx")
def export_report_xlsx(
    db: Session = Depends(get_db),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    sales_rep_id: int | None = Query(default=None),
    approval_status: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    """PDF A7's other export option -- same filtered dataset as the PDF
    export and /reports/summary, as a real .xlsx workbook (openpyxl).
    """
    filtered, avg_hours, top_product = _filtered_quotations_and_stats(
        db, date_from, date_to, sales_rep_id, approval_status, category
    )

    wb = Workbook()
    summary_ws = wb.active
    summary_ws.title = "Summary"
    summary_ws.append(["Quotes Created", len(filtered)])
    summary_ws.append(["Avg Approval Time (hrs)", avg_hours if avg_hours is not None else ""])
    summary_ws.append(["Top Discounted Product", top_product or ""])

    detail_ws = wb.create_sheet("Quotations")
    detail_ws.append(["Quotation", "Customer", "Tier", "Status", "Created", "Sales Rep ID"])
    for q in filtered:
        detail_ws.append([
            f"Q-{q.id:04d}", q.customer_name, q.customer_tier, q.status,
            q.created_at.strftime("%Y-%m-%d"), q.sales_rep_id or "",
        ])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="dealflow360-report.xlsx"'},
    )
