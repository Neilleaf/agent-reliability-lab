from sqlalchemy import Engine

from agent_reliability_lab.retrieval.queries import (
    check_inventory,
    get_customer,
    get_damage_report,
    get_invoice,
    get_order,
    get_product,
    track_shipment,
)
from agent_reliability_lab.synthetic.policies import get_policy, replacement_available
from agent_reliability_lab.tools.models import (
    ToolResponse,
    ToolStatus,
)


def get_customer_tool(
    engine: Engine,
    customer_id: str,
) -> ToolResponse:
    """Return structured customer information."""
    customer = get_customer(
        engine,
        customer_id,
    )

    if customer is None:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="CUSTOMER_NOT_FOUND",
            message=f"Customer {customer_id} was not found.",
        )

    return ToolResponse(
        status=ToolStatus.SUCCESS,
        data={
            "customer": customer.model_dump(mode="json"),
        },
        message="Customer retrieved successfully.",
    )


def get_order_tool(
    engine: Engine,
    order_id: str,
) -> ToolResponse:
    """Return structured order information."""
    order = get_order(
        engine,
        order_id,
    )

    if order is None:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="ORDER_NOT_FOUND",
            message=f"Order {order_id} was not found.",
        )

    return ToolResponse(
        status=ToolStatus.SUCCESS,
        data={
            "order": order.model_dump(mode="json"),
        },
        message="Order retrieved successfully.",
    )


def track_shipment_tool(
    engine: Engine,
    order_id: str,
) -> ToolResponse:
    """Return shipment information for an order."""
    order = get_order(
        engine,
        order_id,
    )

    if order is None:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="ORDER_NOT_FOUND",
            message=f"Order {order_id} was not found.",
        )

    shipment = track_shipment(
        engine,
        order_id,
    )

    if shipment is None:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="SHIPMENT_NOT_FOUND",
            message=(
                f"Order {order_id} exists but does not currently have a shipment."
            ),
        )

    return ToolResponse(
        status=ToolStatus.SUCCESS,
        data={
            "shipment": shipment.model_dump(mode="json"),
        },
        message="Shipment retrieved successfully.",
    )


def check_inventory_tool(
    engine: Engine,
    product_id: str,
) -> ToolResponse:
    """Return inventory availability across warehouses."""
    product = get_product(
        engine,
        product_id,
    )

    if product is None:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="PRODUCT_NOT_FOUND",
            message=f"Product {product_id} was not found.",
        )

    inventory_records = check_inventory(
        engine,
        product_id,
    )

    locations = []

    for record in inventory_records:
        usable_quantity = record.quantity_available - record.quantity_reserved

        locations.append(
            {
                "warehouse_id": record.warehouse_id,
                "quantity_available": record.quantity_available,
                "quantity_reserved": record.quantity_reserved,
                "usable_quantity": usable_quantity,
            }
        )

    total_usable_quantity = sum(location["usable_quantity"] for location in locations)

    return ToolResponse(
        status=ToolStatus.SUCCESS,
        data={
            "product": product.model_dump(mode="json"),
            "locations": locations,
            "total_usable_quantity": total_usable_quantity,
            "replacement_available": replacement_available(
                product.replacement_eligible, locations
            ),
        },
        message="Inventory retrieved successfully.",
    )


def get_product_tool(engine: Engine, product_id: str) -> ToolResponse:
    product = get_product(engine, product_id)
    if product is None:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="PRODUCT_NOT_FOUND",
            message=f"Product {product_id} was not found.",
        )
    return ToolResponse(
        status=ToolStatus.SUCCESS,
        data={"product": product.model_dump(mode="json")},
        message="Product retrieved successfully.",
    )


def get_invoice_tool(engine: Engine, order_id: str) -> ToolResponse:
    invoice = get_invoice(engine, order_id)
    if invoice is None:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="INVOICE_NOT_FOUND",
            message=f"No invoice for order {order_id}.",
        )
    return ToolResponse(
        status=ToolStatus.SUCCESS,
        data={"invoice": invoice},
        message="Stored invoice retrieved without corrections.",
    )


def get_policy_tool(engine: Engine, policy_id: str) -> ToolResponse:
    policy = get_policy(policy_id)
    if policy is None:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="POLICY_NOT_FOUND",
            message=f"Policy {policy_id} was not found.",
        )
    return ToolResponse(
        status=ToolStatus.SUCCESS,
        data={"policy": policy},
        message="Authoritative policy retrieved.",
    )


def get_damage_report_tool(
    engine: Engine, order_id: str, product_id: str
) -> ToolResponse:
    report = get_damage_report(engine, order_id, product_id)
    if report is None:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="DAMAGE_REPORT_NOT_FOUND",
            message="No damage verification record for this order/product.",
        )
    return ToolResponse(
        status=ToolStatus.SUCCESS,
        data={"damage_report": report},
        message="Damage verification record retrieved.",
    )
