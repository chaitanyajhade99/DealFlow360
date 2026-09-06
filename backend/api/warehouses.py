from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import Warehouse, get_db
from api.deps import require_roles
from api.schemas import WarehouseIn, WarehouseOut

router = APIRouter(tags=["warehouses"])

# PDF section 3: warehouse master data (stock levels, replenishment rules,
# shipping cost config) belongs to Admin (sets it up) and Finance/Operations
# ("Manages warehouse fulfillment splits and backorder decisions") -- a
# Sales Rep only "tracks fulfillment progress" (read access to a
# quotation's own split via GET /fulfillment/{id}, which is not gated here),
# not a reason to browse the raw warehouse list.
_CAN_READ = require_roles("admin", "finance")


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
