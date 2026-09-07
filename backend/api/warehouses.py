from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import Warehouse, get_db
from api.deps import require_roles
from api.fulfillment import resync_backorders_for_product
from api.schemas import RestockIn, WarehouseIn, WarehouseOut

router = APIRouter(tags=["warehouses"])

# PDF section 3: warehouse master data (stock levels, replenishment rules,
# shipping cost config) belongs to Admin (sets it up) and Finance/Operations
# ("Manages warehouse fulfillment splits and backorder decisions") -- a
# Sales Rep only "tracks fulfillment progress" (read access to a
# quotation's own split via GET /fulfillment/{id}, which is not gated here),
# not a reason to browse the raw warehouse list.
_CAN_READ = require_roles("admin", "finance")
# Receiving inventory is a Finance/Operations "backorder decision" as much
# as it is Admin config, so both can do it -- unlike the full warehouse
# create/update below, which stays Admin-only (that's platform setup, not
# day-to-day stock handling).
_CAN_RESTOCK = require_roles("admin", "finance")


@router.post("/warehouses", response_model=WarehouseOut)
def create_warehouse(payload: WarehouseIn, db: Session = Depends(get_db), _admin=Depends(require_roles("admin"))):
    warehouse = Warehouse(**payload.model_dump())
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db), _=Depends(_CAN_READ)):
    return db.query(Warehouse).all()


@router.get("/warehouses/{id}", response_model=WarehouseOut)
def get_warehouse(id: int, db: Session = Depends(get_db), _=Depends(_CAN_READ)):
    warehouse = db.get(Warehouse, id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse


@router.patch("/warehouses/{id}", response_model=WarehouseOut)
def update_warehouse(id: int, payload: WarehouseIn, db: Session = Depends(get_db), _admin=Depends(require_roles("admin"))):
    warehouse = db.get(Warehouse, id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    for key, value in payload.model_dump().items():
        setattr(warehouse, key, value)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.post("/warehouses/{id}/restock", response_model=WarehouseOut)
def restock_warehouse(id: int, payload: RestockIn, db: Session = Depends(get_db), _=Depends(_CAN_RESTOCK)):
    """"Receive inventory" -- adds to whatever is already on hand (unlike
    the raw-overwrite PATCH above), then tries to auto-resolve any open
    backorders on this product across every affected quotation, since that's
    the whole point of restocking: PDF section 3's "backorder decisions".
    """
    warehouse = db.get(Warehouse, id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    # Every entry is rebuilt as a brand-new dict, never mutated in place:
    # SQLAlchemy's dirty-checking for a plain JSON column compares the new
    # value against the currently-loaded one, and if an existing dict is
    # mutated before being reassigned, both sides of that comparison end up
    # pointing at the same (already-changed) object -- `is_modified()` then
    # sees no difference and silently skips the write entirely.
    old_stock = warehouse.stock
    if isinstance(old_stock, dict):
        stock = dict(old_stock)
        stock[payload.product_id] = int(stock.get(payload.product_id, 0)) + payload.qty
    else:
        found = False
        stock = []
        for entry in old_stock or []:
            if isinstance(entry, dict) and entry.get("product_id") == payload.product_id:
                stock.append({**entry, "qty": int(entry.get("qty", 0)) + payload.qty})
                found = True
            else:
                stock.append(dict(entry) if isinstance(entry, dict) else entry)
        if not found:
            stock.append({"product_id": payload.product_id, "qty": payload.qty})
    warehouse.stock = stock
    db.commit()
    db.refresh(warehouse)

    resync_backorders_for_product(db, payload.product_id)
    return warehouse
