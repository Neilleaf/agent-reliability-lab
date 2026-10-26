"""Small authoritative Northstar policies, evaluated at the snapshot date."""

from copy import deepcopy
from datetime import date
from decimal import Decimal

from agent_reliability_lab.synthetic.generator import REFERENCE_DATE

REFUND_WINDOW_DAYS = 30
POLICIES = {
    "refund": {
        "policy_id": "refund",
        "version": "v1",
        "as_of": REFERENCE_DATE.isoformat(),
        "window_days": REFUND_WINDOW_DAYS,
        "window_inclusive": True,
        "required_order_status": "delivered",
        "required_shipment_status": "delivered",
        "required_payment_status": "paid",
        "cancelled_or_refunded": "do_not_refund_again",
        "not_delivered": "not_an_ordinary_return_refund",
        "future_delivery_date": "ineligible",
    },
    "damage": {
        "policy_id": "damage",
        "version": "v1",
        "as_of": REFERENCE_DATE.isoformat(),
        "requires_verified_damage_report": True,
        "requires_product_in_order": True,
        "refund_policy_id": "refund",
        "eligibility": "paid delivered order within refund window",
        "preferred_resolution": "replace if product replacement_eligible and usable stock > 0",
        "fallback": "refund if refund policy permits; otherwise deny",
        "unverified_damage": "request_evidence",
    },
    "invoice": {
        "policy_id": "invoice",
        "version": "v1",
        "as_of": REFERENCE_DATE.isoformat(),
        "expected_total": "order.subtotal + order.shipping_charge + order.tax",
        "compare_fields": ["subtotal", "shipping_charge", "tax", "total"],
        "internal_invoice_total": "invoice.subtotal + invoice.shipping_charge + invoice.tax",
        "mismatch_resolution": "investigate_and_correct_invoice",
    },
    "replacement": {
        "policy_id": "replacement",
        "version": "v1",
        "as_of": REFERENCE_DATE.isoformat(),
        "requires_replacement_eligible": True,
        "usable_quantity": "quantity_available - quantity_reserved",
        "availability": "any warehouse has usable_quantity > 0",
        "scope": "all warehouses; one empty location does not mean no stock anywhere",
        "decision_scope": "availability for one replacement unit, not authorization or reservation",
    },
}


def get_policy(policy_id: str) -> dict[str, object] | None:
    """Return an independent machine-readable policy, or None."""
    policy = POLICIES.get(policy_id)
    return deepcopy(policy) if policy is not None else None


def refund_decision(
    order_status: str,
    shipment_status: str,
    actual_delivery_date: date | None,
    payment_status: str,
    *,
    as_of: date = REFERENCE_DATE,
) -> str:
    if payment_status == "refunded":
        return "already_refunded"
    if order_status == "cancelled":
        return "cancelled_no_return_refund"
    if order_status != "delivered" or shipment_status != "delivered":
        return "not_delivered"
    if actual_delivery_date is None:
        return "delivery_evidence_required"
    if not 0 <= (as_of - actual_delivery_date).days <= REFUND_WINDOW_DAYS:
        return "outside_refund_window"
    if payment_status != "paid":
        return "no_paid_amount_to_refund"
    return "refund_eligible"


def replacement_available(eligible: bool, locations: list[dict[str, object]]) -> bool:
    return eligible and any(
        location["quantity_available"] - location["quantity_reserved"] > 0
        for location in locations
    )


def damage_decision(
    *, verified: bool, product_in_order: bool, refund_outcome: str, can_replace: bool
) -> str:
    if not verified or not product_in_order:
        return "request_evidence"
    if refund_outcome != "refund_eligible":
        return "deny"
    return "replace" if can_replace else "refund"


def invoice_discrepancies(
    order: dict[str, object], invoice: dict[str, object]
) -> list[str]:
    """Compare exact money values, including internally inconsistent invoices."""
    expected = {
        "subtotal": Decimal(str(order["subtotal"])),
        "shipping_charge": Decimal(str(order["shipping_charge"])),
        "tax": Decimal(str(order["tax"])),
    }
    expected["total"] = sum(expected.values(), Decimal("0.00"))
    mismatches = [
        key for key, value in expected.items() if Decimal(str(invoice[key])) != value
    ]
    if Decimal(str(invoice["total"])) != sum(
        (Decimal(str(invoice[key])) for key in ("subtotal", "shipping_charge", "tax")),
        Decimal("0.00"),
    ):
        mismatches.append("internal_total")
    return mismatches
