"""FastAPI app entrypoint. Run from the backend/ directory:

    uvicorn api.main:app --reload
"""
from fastapi import FastAPI

from models import Base, engine
from api import (
    approvals,
    auth,
    deal_health,
    discount_tiers,
    fulfillment,
    invoices,
    portal,
    products,
    quotations,
    reports,
    subscriptions,
    upsell,
    warehouses,
)

app = FastAPI(
    title="DealFlow360 API",
    description="Sales Operations platform backend (Person 1: models, api, seed)",
    version="0.2.0",
)

Base.metadata.create_all(bind=engine)

app.include_router(quotations.router)
app.include_router(approvals.router)
app.include_router(fulfillment.router)
app.include_router(subscriptions.router)
app.include_router(invoices.router)
app.include_router(deal_health.router)
app.include_router(discount_tiers.router)
app.include_router(auth.router)
app.include_router(portal.router)
app.include_router(upsell.router)
app.include_router(warehouses.router)
app.include_router(products.router)
app.include_router(reports.router)


@app.get("/health")
def health():
    return {"status": "ok"}
