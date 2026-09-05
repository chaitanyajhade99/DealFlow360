import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from engines import score_risk
from models import Approval, AuditLog, DiscountTier, Product, Quotation, QuotationLine, User, get_db
from api.invoices import create_invoice_if_needed
from api.schemas import (
    ApprovalOut,
    QuotationCreate,
    QuotationLinesUpdate,
    QuotationOut,
)

router = APIRouter(tags=["quotations"])

QUARTER_END_MONTHS = {3: 31, 6: 30, 9: 30, 12: 31}


def _is_quarter_end(dt: datetime, window_days: int = 7) -> bool:
    """True during the last `window_days` days of a fiscal quarter."""
    last_day = QUARTER_END_MONTHS.get(dt.month)
    return last_day is not None and dt.day >= last_day - window_days + 1


def _rep_avg_discount_pct(db: Session, sales_rep_id: int | None, exclude_quotation_id: int) -> float | None:
    if sales_rep_id is None:
        return None
    avg = (
        db.query(sa_func.avg(QuotationLine.discount_pct))
        .join(Quotation, Quotation.id == QuotationLine.quotation_id)
        .filter(Quotation.sales_rep_id == sales_rep_id, Quotation.id != exclude_quotation_id)
        .scalar()
    )
    return float(avg) if avg is not None else None


def _products_for_lines(db: Session, lines: list[QuotationLine]) -> dict[str, Product]:
    codes = {line.product_id for line in lines}
    if not codes:
        return {}
    return {p.product_code: p for p in db.query(Product).filter(Product.product_code.in_(codes)).all()}


def _attach_product_names(db: Session, lines: list[QuotationLine]) -> None:
    """Cosmetic join: sets a transient `product_name` attribute on each line
    (product_id is a free-text string, not an FK — see DATABASE_SCHEMA.md).
    """
    products_by_code = _products_for_lines(db, lines)
    for line in lines:
        product = products_by_code.get(line.product_id)
        line.product_name = product.name if product else None


def _attach_margins(db: Session, quotation: Quotation) -> None:
    """Transient per-line + quotation-level margin, computed from Product.cost
    (PDF B3: "live margin indicator"). None when a line's product has no cost.
    """
    products_by_code = _products_for_lines(db, quotation.lines)
    total = 0.0
    any_known = False
    for line in quotation.lines:
        product = products_by_code.get(line.product_id)
        if product is None or product.cost is None:
            line.margin = None
            continue
        net_price = float(line.unit_price) * (1 - float(line.discount_pct) / 100)
        margin = (net_price - float(product.cost)) * line.qty
        line.margin = round(margin, 2)
        total += margin
        any_known = True
    quotation.total_margin = round(total, 2) if any_known else None


def _resolve_category_limit(db: Session, customer_tier: str, category: str, given: float | None) -> float:
    """category_limit_pct defaults from DiscountTier.category_limits when omitted."""
    if given is not None:
        return given
    tier = db.query(DiscountTier).filter(DiscountTier.name == customer_tier).first()
    if tier and category in (tier.category_limits or {}):
        return float(tier.category_limits[category])
    if tier:
        return float(tier.max_discount_pct)
    return 0.0


def _build_line(db: Session, quotation_id: int, customer_tier: str, line) -> QuotationLine:
    data = line.model_dump()
    data["category_limit_pct"] = _resolve_category_limit(
        db, customer_tier, data["category"], data["category_limit_pct"]
    )
    return QuotationLine(quotation_id=quotation_id, **data)


def score_and_route(db: Session, quotation: Quotation) -> Approval:
    """Shared by POST /quotations/{id}/submit and POST /portal/quotations/{id}/confirm.
    Scores the current lines, updates quotation.status, and creates an Approval
    row with the engine's reason stored in history.
    """
    lines_as_dicts = [
        {
            "product_id": line.product_id,
            "category": line.category,
            "qty": line.qty,
            "unit_price": float(line.unit_price),
            "discount_pct": float(line.discount_pct),
            "category_limit_pct": float(line.category_limit_pct),
        }
        for line in quotation.lines
    ]
    rep = db.get(User, quotation.sales_rep_id) if quotation.sales_rep_id else None
    result = score_risk(
        lines_as_dicts,
        customer_tier=quotation.customer_tier,
        rep_avg_discount_pct=_rep_avg_discount_pct(db, quotation.sales_rep_id, quotation.id),
        is_quarter_end=_is_quarter_end(quotation.created_at),
        seniority=rep.seniority if rep else None,
    )
    blended_risk = result["blended_risk"]
    flagged_lines = result["flagged_lines"]
    reason_entry = [{
        "action": "flagged", "user": "system", "reason": result.get("reason"),
        "at": datetime.now(timezone.utc).isoformat(),
    }]

    if not flagged_lines and blended_risk == "LOW":
        quotation.status = "confirmed"
        approval = Approval(
            quotation_id=quotation.id, blended_risk=blended_risk, stage="confirmed",
            history=reason_entry, flagged_lines=flagged_lines,
        )
        create_invoice_if_needed(db, quotation)
    else:
        quotation.status = "pending_approval"
        # Always start at sales_manager, whether MEDIUM or HIGH -- PDF A3's
        # approval_chain distinguishes "Sales Manager only" (MEDIUM) from
        # "Sales Manager followed by Finance" (HIGH), which only works as a
        # real two-step chain if HIGH starts here too. approvals.py's
        # decide_approval() escalates sales_manager -> finance on approve
        # when blended_risk is HIGH, and only reaches "confirmed" once
        # finance itself approves. (Fixed 2026-09-05 -- HIGH used to be
        # routed straight to "finance", skipping the manager step entirely.)
        approval = Approval(
            quotation_id=quotation.id, blended_risk=blended_risk, stage="sales_manager",
            history=reason_entry, flagged_lines=flagged_lines,
        )

    db.add(approval)
    db.flush()
    return approval


@router.post("/quotations", response_model=QuotationOut)
def create_quotation(payload: QuotationCreate, db: Session = Depends(get_db)):
    # A quotation with no real line items isn't a quotation -- reject it here
    # so an empty one can never land in the database, whatever client sent it.
    valid_lines = [l for l in payload.lines if l.product_id and l.product_id.strip() and l.qty > 0]
    if not valid_lines:
        raise HTTPException(status_code=400, detail="A quotation needs at least one line item with a product and quantity.")

    quotation = Quotation(
        customer_name=payload.customer_name,
        customer_tier=payload.customer_tier,
        status="draft",
        sales_rep_id=payload.sales_rep_id,
        expected_delivery_date=payload.expected_delivery_date,
    )
    db.add(quotation)
    db.flush()

    for line in valid_lines:
        db.add(_build_line(db, quotation.id, payload.customer_tier, line))

    db.commit()
    db.refresh(quotation)
    _attach_product_names(db, quotation.lines)
    _attach_margins(db, quotation)
    return quotation


@router.get("/quotations", response_model=list[QuotationOut])
def list_quotations(db: Session = Depends(get_db)):
    quotations = db.query(Quotation).all()
    _attach_product_names(db, [line for q in quotations for line in q.lines])
    for q in quotations:
        _attach_margins(db, q)
    return quotations


@router.get("/quotations/{id}", response_model=QuotationOut)
def get_quotation(id: int, db: Session = Depends(get_db)):
    quotation = db.get(Quotation, id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    _attach_product_names(db, quotation.lines)
    _attach_margins(db, quotation)
    return quotation


@router.patch("/quotations/{id}/lines", response_model=QuotationOut)
def update_quotation_lines(
    id: int, payload: QuotationLinesUpdate, db: Session = Depends(get_db)
):
    quotation = db.get(Quotation, id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    valid_lines = [l for l in payload.lines if l.product_id and l.product_id.strip() and l.qty > 0]
    if not valid_lines:
        raise HTTPException(status_code=400, detail="A quotation needs at least one line item with a product and quantity.")

    before = [
        {"product_id": l.product_id, "qty": l.qty, "discount_pct": float(l.discount_pct)}
        for l in quotation.lines
    ]

    db.query(QuotationLine).filter(QuotationLine.quotation_id == id).delete()
    for line in valid_lines:
        db.add(_build_line(db, id, quotation.customer_tier, line))

    db.add(AuditLog(
        entity_type="quotation", entity_id=id, user_id=payload.edited_by_user_id,
        action="edit", reason=payload.reason,
        before={"lines": before}, after={"lines": [l.model_dump() for l in valid_lines]},
    ))

    db.commit()
    db.refresh(quotation)
    _attach_product_names(db, quotation.lines)
    _attach_margins(db, quotation)
    return quotation


@router.get("/quotations/{id}/pdf")
def quotation_pdf(id: int, db: Session = Depends(get_db)):
    """PDF export of a quotation (PDF: quotations must be shareable outside
    the console). Built with reportlab so no external service/binary is
    needed -- generated on the fly from live data, never cached. Amounts are
    formatted "Rs. " (not the currency symbol) since reportlab's base
    Helvetica font has no glyph for U+20B9.
    """
    quotation = db.get(Quotation, id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    _attach_product_names(db, quotation.lines)
    _attach_margins(db, quotation)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("DealFlow360", styles["Title"]),
        Paragraph(f"Quotation Q-{quotation.id:04d}", styles["Heading2"]),
        Spacer(1, 6),
        Paragraph(f"<b>Customer:</b> {quotation.customer_name} ({quotation.customer_tier} Tier)", styles["Normal"]),
        Paragraph(f"<b>Status:</b> {quotation.status}", styles["Normal"]),
        Paragraph(f"<b>Created:</b> {quotation.created_at.strftime('%Y-%m-%d')}", styles["Normal"]),
    ]
    if quotation.expected_delivery_date:
        story.append(Paragraph(f"<b>Expected Delivery:</b> {quotation.expected_delivery_date}", styles["Normal"]))
    story.append(Spacer(1, 12))

    rows = [["Product", "Category", "Qty", "Unit Price", "Discount", "Line Total"]]
    grand_total = 0.0
    for line in quotation.lines:
        net_unit = float(line.unit_price) * (1 - float(line.discount_pct) / 100)
        line_total = round(net_unit * line.qty, 2)
        grand_total += line_total
        rows.append([
            line.product_name or line.product_id, line.category, str(line.qty),
            f"Rs. {float(line.unit_price):,.2f}", f"{float(line.discount_pct):.1f}%", f"Rs. {line_total:,.2f}",
        ])
    rows.append(["", "", "", "", "Total", f"Rs. {grand_total:,.2f}"])

    table = Table(rows, colWidths=[45 * mm, 28 * mm, 15 * mm, 28 * mm, 22 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0c5a96")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#cbd5e1")),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#0f172a")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "This document was generated by DealFlow360 and reflects live quotation data at time of export.",
        styles["Italic"],
    ))

    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="quotation-Q-{quotation.id:04d}.pdf"'},
    )


@router.post("/quotations/{id}/submit", response_model=ApprovalOut)
def submit_quotation(id: int, db: Session = Depends(get_db)):
    quotation = db.get(Quotation, id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    approval = score_and_route(db, quotation)
    db.commit()
    db.refresh(approval)
    return approval
