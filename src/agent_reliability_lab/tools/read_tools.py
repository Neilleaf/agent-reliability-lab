from sqlalchemy import Engine

from agent_reliability_lab.retrieval.queries import (
    check_inventory,
    get_customer,
    get_order,
    get_product,
    track_shipment,
)
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
            "replacement_available": total_usable_quantity > 0,
        },
        message="Inventory retrieved successfully.",
    )
