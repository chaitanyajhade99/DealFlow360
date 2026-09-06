from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from engines import recommend_upsell
from models import Product, Quotation, QuotationLine, UpsellRule, get_db

router = APIRouter(tags=["upsell"])


def _real_co_purchase_counts(db: Session) -> dict[tuple[str, str], int]:
    """How many past quotations actually contained both products together --
    real historical co-occurrence from live data, not a hand-picked number.
    Small enough dataset that an in-memory pass per call is fine; revisit
    with a materialized view if the quotations table gets large.
    """
    by_quotation: dict[int, set[str]] = {}
    for quotation_id, product_id in db.query(QuotationLine.quotation_id, QuotationLine.product_id).all():
        by_quotation.setdefault(quotation_id, set()).add(product_id)

    counts: dict[tuple[str, str], int] = {}
    for products in by_quotation.values():
        for source in products:
            for other in products:
                if source != other:
                    key = (source, other)
                    counts[key] = counts.get(key, 0) + 1
    return counts


@router.get("/quotations/{quotation_id}/upsell-suggestions")
def get_upsell_suggestions(quotation_id: int, db: Session = Depends(get_db)):
    """PDF B5: Upsell and Cross Sell Panel."""
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    cart_items = [line.product_id for line in quotation.lines]
    products_by_id = {p.id: p for p in db.query(Product).all()}
    products_by_code = {p.product_code: p for p in products_by_id.values()}
    co_counts = _real_co_purchase_counts(db)

    co_occurrence_data: dict[str, list[dict]] = {}
    for rule in db.query(UpsellRule).all():
        source = products_by_id.get(rule.source_product_id)
        suggested = products_by_id.get(rule.suggested_product_id)
        if not source or not suggested:
            continue
        # Real margin (price - cost), not a percentage placeholder -- this is
        # what actually drives the engine's confidence/count x margin
        # ranking. Without a real "margin" key the engine has nothing to
        # rank on and silently degrades to a likelihood-only order.
        margin = float(suggested.price) - float(suggested.cost) if suggested.cost is not None else 0.0
        co_occurrence_data.setdefault(source.product_code, []).append({
            "product_id": suggested.product_code,
            "is_promoted": suggested.is_promoted,
            "margin": margin,
            "co_purchase_count": co_counts.get((source.product_code, suggested.product_code), 0),
            "suggestion_type": rule.suggestion_type,
        })

    suggestions = recommend_upsell(cart_items, co_occurrence_data)

    enriched = []
    for s in suggestions:
        product = products_by_code.get(s.get("product_id"))
        enriched.append({
            **s,
            "name": product.name if product else None,
            "promo_tag": product.promo_tag if product else None,
        })
    return enriched
