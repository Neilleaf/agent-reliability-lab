from sqlalchemy import Engine, select

from agent_reliability_lab.storage.schema import (
    customers,
    damage_reports,
    inventory,
    invoices,
    order_items,
    orders,
    products,
    shipments,
)
from agent_reliability_lab.synthetic.models import (
    Address,
    Customer,
    InventoryRecord,
    Order,
    OrderItem,
    Product,
    Shipment,
)


def get_customer(
    engine: Engine,
    customer_id: str,
) -> Customer | None:
    """Retrieve a customer by ID."""
    statement = select(customers).where(customers.c.customer_id == customer_id)

    with engine.connect() as connection:
        row = connection.execute(statement).mappings().one_or_none()

    if row is None:
        return None

    return Customer(
        customer_id=row["customer_id"],
        company_name=row["company_name"],
        contact_name=row["contact_name"],
        email=row["email"],
        account_status=row["account_status"],
        customer_tier=row["customer_tier"],
        billing_address=Address(
            line1=row["billing_line1"],
            city=row["billing_city"],
            state=row["billing_state"],
            postal_code=row["billing_postal_code"],
            country=row["billing_country"],
        ),
        shipping_address=Address(
            line1=row["shipping_line1"],
            city=row["shipping_city"],
            state=row["shipping_state"],
            postal_code=row["shipping_postal_code"],
            country=row["shipping_country"],
        ),
        date_created=row["date_created"],
    )


def get_order(
    engine: Engine,
    order_id: str,
) -> Order | None:
    """Retrieve an order and its order items by ID."""
    order_statement = select(orders).where(orders.c.order_id == order_id)

    item_statement = (
        select(order_items)
        .where(order_items.c.order_id == order_id)
        .order_by(order_items.c.order_item_id)
    )

    with engine.connect() as connection:
        order_row = connection.execute(order_statement).mappings().one_or_none()

        if order_row is None:
            return None

        item_rows = connection.execute(item_statement).mappings().all()

    items = [
        OrderItem(
            product_id=row["product_id"],
            quantity=row["quantity"],
            unit_price=row["unit_price"],
            line_total=row["line_total"],
        )
        for row in item_rows
    ]

    return Order(
        order_id=order_row["order_id"],
        customer_id=order_row["customer_id"],
        order_date=order_row["order_date"],
        order_status=order_row["order_status"],
        shipping_address=Address(
            line1=order_row["shipping_line1"],
            city=order_row["shipping_city"],
            state=order_row["shipping_state"],
            postal_code=order_row["shipping_postal_code"],
            country=order_row["shipping_country"],
        ),
        billing_address=Address(
            line1=order_row["billing_line1"],
            city=order_row["billing_city"],
            state=order_row["billing_state"],
            postal_code=order_row["billing_postal_code"],
            country=order_row["billing_country"],
        ),
        order_items=items,
        subtotal=order_row["subtotal"],
        shipping_charge=order_row["shipping_charge"],
        tax=order_row["tax"],
        total_amount=order_row["total_amount"],
    )


def track_shipment(
    engine: Engine,
    order_id: str,
) -> Shipment | None:
    """Retrieve shipment information for an order."""
    statement = select(shipments).where(shipments.c.order_id == order_id)

    with engine.connect() as connection:
        row = connection.execute(statement).mappings().one_or_none()

    if row is None:
        return None

    return Shipment(
        shipment_id=row["shipment_id"],
        order_id=row["order_id"],
        carrier=row["carrier"],
        tracking_reference=row["tracking_reference"],
        shipped_date=row["shipped_date"],
        expected_delivery_date=row["expected_delivery_date"],
        actual_delivery_date=row["actual_delivery_date"],
        shipment_status=row["shipment_status"],
    )


def check_inventory(
    engine: Engine,
    product_id: str,
) -> list[InventoryRecord]:
    """Retrieve inventory for a product across all warehouses."""
    statement = (
        select(inventory)
        .where(inventory.c.product_id == product_id)
        .order_by(inventory.c.warehouse_id)
    )

    with engine.connect() as connection:
        rows = connection.execute(statement).mappings().all()

    return [
        InventoryRecord(
            warehouse_id=row["warehouse_id"],
            product_id=row["product_id"],
            quantity_available=row["quantity_available"],
            quantity_reserved=row["quantity_reserved"],
        )
        for row in rows
    ]


def get_product(
    engine: Engine,
    product_id: str,
) -> Product | None:
    """Retrieve a product by ID."""
    statement = select(products).where(products.c.product_id == product_id)

    with engine.connect() as connection:
        row = connection.execute(statement).mappings().one_or_none()

    if row is None:
        return None

    return Product(
        product_id=row["product_id"],
        product_name=row["product_name"],
        category=row["category"],
        unit_price=row["unit_price"],
        active=row["active"],
        replacement_eligible=row["replacement_eligible"],
    )


def get_invoice(engine: Engine, order_id: str) -> dict[str, object] | None:
    """Read invoice facts without repairing discrepancies or applying Invoice validation.

    The synthetic Invoice model validates generated records. Retrieval must also
    preserve deliberately inconsistent stored invoices for investigation.
    """
    with engine.connect() as connection:
        row = (
            connection.execute(select(invoices).where(invoices.c.order_id == order_id))
            .mappings()
            .one_or_none()
        )
    if row is None:
        return None
    result = dict(row)
    result["issue_date"] = result["issue_date"].isoformat()
    for key in ("subtotal", "shipping_charge", "tax", "total"):
        result[key] = str(result[key])
    return result


def get_damage_report(
    engine: Engine, order_id: str, product_id: str
) -> dict[str, object] | None:
    """Retrieve verification facts for the exact order/product pair."""
    with engine.connect() as connection:
        row = (
            connection.execute(
                select(damage_reports).where(
                    damage_reports.c.order_id == order_id,
                    damage_reports.c.product_id == product_id,
                )
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        return None
    return {**dict(row), "reported_date": row["reported_date"].isoformat()}
