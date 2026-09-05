"""FastAPI app entrypoint. Run from the backend/ directory:

    uvicorn api.main:app --reload
"""
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from models import Base, engine
from api import (
    admin,
    approvals,
    auth,
    dashboard,
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
from api.deps import get_current_internal_user

app = FastAPI(
    title="DealFlow360 API",
    description="Sales Operations platform backend (Person 1: models, api, seed)",
    version="0.3.0",
)

# Frontend integration: without this, every browser-based call from Person
# 3's app (a different origin than this API) is blocked by the browser
# before it ever reaches FastAPI. CORS_ORIGINS accepts a comma-separated list
# for deployment; defaults to "*" for local hackathon development.
_cors_origins = os.environ.get("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _cors_origins == "*" else _cors_origins.split(","),
    allow_credentials=_cors_origins != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Additive-only migration for columns added after the tables already existed
# in deployed databases (local + the shared Supabase team DB) -- create_all
# only creates missing tables, it never ALTERs existing ones.
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'approved'"))

# /auth and /portal issue tokens, so they stay open. Every other router is
# internal-workspace-only (PDF A1: "after login, internal users can access
# backend configuration and open a sales workspace") and now requires a
# valid internal-type JWT via Authorization: Bearer <token>.
_internal = [Depends(get_current_internal_user)]

app.include_router(quotations.router, dependencies=_internal)
app.include_router(approvals.router, dependencies=_internal)
app.include_router(fulfillment.router, dependencies=_internal)
app.include_router(subscriptions.router, dependencies=_internal)
app.include_router(invoices.router, dependencies=_internal)
app.include_router(deal_health.router, dependencies=_internal)
app.include_router(discount_tiers.router, dependencies=_internal)
app.include_router(auth.router)
app.include_router(portal.router)
app.include_router(upsell.router, dependencies=_internal)
app.include_router(warehouses.router, dependencies=_internal)
app.include_router(products.router, dependencies=_internal)
app.include_router(reports.router, dependencies=_internal)
app.include_router(dashboard.router, dependencies=_internal)
app.include_router(admin.router, dependencies=_internal)


@app.get("/health")
def health():
    return {"status": "ok"}
