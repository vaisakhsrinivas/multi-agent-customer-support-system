"""Return policy and in-memory return records (aligns with seeded order UUIDs)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

RETURN_WINDOW_DAYS = 30

_RETURNS: list[dict[str, Any]] = []


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _demo_orders() -> dict[str, dict[str, Any]]:
    now = _utcnow()
    return {
        "bbbbbbbb-0001-4000-8000-000000000001": {
            "customer_email": "ava.chen@example.com",
            "status": "delivered",
            "placed_at": now - timedelta(days=10),
            "currency": "USD",
            "total_cents": 4999,
        },
        "bbbbbbbb-0001-4000-8000-000000000002": {
            "customer_email": "ava.chen@example.com",
            "status": "shipped",
            "placed_at": now - timedelta(days=3),
            "currency": "USD",
            "total_cents": 12900,
        },
        "bbbbbbbb-0001-4000-8000-000000000005": {
            "customer_email": "ben.ortiz@example.com",
            "status": "cancelled",
            "placed_at": now - timedelta(days=40),
            "currency": "USD",
            "total_cents": 1500,
        },
        "bbbbbbbb-0001-4000-8000-000000000008": {
            "customer_email": "diego.martinez@example.com",
            "status": "delivered",
            "placed_at": now - timedelta(days=45),
            "currency": "USD",
            "total_cents": 19999,
        },
    }


def check_return_eligibility(order_id: str, customer_email: str) -> dict[str, Any]:
    """Verify whether an order can be returned under store policy.

    Args:
        order_id: UUID of the order (e.g. from confirmation email).
        customer_email: Email address on the order for ownership verification.

    Returns:
        Dictionary with eligible (bool), reason (str), order_id, and policy details.
    """
    email = customer_email.strip().lower()
    oid = order_id.strip()
    orders = _demo_orders()
    order = orders.get(oid)
    if not order:
        return {
            "eligible": False,
            "reason": "unknown_order",
            "order_id": oid,
            "detail": "No order found with this id.",
        }
    if order["customer_email"].lower() != email:
        return {
            "eligible": False,
            "reason": "email_mismatch",
            "order_id": oid,
            "detail": "Email does not match the order on file.",
        }
    if order["status"] == "cancelled":
        return {
            "eligible": False,
            "reason": "order_cancelled",
            "order_id": oid,
            "status": order["status"],
        }
    if order["status"] != "delivered":
        return {
            "eligible": False,
            "reason": "not_delivered",
            "order_id": oid,
            "status": order["status"],
            "detail": "Returns open only after delivery is confirmed.",
        }
    age = (_utcnow() - order["placed_at"]).days
    if age > RETURN_WINDOW_DAYS:
        return {
            "eligible": False,
            "reason": "outside_return_window",
            "order_id": oid,
            "status": order["status"],
            "days_since_delivery_estimate": age,
            "detail": f"Returns are accepted within {RETURN_WINDOW_DAYS} days of delivery.",
        }
    return {
        "eligible": True,
        "reason": "eligible",
        "order_id": oid,
        "status": order["status"],
        "days_since_delivery_estimate": age,
        "currency": order["currency"],
        "total_cents": order["total_cents"],
    }


def initiate_return(order_id: str, customer_email: str, reason: str) -> dict[str, Any]:
    """Create a return request for an eligible order.

    Call check_return_eligibility first. Records the return in memory.

    Args:
        order_id: UUID of the order to return.
        customer_email: Must match the order email.
        reason: Short description of why the customer is returning the item.

    Returns:
        On success: ok, return_id, order_id, message. On failure: ok False and eligibility payload.
    """
    check = check_return_eligibility(order_id, customer_email)
    if not check.get("eligible"):
        return {
            "ok": False,
            "error": "not_eligible",
            "eligibility": check,
        }
    rid = str(uuid.uuid4())
    _RETURNS.append(
        {
            "return_id": rid,
            "order_id": order_id.strip(),
            "customer_email": customer_email.strip().lower(),
            "reason": reason.strip(),
            "created_at": _utcnow().isoformat(),
        }
    )
    return {
        "ok": True,
        "return_id": rid,
        "order_id": order_id.strip(),
        "message": "Return registered. A shipping label will be emailed within 24 hours.",
    }
