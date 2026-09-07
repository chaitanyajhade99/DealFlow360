from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from engines import split_warehouse
from models import Backorder, FulfillmentSplit, Quotation, Warehouse, get_db
from api.deps import require_roles
from api.schemas import BackorderOut, FulfillmentSplitOut, ManualFulfillmentLineIn

router = APIRouter(tags=["fulfillment"])

# PDF section 3 gives this specifically to Finance/Operations ("Manages
# warehouse fulfillment splits and backorder decisions"), not the Sales
# Rep, who only "tracks fulfillment progress" -- i.e. reads it. GET stays
# open to every internal role; only the override/reset mutations are gated.
_CAN_OVERRIDE = require_roles("finance", "admin")
_CAN_READ_BACKORDERS = require_roles("finance", "admin")


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


def _reserved_by_others(db: Session, quotation_id: int) -> dict[tuple[int, str], int]:
    """Units of (warehouse, product) other quotations' persisted splits have
    already claimed. Physical `Warehouse.stock` is never decremented (the
    engine that reads it belongs to Person 2, and mutating shared JSON on
    every read is its own hazard); instead, "available" is computed as raw
    stock minus what's already spoken for elsewhere, so two quotations can
    never both be handed the same physical units out of one warehouse --
    that double-allocation was a real, unguarded gap before this.
    """
    reserved: dict[tuple[int, str], int] = {}
    others = db.query(FulfillmentSplit).filter(FulfillmentSplit.quotation_id != quotation_id).all()
    for f in others:
        for s in f.splits or []:
            wh_id = s.get("warehouse_id")
            if s.get("is_backorder") or not wh_id:
                continue
            key = (wh_id, s.get("product_id"))
            reserved[key] = reserved.get(key, 0) + int(s.get("qty", 0))
    return reserved


def _effective_stock(warehouse: Warehouse, product_id: str, reserved: dict[tuple[int, str], int]) -> int:
    held = reserved.get((warehouse.id, product_id), 0)
    return max(_warehouse_stock(warehouse, product_id) - held, 0)


def _effective_stock_list(warehouse: Warehouse, reserved: dict[tuple[int, str], int]) -> list[dict]:
    """Normalizes warehouse.stock (dict or list shape) into the list shape
    the fulfillment engine expects, with each product's qty reduced by
    whatever's already reserved for other quotations."""
    raw = warehouse.stock
    product_ids: set[str] = set()
    if isinstance(raw, dict):
        product_ids.update(raw.keys())
    elif isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict) and entry.get("product_id"):
                product_ids.add(entry["product_id"])
    return [
        {"product_id": pid, "qty": _effective_stock(warehouse, pid, reserved)}
        for pid in product_ids
    ]


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


def _sync_backorders(db: Session, quotation: Quotation, backorder_rows: list[dict]) -> None:
    """Keeps the persisted, cross-quotation-queryable Backorder table (see
    models/warehouse.py) in step with whatever the live computation just
    found: open a row for every product still short, update the qty on one
    that already exists, and resolve any that are no longer short.
    """
    shortfall_by_product = {b["product_id"]: b["qty"] for b in backorder_rows}
    existing = {
        b.product_id: b
        for b in db.query(Backorder)
        .filter(Backorder.quotation_id == quotation.id, Backorder.status == "open")
        .all()
    }
    for product_id, qty in shortfall_by_product.items():
        row = existing.pop(product_id, None)
        if row:
            row.qty = qty
        else:
            db.add(Backorder(quotation_id=quotation.id, product_id=product_id, qty=qty, status="open"))
    for row in existing.values():
        row.status = "resolved"
        row.resolved_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/backorders", response_model=list[BackorderOut])
def list_backorders(db: Session = Depends(get_db), _=Depends(_CAN_READ_BACKORDERS)):
    """PDF section 3's "backorder decisions" need something to decide on
    across the whole book of business, not just one quotation at a time --
    this is that report.
    """
    rows = (
        db.query(Backorder)
        .filter(Backorder.status == "open")
        .order_by(Backorder.created_at.desc())
        .all()
    )
    out = []
    for row in rows:
        quotation = db.get(Quotation, row.quotation_id)
        out.append(BackorderOut(
            id=row.id, quotation_id=row.quotation_id, product_id=row.product_id,
            qty=row.qty, status=row.status, created_at=row.created_at,
            customer_name=quotation.customer_name if quotation else None,
            quotation_status=quotation.status if quotation else None,
        ))
    return out


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
        _sync_backorders(db, quotation, fulfillment.backorders)
        return fulfillment

    reserved = _reserved_by_others(db, quotation_id)
    warehouses_as_dicts = [
        {
            "id": wh.id, "name": wh.name, "stock": _effective_stock_list(wh, reserved),
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
    _sync_backorders(db, quotation, backorders)
    return fulfillment


@router.post("/fulfillment/{quotation_id}/override", response_model=FulfillmentSplitOut)
def override_fulfillment(
    quotation_id: int, payload: list[ManualFulfillmentLineIn], db: Session = Depends(get_db),
    _finance=Depends(_CAN_OVERRIDE),
):
    """PDF B6's "Manual Override" button, made real. Finance/Operations can
    redirect which warehouse(s) fulfill each line instead of accepting the
    suggested split -- but inventory must never become inconsistent
    (section 18): every allocation is checked against that warehouse's real
    stock net of whatever every OTHER quotation has already been allocated
    (not just raw on-hand stock, which would let two orders claim the same
    units), and the total allocated per product can never exceed what the
    quotation actually ordered. Under-allocating is allowed -- the shortfall
    becomes a backorder, same as the auto engine.
    """
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if not payload:
        raise HTTPException(status_code=400, detail="Provide at least one allocation line")

    required_by_product = {line.product_id: line.qty for line in quotation.lines}
    warehouses_by_id = {w.id: w for w in db.query(Warehouse).all()}
    reserved = _reserved_by_others(db, quotation_id)

    allocated_by_product: dict[str, int] = {}
    for entry in payload:
        if entry.product_id not in required_by_product:
            raise HTTPException(status_code=400, detail=f"{entry.product_id} is not a line on this quotation")
        if entry.qty < 0:
            raise HTTPException(status_code=400, detail="qty must be zero or positive")
        warehouse = warehouses_by_id.get(entry.warehouse_id)
        if not warehouse:
            raise HTTPException(status_code=404, detail=f"Warehouse {entry.warehouse_id} not found")
        available = _effective_stock(warehouse, entry.product_id, reserved)
        if entry.qty > available:
            raise HTTPException(
                status_code=400,
                detail=f"{warehouse.name} only has {available} unit(s) of {entry.product_id} available (requested {entry.qty})",
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
    _sync_backorders(db, quotation, fulfillment.backorders)
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


def resync_backorders_for_product(db: Session, product_id: str) -> int:
    """Called after a warehouse restock (api/warehouses.py) -- for every
    quotation with an open, non-manual-override backorder on this product,
    recompute its suggested split against the now-larger available pool and
    refresh the persisted Backorder row. A manual override is left alone
    (it's Finance's frozen, authoritative choice; they re-run it themselves
    if they want to reconsider it). Returns how many quotations were
    actually recomputed, for the caller's toast.
    """
    open_rows = (
        db.query(Backorder)
        .filter(Backorder.product_id == product_id, Backorder.status == "open")
        .all()
    )
    touched = 0
    for row in open_rows:
        fulfillment = db.query(FulfillmentSplit).filter(FulfillmentSplit.quotation_id == row.quotation_id).first()
        if fulfillment and fulfillment.is_manual_override:
            continue
        if not db.get(Quotation, row.quotation_id):
            continue
        get_fulfillment(row.quotation_id, db)
        touched += 1
    return touched
