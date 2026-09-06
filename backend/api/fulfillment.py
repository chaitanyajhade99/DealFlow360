from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from engines import split_warehouse
from models import FulfillmentSplit, Quotation, Warehouse, get_db
from api.deps import require_roles
from api.schemas import FulfillmentSplitOut, ManualFulfillmentLineIn

router = APIRouter(tags=["fulfillment"])

# PDF section 3 gives this specifically to Finance/Operations ("Manages
# warehouse fulfillment splits and backorder decisions"), not the Sales
# Rep, who only "tracks fulfillment progress" -- i.e. reads it. GET stays
# open to every internal role; only the override/reset mutations are gated.
_CAN_OVERRIDE = require_roles("finance", "admin")


def _warehouse_stock(warehouse: Warehouse, product_id: str) -> int:
    """Mirrors engines.fulfillment_engine._available_stock's tolerance for
    both stock shapes seen in seed data, without importing from engines/
    (kept a self-contained api-layer helper for the same reason _build_line
    resolves price itself rather than reaching into engines/ for it).
    """
    stock = warehouse.stock
    if isinstance(stock, dict):
        return max(int(stock.get(product_id) or 0), 0)
    if isinstance(stock, list):
        total = 0
        for entry in stock:
            if isinstance(entry, dict) and entry.get("product_id") == product_id:
                total += max(int(entry.get("qty") or 0), 0)
        return total
    return 0


def _backorders_for(quotation: Quotation, splits: list[dict]) -> list[dict]:
    allocated_by_product: dict[str, int] = {}
    for s in splits:
        if not s.get("is_backorder"):
            allocated_by_product[s.get("product_id")] = allocated_by_product.get(s.get("product_id"), 0) + int(s.get("qty", 0))
    backorders = []
    for line in quotation.lines:
        shortfall = line.qty - allocated_by_product.get(line.product_id, 0)
        if shortfall > 0:
            backorders.append({
                "product_id": line.product_id, "warehouse_id": None, "warehouse": "Backorder",
                "qty": shortfall, "cost": 0.0, "est_shipments": 0, "is_backorder": True,
            })
    return backorders


@router.get("/fulfillment/{quotation_id}", response_model=FulfillmentSplitOut)
def get_fulfillment(quotation_id: int, db: Session = Depends(get_db)):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    fulfillment = (
        db.query(FulfillmentSplit)
        .filter(FulfillmentSplit.quotation_id == quotation_id)
        .first()
    )

    # A rep's persisted manual override (PDF B6) is authoritative -- unlike
    # the auto-suggested split, it must NOT be silently recomputed and
    # overwritten on every GET. Only the auto-allocation path below persists
    # a fresh split on every call.
    if fulfillment and fulfillment.is_manual_override:
        fulfillment.backorders = _backorders_for(quotation, fulfillment.splits or [])
        return fulfillment

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
        for r in rows:
            if r.get("is_backorder"):
                backorders.append({**r, "product_id": line.product_id})
            else:
                all_splits.append({**r, "product_id": line.product_id})

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


@router.post("/fulfillment/{quotation_id}/override", response_model=FulfillmentSplitOut)
def override_fulfillment(
    quotation_id: int, payload: list[ManualFulfillmentLineIn], db: Session = Depends(get_db),
    _finance=Depends(_CAN_OVERRIDE),
):
    """PDF B6's "Manual Override" button, made real. Finance/Operations can
    redirect which warehouse(s) fulfill each line instead of accepting the
    suggested split -- but inventory must never become inconsistent
    (section 18): every
    allocation is checked against that warehouse's real live stock, and the
    total allocated per product can never exceed what the quotation actually
    ordered. Under-allocating is allowed -- the shortfall becomes a backorder,
    same as the auto engine.
    """
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if not payload:
        raise HTTPException(status_code=400, detail="Provide at least one allocation line")

    required_by_product = {line.product_id: line.qty for line in quotation.lines}
    warehouses_by_id = {w.id: w for w in db.query(Warehouse).all()}

    allocated_by_product: dict[str, int] = {}
    for entry in payload:
        if entry.product_id not in required_by_product:
            raise HTTPException(status_code=400, detail=f"{entry.product_id} is not a line on this quotation")
        if entry.qty < 0:
            raise HTTPException(status_code=400, detail="qty must be zero or positive")
        warehouse = warehouses_by_id.get(entry.warehouse_id)
        if not warehouse:
            raise HTTPException(status_code=404, detail=f"Warehouse {entry.warehouse_id} not found")
        available = _warehouse_stock(warehouse, entry.product_id)
        if entry.qty > available:
            raise HTTPException(
                status_code=400,
                detail=f"{warehouse.name} only has {available} unit(s) of {entry.product_id} in stock (requested {entry.qty})",
            )
        allocated_by_product[entry.product_id] = allocated_by_product.get(entry.product_id, 0) + entry.qty

    for product_id, required_qty in required_by_product.items():
        allocated = allocated_by_product.get(product_id, 0)
        if allocated > required_qty:
            raise HTTPException(
                status_code=400,
                detail=f"{product_id}: allocated {allocated} units exceeds the {required_qty} ordered",
            )

    splits = []
    for entry in payload:
        if entry.qty <= 0:
            continue
        warehouse = warehouses_by_id[entry.warehouse_id]
        cost = round(float(warehouse.shipment_fixed_cost) + float(warehouse.shipping_cost_per_unit) * entry.qty, 2)
        splits.append({
            "warehouse_id": warehouse.id, "product_id": entry.product_id, "qty": entry.qty,
            "cost": cost, "warehouse": warehouse.name, "est_shipments": 1, "is_backorder": False,
        })

    fulfillment = db.query(FulfillmentSplit).filter(FulfillmentSplit.quotation_id == quotation_id).first()
    if fulfillment:
        fulfillment.splits = splits
        fulfillment.is_manual_override = True
    else:
        fulfillment = FulfillmentSplit(quotation_id=quotation_id, splits=splits, is_manual_override=True)
        db.add(fulfillment)

    db.commit()
    db.refresh(fulfillment)
    fulfillment.backorders = _backorders_for(quotation, splits)
    return fulfillment


@router.post("/fulfillment/{quotation_id}/reset", response_model=FulfillmentSplitOut)
def reset_fulfillment(quotation_id: int, db: Session = Depends(get_db), _finance=Depends(_CAN_OVERRIDE)):
    """"Accept Suggested Split" (PDF B6) -- discards a manual override and
    goes back to the live auto-allocation engine on the next GET.
    """
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    fulfillment = db.query(FulfillmentSplit).filter(FulfillmentSplit.quotation_id == quotation_id).first()
    if fulfillment:
        fulfillment.is_manual_override = False
        db.commit()

    return get_fulfillment(quotation_id, db)
