from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from engines import split_warehouse
from models import FulfillmentSplit, Quotation, Warehouse, get_db
from api.schemas import FulfillmentSplitOut

router = APIRouter(tags=["fulfillment"])


@router.get("/fulfillment/{quotation_id}", response_model=FulfillmentSplitOut)
def get_fulfillment(quotation_id: int, db: Session = Depends(get_db)):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    warehouses_as_dicts = [
        {
            "id": wh.id, "name": wh.name, "stock": wh.stock,
            "shipping_cost_per_unit": float(wh.shipping_cost_per_unit),
            "shipment_fixed_cost": float(wh.shipment_fixed_cost),
        }
        for wh in db.query(Warehouse).all()
    ]

    all_splits = []
    backorders = []
    for line in quotation.lines:
        rows = split_warehouse(line.product_id, line.qty, warehouses_as_dicts)
        all_splits.extend(r for r in rows if not r.get("is_backorder"))
        backorder = next((r for r in rows if r.get("is_backorder")), None)
        if backorder:
            backorders.append({**backorder, "product_id": line.product_id})

    fulfillment = (
        db.query(FulfillmentSplit)
        .filter(FulfillmentSplit.quotation_id == quotation_id)
        .first()
    )
    if fulfillment:
        fulfillment.splits = all_splits
    else:
        fulfillment = FulfillmentSplit(quotation_id=quotation_id, splits=all_splits)
        db.add(fulfillment)

    db.commit()
    db.refresh(fulfillment)
    # Transient, not persisted — drives the "Consolidate Remaining Backorder" prompt (wireframe B6).
    fulfillment.backorders = backorders
    return fulfillment
