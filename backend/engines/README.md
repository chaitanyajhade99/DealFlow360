# backend/engines — algorithm layer (Person 2)

Pure functions. Plain data in, plain dict/list out. No DB access, no imports
from `backend/models/` or `backend/api/`. Every return value is JSON-serializable
as-is (no `inf`, no `NaN`, no dates, no Decimals).

```python
from backend.engines import score_risk, split_warehouse, detect_anomalies, recommend_upsell
```

| Contract function | Algorithm |
|---|---|
| `score_risk` | Deterministic rule floor **+ XGBoost escalation** (hybrid) |
| `split_warehouse` | Greedy, deepest-stock-first |
| `detect_anomalies` | Per-rep 2σ z-score |
| `recommend_upsell` | **Apriori** association rules, ranked by expected margin |

## Setup

```bash
python backend/engines/train.py                    # generate data + train both models
python backend/engines/demo.py                     # see every engine working
python -m unittest discover -s backend/engines/tests -v   # 94 tests
uvicorn backend.engines.api:app --reload           # HTTP layer -> /docs
```

## HTTP layer (`api.py`)

The engines stay pure — plain dicts in, plain dicts out, no DB, no framework.
`api.py` is the only file that knows HTTP exists, so everything above remains
directly importable and unit-testable exactly as before.

**Person 1 — mount it into your app** and the engines show up in your existing
`/docs` alongside your endpoints:

```python
from backend.engines.api import router
app.include_router(router)
```

Or run it standalone, with no database at all, to work on the engines alone:

```bash
uvicorn backend.engines.api:app --reload   # -> http://127.0.0.1:8000/docs
```

| Route | Engine | Screen |
|---|---|---|
| `POST /engines/risk/score` | `score_risk` | 6 |
| `POST /engines/fulfillment/split` | `split_warehouse` | 8 |
| `POST /engines/anomalies/detect` | `detect_anomalies` | 14 |
| `POST /engines/upsell/recommend` | `recommend_upsell` | 4 |
| `GET /engines/health` | model status + metrics | — |
| `GET /engines/config` | the tunables below | 18 (A3/A6) |

**Every route is stateless.** Nothing here touches the database — the caller
passes the rows it already loaded. That is what keeps these safe to call from
anywhere, and it means mounting the router adds no DB coupling to your app.

Two things worth knowing:

- **`co_occurrence_data` is deliberately a loose `Dict[str, List[Dict]]`.** The
  engine accepts several key spellings (`count`/`co_occurrence`,
  `margin`/`margin_delta`/`margin_impact`), and a strict Pydantic model would
  silently throw the alternates away. Pinned by `test_key_aliases_survive_the_loose_dict`.
- **`is_quarter_end` can be derived.** Pass `quote_date` (your
  `quotations.created_at`) and the route derives it as the last
  `QUARTER_END_WINDOW_DAYS` (14) of a calendar quarter. That window is a
  convention chosen in `api.py`, not something the PDF pins down — pass
  `is_quarter_end` explicitly to override it.

Built against the installed **FastAPI 0.95.2 / Pydantic v1**, so `class Config`
and `.dict()`, not `model_config` and `.model_dump()`. If the project moves to
Pydantic v2, `api.py` is the only file that needs touching.

`test_api.py` drives all of this through `TestClient`, so it exercises real
request validation and response serialization — it catches a `response_model`
that silently drops a key, which the engine unit tests structurally cannot see.

---

`train.py` takes ~5 seconds and is deterministic — same seed, same datasets,
same rules, same model. Needs `xgboost`, `scikit-learn`, `numpy`, `pandas`
(all already installed here). Apriori is implemented from scratch, so there is
no `mlxtend` dependency.

**Nothing requires the trained artifact.** With no `data/risk_model.json`,
`score_risk` runs rules-only and reports `model_available: False`; a fresh
clone never crashes. Tests skip the artifact-dependent cases automatically.

All percentages are percentage **points** (`12.0` means 12%), never fractions.

---

## Files

| File | What it is |
|---|---|
| `risk_engine.py` | `score_risk` — hybrid, and `score_rules_only` for the pure rules |
| `risk_model.py` | Feature extraction, XGBoost training, artifact load/predict |
| `apriori.py` | Frequent itemsets + association rules, written from scratch |
| `upsell_engine.py` | `recommend_upsell` — consumes Apriori output or a hand-authored dict |
| `fulfillment_engine.py` | `split_warehouse` — greedy allocation |
| `anomaly_engine.py` | `detect_anomalies` — per-rep z-score |
| `synthetic_data.py` | Dataset generators (quotes, baskets, rep histories) |
| `train.py` | CLI: generate → mine → train → save |
| `demo.py` | Runs everything, prints what each wireframe screen renders |
| `api.py` | FastAPI router + standalone app — the only file that knows HTTP |
| `data/` | Generated CSVs, mined rules, trained model (~1.4 MB, committed) |

---

## Why `score_risk` is a hybrid, not pure ML

Handing the approval decision to a black-box model alone breaks three things
the PDF asks for:

- **Section 10 states an exact expected outcome** for its worked example. A
  learned model cannot *guarantee* that; a rule can.
- **A3 requires approvals logged "with user, timestamp, and reason".** A
  softmax probability is not a reason. The rules produce the `reason` string.
- **Section 7 requires real governance logic.** A rule that always fires on a
  ceiling breach is exactly that.

But pure rules are also not enough. They only see *how far each line is over
its own ceiling*. They cannot see that the rep is junior, that the overage sits
entirely on thin-margin Service lines, that it is quarter end, or that the deal
is ten times the usual size.

So: **rules set the floor, the model may escalate above it, and the model can
never lower it.**

```
final_band = max(rule_band, model_band if model_confidence >= 0.55 else LOW)
```

The gate matters — below `MODEL_ESCALATION_MIN_CONFIDENCE` the model is
guessing, and a spurious escalation wastes a manager's time.

Measured on 1500 held-out quotes: the model escalates **~12%**, and **77 of
those had zero flagged lines** — quotes where every line was inside its
ceiling and the rules had nothing at all to say. Demo case `[4]` is one of
them (`Q-00017`: 187k deal, junior rep, value concentrated in Subscription at
9.18% against a 10% ceiling; rules `LOW`, model `MEDIUM` at 0.92 confidence,
and the generator's own latent label for it was `HIGH`).

`score_risk(lines, use_model=False)` gives the pure rule engine. That is what
the deterministic tests assert against, so retraining can never silently move
them.

### The rules themselves (PDF section 10)

Two independent rules, worse one wins:

1. **Worst single line** — one line ≥ `SINGLE_LINE_HIGH_PCT` (5) points over
   its own ceiling flags the whole quote. This is the PDF's worked example.
2. **Blended overage** — line-value-weighted average overage across the order,
   HIGH at `BLENDED_HIGH_PCT` (3) points. This is the PDF's "why blended?"
   case: 2 over, 3 over, 2 over.

Neither alone is enough. In the PDF's own example the blend is only **1.14**
points — the large clean Laptop line dilutes the bad Service line — so rule 2
alone would pass it. And rule 1 alone is just `max()`, which the "why blended?"
paragraph says is insufficient.

### Model features

13 features, order pinned in `risk_model.FEATURE_NAMES` (training and inference
both go through `features_to_vector`, so they cannot drift):

`blended_overage_pct`, `worst_line_overage_pct`, `n_lines`, `n_flagged_lines`,
`flagged_value_share`, `log_total_value`, `thin_margin_value_share`,
`tier_ordinal`, `avg_discount_pct`, `max_discount_pct`, `seniority`,
`is_quarter_end`, `discount_vs_rep_baseline`.

Unknown context (no tier, a rep with no history) becomes **NaN**, not a guessed
zero — zero would mean "Bronze" and "junior", a confident lie. XGBoost learns a
default branch direction for missing values natively.

Held-out performance: **accuracy 0.876, macro F1 0.845** (3200 train / 800
test). Top gain: `blended_overage_pct` 11.18, `worst_line_overage_pct` 9.55,
then `log_total_value` 3.13, `seniority` 3.05, `is_quarter_end` 2.66 — the
contextual features the rules cannot see are exactly where the model earns its
place.

---

## Apriori cross-sell

`apriori.py` implements the real algorithm, level-wise with the downward-closure
prune: an itemset can only be frequent if every subset is frequent, so
candidates with an infrequent subset are dropped before being counted.
`test_apriori.py` asserts that invariant directly across the whole result.

```
confidence = support(A ∪ C) / support(A)     P(consequent | antecedent)
lift       = confidence / support(C)         vs the consequent's base rate
```

**Lift is the one that matters.** Confidence alone happily recommends a product
that appears in most baskets regardless of the cart — high confidence, lift ≈ 1,
no actual signal. `build_co_occurrence` drops anything below lift 1.05, so every
suggestion beats its own base rate.

Ranking in `recommend_upsell` adapts to its input:

| Data source | Basis | Score |
|---|---|---|
| Apriori (`confidence` present) | `confidence_x_margin` | confidence × margin × promo boost |
| Hand-authored dict | `count_x_margin` | count × margin × promo boost |
| No margin anywhere | `confidence_only` / `count_only` | likelihood alone × promo boost |

The last row is the **degraded** ranking. `products` has no margin column yet,
so every suggestion can arrive with margin `0.0` — and multiplying by that
would zero every score and collapse the sort onto its `product_id` tiebreak,
returning alphabetical order that looks like a ranking. When no suggestion
carries a usable margin the engine ranks on likelihood alone and says so in
`ranking_basis`, so a caller can tell a degraded ranking from a real one.
Once `products.margin` exists this path stops firing on its own.

Expected margin is the right ranking for a rep: *"60% of laptop baskets also
took the dock, and the dock earns 50 — so suggesting it is worth ~30."* On the
mined data the Wireless Mouse has the **highest** confidence (0.643) and still
ranks third, because 64% of a 5.00 margin loses to 60% of a 50.00 margin. Raw
count would have put it first.

Mining recovers the associations the generator planted (`SERVER-01 →
RACK/INSTALL/SUPPORT`, `LAPTOP-01 → MOUSE/DOCK/WARRANTY`) from raw baskets
alone, with no knowledge of how they were made — that is what
`test_recovers_the_planted_associations` checks.

Multi-item antecedents ("laptop AND monitor together imply a dock") are mined
and available in `generate_rules`, but `build_co_occurrence` keeps only
single-item antecedents because `recommend_upsell` looks up one cart product at
a time per the contract. Wiring the multi-item ones into the cart lookup is the
obvious next improvement.

---

## Synthetic data

`synthetic_data.py`, all deterministic under a seed. 14-product catalogue with
categories, prices, margins and promotion flags.

**The labels are deliberately not the rule.** Labelling each quote with the
deterministic rule and then training a model to re-learn that rule would be
circular — the model would add nothing. So the label comes from a richer latent
process (`_latent_risk`) that weights overage by how thin the category's margin
is, scales with deal size, and forgives senior reps on strategic accounts, plus
label noise because human approvers are not perfectly consistent. The rule sees
only line-level overage; the model gets the context. That gap is the whole
reason the hybrid is worth building.

Line ceilings use `min(category ceiling, tier ceiling)` — exactly the PDF's
Gold/Hardware/Service example, where a Gold customer still only gets 10% on
Service lines.

Basket generation plants known associations at known probabilities so Apriori's
output can be checked against ground truth rather than eyeballed.

---

## Contract deltas — please read

I did **not** edit `API_CONTRACT.md`. Every signature and key named there is
implemented exactly as written. Below are **additive keys and keyword-only
arguments** on top — nothing renamed or removed, so existing call sites keep
working. Flagging them so we can fold them into the contract if the team agrees.

| Function | Contract says | Also returns / accepts | Why |
|---|---|---|---|
| `score_risk` | `{blended_risk, flagged_lines}` | `blended_score_pct`, `worst_line_over_pct`, `total_line_value`, `approval_chain`, `reason`, `rule_risk`, `model_risk`, `model_confidence`, `model_probabilities`, `model_available`, `escalated_by_model`; kwargs `customer_tier`, `rep_avg_discount_pct`, `is_quarter_end`, `seniority`, `use_model` | Screen 6 shows score + approval steps; `reason` is A3's audit requirement; the `model_*` keys make the escalation explainable |
| `split_warehouse` | `[{warehouse_id, qty, cost}]` | `warehouse`, `est_shipments`, `is_backorder` | Screen 8 columns |
| `detect_anomalies` | `{is_anomaly, z_score}` | `mean`, `stddev`, `threshold`, `current_discount`, `sample_size` | Screen 14's card reads "18% vs rep avg 5.7%" |
| `recommend_upsell` | `[{product_id, margin_delta}]` | `co_purchase_count`, `score`, `ranking_basis`, `confidence`, `lift`, `expected_margin`, `is_promoted`, `promo_tag`, `product_name`; kwargs `min_margin`, `min_lift`, `limit` | Screen 4 needs the promo tag; confidence/lift come from Apriori |

**Person 1 — two things to handle:**

1. **`split_warehouse` returns a backorder row** when stock cannot cover the
   qty (`is_backorder: True`, `warehouse_id: None`). Filter it before
   persisting `FulfillmentSplit.splits`:

   ```python
   rows      = split_warehouse(product_id, qty, warehouses)
   splits    = [r for r in rows if not r["is_backorder"]]
   backorder = next((r for r in rows if r["is_backorder"]), None)   # drives B6
   ```

   `is_backorder` is on **every** row, so `row["is_backorder"]` never raises.

2. **Pass model context to `score_risk` when you have it.** It works without,
   but the model is materially better with it:

   ```python
   score_risk(
       lines,
       customer_tier=quotation.customer_tier,
       rep_avg_discount_pct=rep_baseline,     # mean of rep_histories.json
       is_quarter_end=is_quarter_end(today),
       seniority=rep.seniority,
   )
   ```

   Store `result["reason"]` on the Approval record — that is A3's "reason"
   field, already written in plain language.

---

## Screen field mapping

**Screen 6 — "Why This Quote Was Flagged"** (`score_risk().flagged_lines`).
`risk_engine.FLAGGED_LINE_COLUMNS` exports this mapping so the header row lives
in one place:

| Column | Key |
|---|---|
| Line | `line` |
| Discount Given | `discount_given_pct` |
| Limit Allowed | `limit_allowed_pct` |
| Over By | `over_by_pct` |

Rows sort worst-overage-first. Each also carries `line_id`, `product_id`,
`category`, `line_value` for linking back.

Note a model escalation can produce a **`HIGH` band with an empty
`flagged_lines`** — that is the interesting case, not a bug. Render
`reason` and `escalated_by_model` so the manager knows why they were called in.

**Screen 8 — fulfillment split** (`split_warehouse()`): Warehouse → `warehouse`,
Qty Fulfilled → `qty`, Est. Shipments → `est_shipments`, Cost → `cost`.
`est_shipments` is 1 per sourcing warehouse; the order-level total is the count
of non-backorder rows.

**Screen 14 — "Discount Anomalies"** (`detect_anomalies()`): `is_anomaly` gates
the card, `current_discount` vs `mean` is the headline, `z_score` is severity,
`sample_size` lets you say "not enough history yet" instead of implying a quote
is clean.

**Screen 4 — upsell cards** (`recommend_upsell()`): product → `product_name`,
margin delta → `margin_delta`, promo tag → `promo_tag` (`None` when not
promoted). With Apriori data, `confidence` supports "62% of laptop buyers also
take this". Already-quoted products are never suggested back.

---

## Other design decisions

**Fail-closed on missing data.** A line with no `category_limit_pct` is scored
against a 0% ceiling, so it flags rather than silently passing. Constant:
`DEFAULT_CATEGORY_LIMIT_PCT`.

**Category names are folded before matching.** The database stores
`"Services"`; these engines were written against `"Service"`. A plain set
membership test missed every Services line and silently scored
`thin_margin_value_share` as 0.0 on real data — no error, just a dead feature
(6th by gain). `risk_model._normalise_category` lowercases and drops a
trailing plural, so either spelling scores identically. Pinned by
`TestCategoryNaming`.

**Line weighting uses gross list value** (`qty * unit_price`) — the revenue
exposed at that discount, not post-discount net.

**Warehouse greedy is deepest-stock-first**, which is what minimises shipments:
if one warehouse can cover the qty it wins outright and you get a single row.
Ties break on cheaper per-unit shipping, then warehouse id, so identical inputs
always produce identical splits. `cost = shipment_fixed_cost +
shipping_cost_per_unit * qty` (both default 0.0; `shipping_cost_weight` /
`shipping_fixed_cost` accepted as aliases).

**Anomaly detection is per-rep, sample stddev** (n−1) — a rep's past quotes are
a sample of behaviour, not a population. 18% is routine for one rep and
alarming for another. Fewer than 2 history entries → never an anomaly (a new
rep has no baseline). Zero-variance history → true z is infinite, which is not
valid JSON, so `Z_SCORE_CAP` (99.0) is reported.

**Inference never breaks quoting.** A corrupt artifact, a version mismatch, or
any exception during prediction degrades to rules-only rather than failing the
request.

---

## Tunables

All exported from `backend.engines`, so the config screens (PDF A3/A6) can
display or override them without touching engine code.

| Constant | Default | Meaning |
|---|---|---|
| `SINGLE_LINE_HIGH_PCT` | 5.0 | One line this far over its ceiling → HIGH |
| `BLENDED_HIGH_PCT` | 3.0 | Value-weighted average overage → HIGH |
| `DEFAULT_CATEGORY_LIMIT_PCT` | 0.0 | Ceiling assumed when a line omits one |
| `MODEL_ESCALATION_MIN_CONFIDENCE` | 0.55 | Model must clear this to escalate |
| `Z_THRESHOLD` | 2.0 | Sigmas above a rep's mean before it's an anomaly |
| `Z_SCORE_CAP` | 99.0 | Reported when history has zero variance |
| `PROMOTION_BOOST` | 1.25 | Score multiplier for promoted upsells |
| `DEFAULT_MIN_SUPPORT` | 0.02 | Apriori: minimum itemset support |
| `DEFAULT_MIN_CONFIDENCE` | 0.25 | Apriori: minimum rule confidence |
| `DEFAULT_MIN_LIFT` | 1.05 | Apriori: minimum lift (keep above 1.0) |
