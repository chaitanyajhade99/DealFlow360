"""Stalled deal detection (PDF B9, wireframe screen 14).

The Deal Health dashboard shows quotations that have been inactive for more
than a configured number of days. This is purely algorithmic work: compare
timestamps, apply a threshold, return a ranked list. No DB access.

Person 1 calls detect_stalled() from GET /deal-health alongside detect_anomalies().
"""

from __future__ import annotations

from datetime import datetime, timezone

# Default staleness threshold in days. Feeds the admin config screen (PDF A7)
# so the manager can tune it without a code deploy.
DEFAULT_STALE_DAYS = 7

# Statuses that are terminal — confirmed/cancelled orders are never "stalled".
TERMINAL_STATUSES = {"confirmed", "cancelled", "invoiced", "done", "closed"}


def _as_datetime(value) -> datetime | None:
    """Coerce ISO-8601 strings, epoch ints/floats, or datetime objects to UTC datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        # Try a handful of ISO-8601 variants without depending on dateutil.
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(value, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue
    return None


def _quote_label(quotation: dict) -> str:
    """Best display name for the quotation row."""
    for key in ("name", "quotation_name", "id"):
        label = quotation.get(key)
        if label is not None:
            return str(label)
    return "Unknown"


def detect_stalled(
    quotations: list[dict],
    *,
    stale_days: int = DEFAULT_STALE_DAYS,
    now: datetime | None = None,
) -> dict:
    """Return quotations that have been inactive for longer than stale_days.

    A quotation is stalled when:
      - Its status is NOT in TERMINAL_STATUSES (confirmed / cancelled / done)
      - It has been last updated more than stale_days days ago

    The result is sorted by days_stalled descending, so the most-stuck deals
    appear first on screen 14.

    Args:
        quotations: list of quotation dicts. Reads:
            - ``last_updated_at`` (or ``updated_at`` / ``write_date``) — the
              timestamp to compare. If absent the quotation is included with
              days_stalled = None and is_stalled = False.
            - ``status`` (or ``state``) — skips terminal ones.
            - ``id``, ``name``, ``quotation_name`` — for the display label.
            - ``customer_name`` (or ``partner_name``) — for the dashboard row.
            - ``amount_total`` (optional) — deal value for the dashboard.
        stale_days: keyword-only. Days of inactivity before flagging.
            Default: DEFAULT_STALE_DAYS (7).
        now: keyword-only. Override "now" for deterministic tests.
            Defaults to UTC wall clock.

    Returns:
        {
          "stalled": [           # sorted worst-first — these populate screen 14
            {
              "quotation_id": Any,         # quotation dict's id field
              "quotation_name": str,       # display label
              "customer_name": str,
              "status": str,
              "days_stalled": int,         # full days since last_updated_at
              "last_updated_at": str,      # ISO-8601 UTC, for the UI tooltip
              "amount_total": float | None,
            },
            ...
          ],
          "total_active": int,   # non-terminal quotations evaluated
          "total_stalled": int,  # how many exceeded the threshold
          "stale_days_threshold": int,
        }

    Notes:
        - A quotation with a missing or unparseable timestamp is skipped (not
          flagged), to avoid false positives from data-quality gaps.
        - TERMINAL_STATUSES is exported so the frontend can display which
          statuses were excluded without hardcoding them.
    """
    reference = now or datetime.now(tz=timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)

    stalled: list[dict] = []
    total_active = 0

    for q in quotations or []:
        # Resolve status, skip terminal ones.
        status = str(q.get("status") or q.get("state") or "").lower().strip()
        if status in TERMINAL_STATUSES:
            continue
        total_active += 1

        # Resolve last-activity timestamp.
        raw_ts = (
            q.get("last_updated_at")
            or q.get("updated_at")
            or q.get("write_date")
        )
        last_updated = _as_datetime(raw_ts)
        if last_updated is None:
            # Can't evaluate staleness without a timestamp — skip.
            continue

        elapsed_seconds = (reference - last_updated).total_seconds()
        days_stalled = int(elapsed_seconds // 86400)

        if days_stalled >= stale_days:
            customer = str(
                q.get("customer_name") or q.get("partner_name") or "Unknown"
            )
            amount = q.get("amount_total")
            try:
                amount = round(float(amount), 2) if amount is not None else None
            except (TypeError, ValueError):
                amount = None

            stalled.append(
                {
                    "quotation_id": q.get("id"),
                    "quotation_name": _quote_label(q),
                    "customer_name": customer,
                    "status": status or "draft",
                    "days_stalled": days_stalled,
                    "last_updated_at": last_updated.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "amount_total": amount,
                }
            )

    stalled.sort(key=lambda row: row["days_stalled"], reverse=True)

    return {
        "stalled": stalled,
        "total_active": total_active,
        "total_stalled": len(stalled),
        "stale_days_threshold": stale_days,
    }
