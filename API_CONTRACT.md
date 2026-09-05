## Entities
- Quotation: id, customer_name, customer_tier, status, created_at
- QuotationLine: id, quotation_id, product_id, category, qty, unit_price, discount_pct, category_limit_pct
- Approval: id, quotation_id, blended_risk (LOW/MEDIUM/HIGH), stage, assigned_to, history[]
- Warehouse: id, name, stock[{product_id, qty}]
- FulfillmentSplit: id, quotation_id, splits[{warehouse_id, qty, cost}]
- Subscription: id, customer_name, plan, cycle, next_bill_date, status
- Invoice: id, quotation_id, amount, status, due_date

## Endpoints (Person 1 owns implementation)
POST /quotations
GET /quotations
GET /quotations/{id}
PATCH /quotations/{id}/lines
POST /quotations/{id}/submit          -> calls engines.score_risk()
POST /approvals/{id}/decision         -> approve/reject/return
GET /fulfillment/{quotation_id}       -> calls engines.split_warehouse()
POST /subscriptions
GET /invoices
GET /deal-health                      -> calls engines.detect_anomalies()

## Engine function signatures (Person 2 owns implementation, pure functions, no DB access)
score_risk(lines: list[dict]) -> {blended_risk: str, flagged_lines: list[dict]}
split_warehouse(product_id: str, qty: int, warehouses: list[dict]) -> list[{warehouse_id, qty, cost}]
detect_anomalies(rep_discount_history: list[float], current_discount: float) -> {is_anomaly: bool, z_score: float}
recommend_upsell(cart_items: list[str], co_occurrence_data: dict) -> list[{product_id, margin_delta}]