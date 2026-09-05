from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import PriceList, Product, ProductVariant, get_db
from api.schemas import ProductIn, ProductOut

router = APIRouter(tags=["products"])


def _apply_nested(db: Session, product: Product, payload: ProductIn) -> None:
    db.query(ProductVariant).filter(ProductVariant.product_id == product.id).delete()
    for v in payload.variants:
        db.add(ProductVariant(product_id=product.id, **v.model_dump()))

    db.query(PriceList).filter(PriceList.product_id == product.id).delete()
    for pl in payload.price_lists:
        db.add(PriceList(product_id=product.id, **pl.model_dump()))


@router.post("/products", response_model=ProductOut)
def create_product(payload: ProductIn, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.product_code == payload.product_code).first():
        raise HTTPException(status_code=400, detail="product_code already exists")
    data = payload.model_dump(exclude={"variants", "price_lists"})
    product = Product(**data)
    db.add(product)
    db.flush()
    _apply_nested(db, product, payload)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@router.get("/products/{id}", response_model=ProductOut)
def get_product(id: int, db: Session = Depends(get_db)):
    product = db.get(Product, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/products/{id}", response_model=ProductOut)
def update_product(id: int, payload: ProductIn, db: Session = Depends(get_db)):
    product = db.get(Product, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    data = payload.model_dump(exclude={"variants", "price_lists"})
    for key, value in data.items():
        setattr(product, key, value)
    _apply_nested(db, product, payload)
    db.commit()
    db.refresh(product)
    return product
