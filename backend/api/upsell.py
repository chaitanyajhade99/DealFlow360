from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from engines import recommend_upsell
from models import Product, Quotation, UpsellRule, get_db

router = APIRouter(tags=["upsell"])


@router.get("/quotations/{quotation_id}/upsell-suggestions")
def get_upsell_suggestions(quotation_id: int, db: Session = Depends(get_db)):
    """PDF B5: Upsell and Cross Sell Panel."""
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    cart_items = [line.product_id for line in quotation.lines]
    products_by_id = {p.id: p for p in db.query(Product).all()}
    products_by_code = {p.product_code: p for p in products_by_id.values()}

    co_occurrence_data: dict[str, list[dict]] = {}
    for rule in db.query(UpsellRule).all():
        source = products_by_id.get(rule.source_product_id)
        suggested = products_by_id.get(rule.suggested_product_id)
        if not source or not suggested:
            continue
        co_occurrence_data.setdefault(source.product_code, []).append({
            "product_id": suggested.product_code,
            "is_promoted": suggested.is_promoted,
            "min_margin_pct": float(rule.min_margin_pct),
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
