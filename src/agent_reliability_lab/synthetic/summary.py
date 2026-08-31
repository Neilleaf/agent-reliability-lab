from collections import Counter
from decimal import Decimal

from agent_reliability_lab.synthetic.generator import generate_snapshot
from agent_reliability_lab.synthetic.models import NorthstarSnapshot


def _print_distribution(title: str, counts: Counter[str]) -> None:
    print(f"\n{title}")

    total = sum(counts.values())

    for label, count in counts.most_common():
        percentage = count / total * 100
        print(f"  {label:<22} {count:>4}  ({percentage:>5.1f}%)")


def print_snapshot_summary(world: NorthstarSnapshot) -> None:
    print("=" * 60)
    print("NORTHSTAR SUPPLY CO. — SYNTHETIC WORLD SUMMARY")
    print("=" * 60)

    print("\nRECORD COUNTS")
    print(f"  Customers:       {len(world.customers)}")
    print(f"  Products:        {len(world.products)}")
    print(f"  Warehouses:      {len(world.warehouses)}")
    print(f"  Inventory rows:  {len(world.inventory)}")
    print(f"  Orders:          {len(world.orders)}")
    print(f"  Shipments:       {len(world.shipments)}")
    print(f"  Invoices:        {len(world.invoices)}")
    print(f"  Support tickets: {len(world.support_tickets)}")

    customer_tiers = Counter(
        customer.customer_tier.value for customer in world.customers
    )

    _print_distribution(
        "CUSTOMER TIER DISTRIBUTION",
        customer_tiers,
    )

    account_statuses = Counter(
        customer.account_status.value for customer in world.customers
    )

    _print_distribution(
        "CUSTOMER ACCOUNT STATUS",
        account_statuses,
    )

    product_categories = Counter(product.category.value for product in world.products)

    _print_distribution(
        "PRODUCT CATEGORIES",
        product_categories,
    )

    active_products = sum(product.active for product in world.products)

    print("\nPRODUCT STATUS")
    print(f"  Active:          {active_products}")
    print(f"  Discontinued:    {len(world.products) - active_products}")

    order_statuses = Counter(order.order_status.value for order in world.orders)

    _print_distribution(
        "ORDER STATUS DISTRIBUTION",
        order_statuses,
    )

    order_values = [order.total_amount for order in world.orders]

    average_order_value = sum(order_values, start=Decimal("0.00")) / len(order_values)

    print("\nORDER VALUE")
    print(f"  Average:         ${average_order_value:.2f}")
    print(f"  Minimum:         ${min(order_values):.2f}")
    print(f"  Maximum:         ${max(order_values):.2f}")

    shipment_statuses = Counter(
        shipment.shipment_status.value for shipment in world.shipments
    )

    _print_distribution(
        "SHIPMENT STATUS DISTRIBUTION",
        shipment_statuses,
    )

    payment_statuses = Counter(
        invoice.payment_status.value for invoice in world.invoices
    )

    _print_distribution(
        "INVOICE PAYMENT STATUS",
        payment_statuses,
    )

    usable_inventory = [
        record.quantity_available - record.quantity_reserved
        for record in world.inventory
    ]

    zero_inventory_records = sum(quantity == 0 for quantity in usable_inventory)

    average_usable_inventory = sum(usable_inventory) / len(usable_inventory)

    print("\nINVENTORY")
    print(f"  Average usable units: {average_usable_inventory:.1f}")
    print(f"  Zero usable inventory: {zero_inventory_records}")
    print(f"  Positive inventory: {len(usable_inventory) - zero_inventory_records}")

    customers_with_orders = {order.customer_id for order in world.orders}

    print("\nCUSTOMER ACTIVITY")
    print(f"  Customers with orders: {len(customers_with_orders)}")
    print(
        f"  Customers without orders: "
        f"{len(world.customers) - len(customers_with_orders)}"
    )

    print("\n" + "=" * 60)


def main() -> None:
    world = generate_snapshot(seed=42)
    print_snapshot_summary(world)


if __name__ == "__main__":
    main()
