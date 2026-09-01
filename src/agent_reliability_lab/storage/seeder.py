from sqlalchemy import Engine, insert

from agent_reliability_lab.storage.database import (
    create_database_engine,
    reset_database,
)
from agent_reliability_lab.storage.schema import (
    customers,
    inventory,
    invoices,
    order_items,
    orders,
    products,
    shipments,
    support_tickets,
    warehouses,
)
from agent_reliability_lab.synthetic.generator import generate_snapshot
from agent_reliability_lab.synthetic.models import NorthstarSnapshot


def _customer_rows(world: NorthstarSnapshot) -> list[dict[str, object]]:
    return [
        {
            "customer_id": customer.customer_id,
            "company_name": customer.company_name,
            "contact_name": customer.contact_name,
            "email": customer.email,
            "account_status": customer.account_status.value,
            "customer_tier": customer.customer_tier.value,
            "billing_line1": customer.billing_address.line1,
            "billing_city": customer.billing_address.city,
            "billing_state": customer.billing_address.state,
            "billing_postal_code": customer.billing_address.postal_code,
            "billing_country": customer.billing_address.country,
            "shipping_line1": customer.shipping_address.line1,
            "shipping_city": customer.shipping_address.city,
            "shipping_state": customer.shipping_address.state,
            "shipping_postal_code": customer.shipping_address.postal_code,
            "shipping_country": customer.shipping_address.country,
            "date_created": customer.date_created,
        }
        for customer in world.customers
    ]


def _product_rows(world: NorthstarSnapshot) -> list[dict[str, object]]:
    return [
        {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "category": product.category.value,
            "unit_price": product.unit_price,
            "active": product.active,
            "replacement_eligible": product.replacement_eligible,
        }
        for product in world.products
    ]


def _warehouse_rows(world: NorthstarSnapshot) -> list[dict[str, object]]:
    return [
        {
            "warehouse_id": warehouse.warehouse_id,
            "warehouse_name": warehouse.warehouse_name,
        }
        for warehouse in world.warehouses
    ]


def _inventory_rows(world: NorthstarSnapshot) -> list[dict[str, object]]:
    return [
        {
            "warehouse_id": record.warehouse_id,
            "product_id": record.product_id,
            "quantity_available": record.quantity_available,
            "quantity_reserved": record.quantity_reserved,
        }
        for record in world.inventory
    ]


def _order_rows(world: NorthstarSnapshot) -> list[dict[str, object]]:
    return [
        {
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "order_date": order.order_date,
            "order_status": order.order_status.value,
            "shipping_line1": order.shipping_address.line1,
            "shipping_city": order.shipping_address.city,
            "shipping_state": order.shipping_address.state,
            "shipping_postal_code": order.shipping_address.postal_code,
            "shipping_country": order.shipping_address.country,
            "billing_line1": order.billing_address.line1,
            "billing_city": order.billing_address.city,
            "billing_state": order.billing_address.state,
            "billing_postal_code": order.billing_address.postal_code,
            "billing_country": order.billing_address.country,
            "subtotal": order.subtotal,
            "shipping_charge": order.shipping_charge,
            "tax": order.tax,
            "total_amount": order.total_amount,
        }
        for order in world.orders
    ]


def _order_item_rows(
    world: NorthstarSnapshot,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for order in world.orders:
        for item in order.order_items:
            rows.append(
                {
                    "order_id": order.order_id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total,
                }
            )

    return rows


def _shipment_rows(world: NorthstarSnapshot) -> list[dict[str, object]]:
    return [
        {
            "shipment_id": shipment.shipment_id,
            "order_id": shipment.order_id,
            "carrier": shipment.carrier,
            "tracking_reference": shipment.tracking_reference,
            "shipped_date": shipment.shipped_date,
            "expected_delivery_date": shipment.expected_delivery_date,
            "actual_delivery_date": shipment.actual_delivery_date,
            "shipment_status": shipment.shipment_status.value,
        }
        for shipment in world.shipments
    ]


def _invoice_rows(world: NorthstarSnapshot) -> list[dict[str, object]]:
    return [
        {
            "invoice_id": invoice.invoice_id,
            "order_id": invoice.order_id,
            "issue_date": invoice.issue_date,
            "subtotal": invoice.subtotal,
            "shipping_charge": invoice.shipping_charge,
            "tax": invoice.tax,
            "total": invoice.total,
            "payment_status": invoice.payment_status.value,
        }
        for invoice in world.invoices
    ]


def _support_ticket_rows(
    world: NorthstarSnapshot,
) -> list[dict[str, object]]:
    return [
        {
            "ticket_id": ticket.ticket_id,
            "customer_id": ticket.customer_id,
            "order_id": ticket.order_id,
            "issue_type": ticket.issue_type.value,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "description": ticket.description,
            "created_date": ticket.created_date,
        }
        for ticket in world.support_tickets
    ]


def seed_database(
    engine: Engine,
    world: NorthstarSnapshot,
) -> None:
    """Rebuild and populate the Northstar database."""
    reset_database(engine)

    with engine.begin() as connection:
        connection.execute(
            insert(customers),
            _customer_rows(world),
        )

        connection.execute(
            insert(products),
            _product_rows(world),
        )

        connection.execute(
            insert(warehouses),
            _warehouse_rows(world),
        )

        connection.execute(
            insert(inventory),
            _inventory_rows(world),
        )

        connection.execute(
            insert(orders),
            _order_rows(world),
        )

        connection.execute(
            insert(order_items),
            _order_item_rows(world),
        )

        connection.execute(
            insert(shipments),
            _shipment_rows(world),
        )

        connection.execute(
            insert(invoices),
            _invoice_rows(world),
        )

        ticket_rows = _support_ticket_rows(world)

        if ticket_rows:
            connection.execute(
                insert(support_tickets),
                ticket_rows,
            )


def main() -> None:
    world = generate_snapshot(seed=42)
    engine = create_database_engine()

    seed_database(
        engine,
        world,
    )

    print("Northstar database seeded successfully.")
    print(f"Customers: {len(world.customers)}")
    print(f"Products: {len(world.products)}")
    print(f"Orders: {len(world.orders)}")
    print(f"Shipments: {len(world.shipments)}")
    print(f"Invoices: {len(world.invoices)}")


if __name__ == "__main__":
    main()
