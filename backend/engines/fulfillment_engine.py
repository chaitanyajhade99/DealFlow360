"""Multi-warehouse fulfillment splitting (PDF A4 / B6).

Pure function layer. No DB access, no imports from models/ or api/.
Person 1 calls split_warehouse() from GET /fulfillment/{quotation_id}.
"""

from __future__ import annotations

# Shipping cost keys read off each warehouse dict, with the aliases seed data
# tends to use. All default to 0.0 when absent, so a warehouse with no cost
# config still allocates -- it just costs nothing.
_PER_UNIT_KEYS = ("shipping_cost_per_unit", "shipping_cost_weight")
_FIXED_KEYS = ("shipment_fixed_cost", "shipping_fixed_cost")


def _as_float(value, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _first_present(warehouse: dict, keys, default: float = 0.0) -> float:
    for key in keys:
        if warehouse.get(key) is not None:
            return _as_float(warehouse[key], default)
    return default


def _available_stock(warehouse: dict, product_id: str) -> int:
    """Read on-hand qty for one product.

    Tolerates both stock shapes seen in seed data:
      - API_CONTRACT form: [{"product_id": "P1", "qty": 10}, ...]
      - shorthand map:     {"P1": 10, ...}
    Negative or unparseable quantities clamp to 0.
    """
    stock = warehouse.get("stock")
    if isinstance(stock, dict):
        return max(_as_int(stock.get(product_id)), 0)
    if isinstance(stock, list):
        total = 0
        for entry in stock:
            if isinstance(entry, dict) and entry.get("product_id") == product_id:
                total += max(_as_int(entry.get("qty")), 0)
        return total
    return 0


def split_warehouse(product_id: str, qty: int, warehouses: list[dict]) -> list[dict]:
    """Allocate one product across warehouses, fewest shipments first.

    Greedy: sort by available stock DESCENDING and fill from the deepest
    warehouse first. Because the deepest warehouse goes first, a single
    warehouse that can cover the whole order produces exactly one row -- the
    split only happens when no single warehouse can cover qty, which is the
    "minimise number of shipments" weighting from PDF A4.

    Ties in stock break on cheaper per-unit shipping, then warehouse id, so
    the same inputs always produce the same split (demos and tests stay stable).

    Args:
        product_id: product being fulfilled.
        qty: units required. <= 0 returns [].
        warehouses: Warehouse dicts. Reads id, name, stock, and optionally
            shipping_cost_per_unit (alias shipping_cost_weight) and
            shipment_fixed_cost (alias shipping_fixed_cost).

    Returns:
        List of allocation rows, deepest warehouse first, carrying the screen-8
        columns (Warehouse / Qty Fulfilled / Est. Shipments / Cost):
        {
          "warehouse_id": Any,      # API_CONTRACT key
          "qty": int,               # API_CONTRACT key -- "Qty Fulfilled"
          "cost": float,            # API_CONTRACT key -- "Cost"
          "warehouse": str,         # "Warehouse" (display name)
          "est_shipments": int,     # "Est. Shipments"
          "is_backorder": bool,
        }

        If stock cannot cover qty, a final row with is_backorder=True,
        warehouse_id=None and est_shipments=0 carries the shortfall -- this is
        what drives B6's "Consolidate Remaining Backorder" prompt. Person 1
        should filter `if not row["is_backorder"]` before persisting
        FulfillmentSplit.splits. The key is present on every row, so a plain
        row["is_backorder"] never raises.

    Notes:
        - est_shipments is 1 per sourcing warehouse; the order-level shipment
          count is the number of non-backorder rows.
        - cost = shipment_fixed_cost + (shipping_cost_per_unit * qty allocated).
        - Warehouses with zero stock for this product are skipped entirely.
    """
    needed = _as_int(qty)
    if needed <= 0:
        return []

    candidates = []
    for warehouse in warehouses or []:
        available = _available_stock(warehouse, product_id)
        if available <= 0:
            continue
        candidates.append(
            {
                "warehouse": warehouse,
                "available": available,
                "per_unit": _first_present(warehouse, _PER_UNIT_KEYS),
                "fixed": _first_present(warehouse, _FIXED_KEYS),
            }
        )

    # Deepest stock first; cheapest shipping, then id, as deterministic tiebreaks.
    candidates.sort(
        key=lambda c: (-c["available"], c["per_unit"], str(c["warehouse"].get("id", "")))
    )

    allocations: list[dict] = []
    remaining = needed

    for candidate in candidates:
        if remaining <= 0:
            break
        take = min(candidate["available"], remaining)
        remaining -= take
        warehouse = candidate["warehouse"]
        cost = candidate["fixed"] + candidate["per_unit"] * take
        allocations.append(
            {
                "warehouse_id": warehouse.get("id"),
                "qty": take,
                "cost": round(cost, 2),
                "warehouse": warehouse.get("name") or str(warehouse.get("id", "Unknown")),
                "est_shipments": 1,
                "is_backorder": False,
            }
        )

    if remaining > 0:
        allocations.append(
            {
                "warehouse_id": None,
                "qty": remaining,
                "cost": 0.0,
                "warehouse": "Backorder",
                "est_shipments": 0,
                "is_backorder": True,
            }
        )

    return allocations
