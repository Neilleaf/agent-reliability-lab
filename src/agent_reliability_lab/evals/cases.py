"""Canonical V1 cases and explicit, isolated database fixture changes."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, insert, update

from agent_reliability_lab.storage import schema
from agent_reliability_lab.storage.seeder import seed_database
from agent_reliability_lab.synthetic.generator import REFERENCE_DATE, generate_snapshot
from agent_reliability_lab.synthetic.models import NorthstarSnapshot
from agent_reliability_lab.synthetic.policies import (
    damage_decision,
    get_policy,
    invoice_discrepancies,
    refund_decision,
    replacement_available,
)

FAMILIES = {
    "S01": "Shipment",
    "S02": "Refund",
    "S03": "Damaged Product",
    "S04": "Incorrect Invoice",
    "S05": "Replacement",
}


def _record(model: BaseModel) -> dict[str, object]:
    """Match SQLite Numeric(10, 2) serialization without changing generators."""
    money_fields = {
        "unit_price",
        "line_total",
        "subtotal",
        "shipping_charge",
        "tax",
        "total",
        "total_amount",
    }

    def normalize(value):
        if isinstance(value, dict):
            return {
                key: format(Decimal(str(item)), ".2f")
                if key in money_fields
                else normalize(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value

    return normalize(model.model_dump(mode="json"))


class EvidenceRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: str
    arguments: dict[str, str]
    expected_data: dict[str, object]


class FixtureChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table: Literal[
        "orders", "shipments", "products", "inventory", "invoices", "damage_reports"
    ]
    key: dict[str, str]
    values: dict[str, object]
    insert: bool = False


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    family: Literal["S01", "S02", "S03", "S04", "S05"]
    task: str
    entity_ids: dict[str, str]
    ground_truth: dict[str, object]
    required_evidence: list[EvidenceRequirement]
    fixture_changes: list[FixtureChange] = Field(default_factory=list)


def prepare_case_database(
    engine: Engine, world: NorthstarSnapshot, case: BenchmarkCase
) -> None:
    """Seed a dedicated case database, then apply only declared fixture changes."""
    seed_database(engine, world)
    with engine.begin() as connection:
        for change in case.fixture_changes:
            table = getattr(schema, change.table)
            if change.insert:
                connection.execute(insert(table).values(**change.key, **change.values))
            else:
                statement = (
                    update(table)
                    .where(
                        *(table.c[key] == value for key, value in change.key.items())
                    )
                    .values(**change.values)
                )
                result = connection.execute(statement)
                if result.rowcount != 1:
                    raise ValueError(f"Fixture must update exactly one row: {change}")


def build_benchmark_cases(
    world: NorthstarSnapshot | None = None,
) -> list[BenchmarkCase]:
    """Construct four deliberate cases per family without mutating the base world."""
    world = world if world is not None else generate_snapshot(seed=42)
    cases = []
    for status in ("lost", "delayed", "in_transit", "delivered"):
        shipment = next(s for s in world.shipments if s.shipment_status.value == status)
        order_id = shipment.order_id
        order = next(o for o in world.orders if o.order_id == order_id)
        cases.append(
            BenchmarkCase(
                case_id=f"S01_{status}",
                family="S01",
                task=(
                    f"A customer says order {order_id} is lost. "
                    "Investigate the order using Northstar's records "
                    "and tell me what is actually happening. "
                    "Do not assume the customer's claim is correct."
                ),
                entity_ids={"order_id": order_id},
                ground_truth={"expected_decision": status, "shipment_status": status},
                required_evidence=[
                    EvidenceRequirement(
                        tool="get_order",
                        arguments={"order_id": order_id},
                        expected_data={"order": _record(order)},
                    ),
                    EvidenceRequirement(
                        tool="track_shipment",
                        arguments={"order_id": order_id},
                        expected_data={"shipment": shipment.model_dump(mode="json")},
                    ),
                ],
            )
        )

    delivered_shipment = next(
        s for s in world.shipments if s.shipment_status.value == "delivered"
    )
    delivered_order = next(
        o for o in world.orders if o.order_id == delivered_shipment.order_id
    )
    variants = {
        "S02": ["valid_refund", "outside_window", "not_delivered", "already_refunded"],
        "S03": ["replace", "no_stock", "ineligible_product", "unverified_damage"],
        "S04": [
            "correct_invoice",
            "inflated_subtotal",
            "shipping_discrepancy",
            "tax_total_discrepancy",
        ],
        "S05": ["available", "no_stock", "ineligible_product", "one_warehouse_empty"],
    }
    for family, names in variants.items():
        for name in names:
            changes = []
            order_model = delivered_order
            if name == "not_delivered":
                shipment_model = next(
                    s
                    for s in world.shipments
                    if s.shipment_status.value == "in_transit"
                )
                order_model = next(
                    o for o in world.orders if o.order_id == shipment_model.order_id
                )
            elif name == "already_refunded":
                order_model = next(
                    o for o in world.orders if o.order_status.value == "cancelled"
                )
                shipment_model = None
            else:
                shipment_model = delivered_shipment
            order_id = order_model.order_id
            order = _record(order_model)
            product_id = order_model.order_items[0].product_id
            product = _record(
                next(p for p in world.products if p.product_id == product_id)
            )
            shipment = (
                shipment_model.model_dump(mode="json") if shipment_model else None
            )
            invoice_model = next(
                (i for i in world.invoices if i.order_id == order_id), None
            )
            invoice = (
                _record(invoice_model)
                if invoice_model
                else {
                    "invoice_id": "INV-99999",
                    "order_id": order_id,
                    "issue_date": order["order_date"],
                    **{
                        key: order[key]
                        for key in ("subtotal", "shipping_charge", "tax")
                    },
                    "total": order["total_amount"],
                    "payment_status": "refunded",
                }
            )

            def change(table, key, values, *, insert_row=False, changes=changes):
                changes.append(
                    FixtureChange(
                        table=table, key=key, values=values, insert=insert_row
                    )
                )

            if shipment and name != "not_delivered":
                days = 31 if name == "outside_window" else 10
                delivery_date = REFERENCE_DATE - timedelta(days=days)
                # Keep all adjusted fixture events chronologically coherent.
                order["order_date"] = (REFERENCE_DATE - timedelta(days=45)).isoformat()
                change(
                    "orders",
                    {"order_id": order_id},
                    {"order_date": REFERENCE_DATE - timedelta(days=45)},
                )
                shipment.update(
                    shipped_date=(REFERENCE_DATE - timedelta(days=40)).isoformat(),
                    actual_delivery_date=delivery_date.isoformat(),
                    expected_delivery_date=delivery_date.isoformat(),
                )
                change(
                    "shipments",
                    {"shipment_id": shipment["shipment_id"]},
                    {
                        "shipped_date": REFERENCE_DATE - timedelta(days=40),
                        "actual_delivery_date": delivery_date,
                        "expected_delivery_date": delivery_date,
                    },
                )
                invoice["issue_date"] = order["order_date"]

            invoice["payment_status"] = (
                "refunded" if name == "already_refunded" else "paid"
            )
            for key in ("subtotal", "shipping_charge", "tax"):
                invoice[key] = order[key]
            invoice["total"] = order["total_amount"]
            if family == "S04":
                field = {
                    "inflated_subtotal": "subtotal",
                    "shipping_discrepancy": "shipping_charge",
                    "tax_total_discrepancy": "tax",
                }.get(name)
                if field:
                    invoice[field] = str(Decimal(invoice[field]) + Decimal("10.00"))
                    if name != "tax_total_discrepancy":
                        invoice["total"] = str(
                            Decimal(invoice["total"]) + Decimal("10.00")
                        )
            invoice_values = {
                **invoice,
                "issue_date": date.fromisoformat(invoice["issue_date"]),
            }
            for key in ("subtotal", "shipping_charge", "tax", "total"):
                invoice_values[key] = Decimal(invoice_values[key])
            invoice_key = {"invoice_id": invoice_values.pop("invoice_id")}
            change(
                "invoices",
                invoice_key,
                invoice_values,
                insert_row=invoice_model is None,
            )

            # Replacement and damage cases explicitly control eligibility and all locations.
            locations = []
            if family in ("S03", "S05"):
                product["replacement_eligible"] = name != "ineligible_product"
                change(
                    "products",
                    {"product_id": product_id},
                    {"replacement_eligible": product["replacement_eligible"]},
                )
                for index, warehouse in enumerate(world.warehouses):
                    available = (
                        3
                        if name != "no_stock" and (name == "available" or index == 1)
                        else 2
                    )
                    reserved = 2
                    values = {
                        "quantity_available": available,
                        "quantity_reserved": reserved,
                    }
                    change(
                        "inventory",
                        {
                            "warehouse_id": warehouse.warehouse_id,
                            "product_id": product_id,
                        },
                        values,
                    )
                    locations.append(
                        {
                            "warehouse_id": warehouse.warehouse_id,
                            **values,
                            "usable_quantity": available - reserved,
                        }
                    )
                locations.sort(key=lambda item: item["warehouse_id"])

            evidence = []

            def require(tool, arguments, expected_data, evidence=evidence):
                evidence.append(
                    EvidenceRequirement(
                        tool=tool, arguments=arguments, expected_data=expected_data
                    )
                )

            def policy(policy_id):
                require(
                    "get_policy",
                    {"policy_id": policy_id},
                    {"policy": get_policy(policy_id)},
                )

            truth = {}
            if family in ("S02", "S03", "S04"):
                require("get_order", {"order_id": order_id}, {"order": order})
                require("get_invoice", {"order_id": order_id}, {"invoice": invoice})
            if family in ("S02", "S03"):
                # A shipped (not delivered) order already fails the ordinary-return
                # condition. Tracking cannot change that policy decision.
                if shipment and name != "not_delivered":
                    require(
                        "track_shipment", {"order_id": order_id}, {"shipment": shipment}
                    )
                policy("refund")
                refund_outcome = refund_decision(
                    order["order_status"],
                    shipment["shipment_status"] if shipment else "none",
                    date.fromisoformat(shipment["actual_delivery_date"])
                    if shipment and shipment["actual_delivery_date"]
                    else None,
                    invoice["payment_status"],
                )
                truth["expected_decision"] = refund_outcome
            if family in ("S03", "S05"):
                require("get_product", {"product_id": product_id}, {"product": product})
                can_replace = replacement_available(
                    product["replacement_eligible"], locations
                )
                require(
                    "check_inventory",
                    {"product_id": product_id},
                    {
                        "product": product,
                        "locations": locations,
                        "total_usable_quantity": sum(
                            item["usable_quantity"] for item in locations
                        ),
                        "replacement_available": can_replace,
                    },
                )
                truth.update(
                    replacement_available=can_replace,
                    replacement_eligible=product["replacement_eligible"],
                )

                if family == "S05":
                    policy("replacement")
                    truth["expected_decision"] = (
                        "available" if can_replace else "unavailable"
                    )
                else:
                    policy("damage")
                    verified = name != "unverified_damage"
                    report = {"verified": verified, "reported_date": REFERENCE_DATE}
                    change(
                        "damage_reports",
                        {"order_id": order_id, "product_id": product_id},
                        report,
                        insert_row=True,
                    )
                    require(
                        "get_damage_report",
                        {"order_id": order_id, "product_id": product_id},
                        {
                            "damage_report": {
                                "order_id": order_id,
                                "product_id": product_id,
                                "verified": verified,
                                "reported_date": REFERENCE_DATE.isoformat(),
                            }
                        },
                    )
                    truth.update(
                        damage_verified=verified,
                        expected_decision=damage_decision(
                            verified=verified,
                            product_in_order=True,
                            refund_outcome=refund_outcome,
                            can_replace=can_replace,
                        ),
                    )
            if family == "S04":
                policy("invoice")
                discrepancies = invoice_discrepancies(order, invoice)
                truth.update(
                    discrepancies=discrepancies,
                    expected_decision="correct_invoice"
                    if not discrepancies
                    else "correct_discrepancy",
                )

            # QA: do not require downstream lookups after a decisive policy gate.
            # Keep all fixtures and ground-truth labels intact, including audit facts.
            if family == "S03" and not truth["damage_verified"]:
                evidence = [
                    item
                    for item in evidence
                    if item.tool in ("get_order", "get_damage_report")
                    or (
                        item.tool == "get_policy"
                        and item.arguments["policy_id"] == "damage"
                    )
                ]
            elif family in ("S03", "S05") and not truth["replacement_eligible"]:
                evidence = [item for item in evidence if item.tool != "check_inventory"]

            claim = {
                "S02": f"A customer says order {order_id} qualifies for a refund. Investigate eligibility under Northstar policy.",
                "S03": f"A customer says product {product_id} in order {order_id} arrived damaged and wants a replacement. Investigate the recorded evidence and determine the appropriate resolution under Northstar policy.",
                "S04": f"A customer says the invoice for order {order_id} overcharges them. Compare the stored invoice against the order and Northstar policy.",
                "S05": f"A customer says product {product_id} is out of stock and cannot be replaced. Investigate replacement eligibility and usable inventory across all warehouses under Northstar policy.",
            }[family]
            cases.append(
                BenchmarkCase(
                    case_id=f"{family}_{name}",
                    family=family,
                    task=claim + " Do not assume the customer's claim is correct.",
                    entity_ids={"order_id": order_id, "product_id": product_id},
                    ground_truth=truth,
                    required_evidence=evidence,
                    fixture_changes=changes,
                )
            )
    return cases
