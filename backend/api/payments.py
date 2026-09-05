"""Shared Razorpay helpers. Business rule: an invoice is paid BY THE
CUSTOMER, through the portal -- see api/portal.py's razorpay-order/verify
routes, which are the only ones behind a customer JWT. The internal
workspace (api/invoices.py) can only view invoice status and record a
manually-reconciled offline payment (bank transfer) with a confirmation
step; it does not initiate or complete a Razorpay charge on the customer's
behalf.
"""
import hashlib
import hmac
import os

import razorpay

# Razorpay TEST-mode credentials. Overridable via env vars for real
# deployments; the defaults below are the test key pair provided for this
# hackathon build so checkout works out of the box in dev.
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_TYRBlT6eTZOuNQ")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "9enh7cNbIqwuX33A1v0zAnkz")

_razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_order(invoice_id: int, amount: float, quotation_id: int) -> dict:
    """Step 1 of Checkout: create the order server-side so the amount can't
    be tampered with client-side.
    """
    amount_paise = int(round(float(amount) * 100))
    order = _razorpay_client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"invoice-{invoice_id}",
        "notes": {"invoice_id": str(invoice_id), "quotation_id": str(quotation_id)},
    })
    return {"order_id": order["id"], "amount": amount_paise, "currency": "INR", "key_id": RAZORPAY_KEY_ID}


def verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Step 2: HMAC-SHA256 of order_id|payment_id, keyed with the account
    secret -- Razorpay's own recommended flow, since the client-side
    "success" callback alone is not proof a payment actually happened.
    """
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
