from datetime import date, timedelta
from decimal import Decimal
from random import Random

from faker import Faker

from agent_reliability_lab.synthetic.models import (
    AccountStatus,
    Address,
    Customer,
    CustomerTier,
    InventoryRecord,
    Invoice,
    NorthstarBaseWorld,
    NorthstarSnapshot,
    Order,
    OrderItem,
    OrderStatus,
    PaymentStatus,
    Product,
    ProductCategory,
    Shipment,
    ShipmentStatus,
    Warehouse,
)

REFERENCE_DATE = date(2026, 8, 31)

MONEY_PLACES = Decimal("0.01")
TAX_RATE = Decimal("0.0825")


def _money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places."""
    return value.quantize(MONEY_PLACES)


PRODUCT_CATALOG = {
    ProductCategory.SAFETY_EQUIPMENT: [
        "Industrial Safety Helmet",
        "Cut-Resistant Gloves",
        "Protective Safety Goggles",
        "High-Visibility Vest",
        "Hearing Protection Earmuffs",
        "Respirator Mask",
        "Safety Knee Pads",
        "Face Shield",
        "Chemical Resistant Gloves",
        "Protective Work Apron",
    ],
    ProductCategory.TOOLS: [
        "Cordless Drill",
        "Professional Tool Kit",
        "Torque Wrench",
        "Digital Measuring Tool",
        "Adjustable Spanner Set",
        "Precision Screwdriver Set",
        "Heavy-Duty Pliers",
        "Rubber Mallet",
        "Socket Wrench Set",
        "Utility Knife Set",
    ],
    ProductCategory.OFFICE_EQUIPMENT: [
        "Ergonomic Office Chair",
        "Adjustable Monitor Stand",
        "Wireless Keyboard",
        "LED Desk Lamp",
        "Laptop Stand",
        "Document Shredder",
        "Foot Rest",
        "Desk Organiser",
        "Whiteboard",
        "Cable Management Tray",
    ],
    ProductCategory.STORAGE_EQUIPMENT: [
        "Industrial Shelving Unit",
        "Stackable Storage Bin",
        "Mobile Tool Cabinet",
        "Lockable Document Cabinet",
        "Parts Storage Organiser",
        "Heavy-Duty Storage Rack",
        "Rolling Storage Cart",
        "Wall-Mounted Tool Rack",
        "Archive Storage Box",
        "Workshop Drawer Unit",
    ],
    ProductCategory.ELECTRICAL_ACCESSORIES: [
        "Heavy-Duty Extension Cable",
        "Surge Protector",
        "Portable Work Light",
        "Cable Reel",
        "USB Charging Hub",
        "Industrial Power Strip",
        "Rechargeable Inspection Light",
        "Outdoor Extension Lead",
        "Power Adapter",
        "Cable Connector Set",
    ],
}


def _generate_address(fake: Faker) -> Address:
    return Address(
        line1=fake.street_address(),
        city=fake.city(),
        state=fake.state(),
        postal_code=fake.postcode(),
        country="United States",
    )


def generate_customers(
    *,
    count: int = 100,
    seed: int = 42,
) -> list[Customer]:
    fake = Faker("en_US")
    fake.seed_instance(seed)

    rng = Random(seed)

    customers: list[Customer] = []

    for index in range(1, count + 1):
        billing_address = _generate_address(fake)

        if rng.random() < 0.7:
            shipping_address = billing_address
        else:
            shipping_address = _generate_address(fake)

        tier = rng.choices(
            population=[
                CustomerTier.STANDARD,
                CustomerTier.BUSINESS,
                CustomerTier.ENTERPRISE,
            ],
            weights=[60, 30, 10],
            k=1,
        )[0]

        account_status = (
            AccountStatus.ACTIVE if rng.random() < 0.95 else AccountStatus.SUSPENDED
        )

        customer = Customer(
            customer_id=f"CUS-{index:05d}",
            company_name=fake.unique.company(),
            contact_name=fake.name(),
            email=fake.unique.company_email(),
            account_status=account_status,
            customer_tier=tier,
            billing_address=billing_address,
            shipping_address=shipping_address,
            date_created=fake.date_between_dates(
                date_start=date(2022, 1, 1),
                date_end=REFERENCE_DATE,
            ),
        )

        customers.append(customer)

    return customers


def generate_products(
    *,
    seed: int = 42,
) -> list[Product]:
    rng = Random(seed)

    products: list[Product] = []

    product_number = 1001

    for category, product_names in PRODUCT_CATALOG.items():
        for product_name in product_names:
            price_cents = rng.randint(1000, 50000)

            product = Product(
                product_id=f"P{product_number}",
                product_name=product_name,
                category=category,
                unit_price=Decimal(price_cents) / Decimal(100),
                active=rng.random() < 0.95,
                replacement_eligible=rng.random() < 0.90,
            )

            products.append(product)
            product_number += 1

    return products


def generate_warehouses() -> list[Warehouse]:
    return [
        Warehouse(
            warehouse_id="WH-NORTH",
            warehouse_name="Northstar North Distribution Centre",
        ),
        Warehouse(
            warehouse_id="WH-CENTRAL",
            warehouse_name="Northstar Central Distribution Centre",
        ),
        Warehouse(
            warehouse_id="WH-SOUTH",
            warehouse_name="Northstar South Distribution Centre",
        ),
    ]


def generate_inventory(
    products: list[Product],
    warehouses: list[Warehouse],
    *,
    seed: int = 42,
) -> list[InventoryRecord]:
    rng = Random(seed)

    inventory: list[InventoryRecord] = []

    for warehouse in warehouses:
        for product in products:
            quantity_available = rng.randint(0, 100)
            quantity_reserved = rng.randint(0, quantity_available)

            inventory.append(
                InventoryRecord(
                    warehouse_id=warehouse.warehouse_id,
                    product_id=product.product_id,
                    quantity_available=quantity_available,
                    quantity_reserved=quantity_reserved,
                )
            )

    return inventory


def generate_base_world(
    *,
    seed: int = 42,
) -> NorthstarBaseWorld:
    customers = generate_customers(seed=seed)
    products = generate_products(seed=seed)
    warehouses = generate_warehouses()

    inventory = generate_inventory(
        products,
        warehouses,
        seed=seed,
    )

    return NorthstarBaseWorld(
        customers=customers,
        products=products,
        warehouses=warehouses,
        inventory=inventory,
    )


def generate_orders(
    customers: list[Customer],
    products: list[Product],
    *,
    count: int = 400,
    seed: int = 42,
) -> list[Order]:
    rng = Random(seed)

    active_products = [product for product in products if product.active]

    start_date = date(2026, 1, 1)

    orders: list[Order] = []

    for index in range(1, count + 1):
        customer = rng.choice(customers)

        status = rng.choices(
            population=[
                OrderStatus.PENDING,
                OrderStatus.CONFIRMED,
                OrderStatus.PROCESSING,
                OrderStatus.SHIPPED,
                OrderStatus.DELIVERED,
                OrderStatus.CANCELLED,
            ],
            weights=[
                5,
                10,
                15,
                30,
                35,
                5,
            ],
            k=1,
        )[0]

        latest_order_date = REFERENCE_DATE

        if status == OrderStatus.DELIVERED:
            latest_order_date = REFERENCE_DATE - timedelta(days=4)
        elif status == OrderStatus.SHIPPED:
            latest_order_date = REFERENCE_DATE - timedelta(days=1)

        date_range_days = (latest_order_date - start_date).days

        order_date = start_date + timedelta(days=rng.randint(0, date_range_days))

        number_of_products = rng.randint(1, 4)

        selected_products = rng.sample(
            active_products,
            k=number_of_products,
        )

        order_items: list[OrderItem] = []

        for product in selected_products:
            quantity = rng.randint(1, 5)

            line_total = _money(product.unit_price * quantity)

            order_items.append(
                OrderItem(
                    product_id=product.product_id,
                    quantity=quantity,
                    unit_price=product.unit_price,
                    line_total=line_total,
                )
            )

        subtotal = sum(
            (item.line_total for item in order_items),
            start=Decimal("0.00"),
        )

        shipping_charge = (
            Decimal("0.00") if subtotal >= Decimal("500.00") else Decimal("18.00")
        )

        tax = _money(subtotal * TAX_RATE)

        total_amount = _money(subtotal + shipping_charge + tax)

        orders.append(
            Order(
                order_id=f"ORD-{index:05d}",
                customer_id=customer.customer_id,
                order_date=order_date,
                order_status=status,
                shipping_address=customer.shipping_address,
                billing_address=customer.billing_address,
                order_items=order_items,
                subtotal=subtotal,
                shipping_charge=shipping_charge,
                tax=tax,
                total_amount=total_amount,
            )
        )

    return orders


def generate_shipments(
    orders: list[Order],
    *,
    seed: int = 42,
) -> list[Shipment]:
    rng = Random(seed)

    carriers = [
        "Northstar Freight",
        "RapidShip",
        "ParcelPath",
        "Continental Logistics",
    ]

    shipments: list[Shipment] = []

    shipment_number = 1

    for order in orders:
        if order.order_status not in {
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        }:
            continue

        shipped_date = min(
            order.order_date + timedelta(days=rng.randint(1, 3)),
            REFERENCE_DATE,
        )

        expected_delivery_date = shipped_date + timedelta(days=rng.randint(2, 7))

        if order.order_status == OrderStatus.DELIVERED:
            shipment_status = ShipmentStatus.DELIVERED

            actual_delivery_date = min(
                expected_delivery_date + timedelta(days=rng.randint(-2, 2)),
                REFERENCE_DATE,
            )

        else:
            shipment_status = rng.choices(
                population=[
                    ShipmentStatus.IN_TRANSIT,
                    ShipmentStatus.DELAYED,
                    ShipmentStatus.LOST,
                    ShipmentStatus.RETURNED_TO_SENDER,
                ],
                weights=[
                    65,
                    20,
                    10,
                    5,
                ],
                k=1,
            )[0]

            actual_delivery_date = None

        shipments.append(
            Shipment(
                shipment_id=f"SHP-{shipment_number:05d}",
                order_id=order.order_id,
                carrier=rng.choice(carriers),
                tracking_reference=(
                    f"TRK-{order.order_id.removeprefix('ORD-')}-"
                    f"{rng.randint(1000, 9999)}"
                ),
                shipped_date=shipped_date,
                expected_delivery_date=expected_delivery_date,
                actual_delivery_date=actual_delivery_date,
                shipment_status=shipment_status,
            )
        )

        shipment_number += 1

    return shipments


def generate_invoices(
    orders: list[Order],
    *,
    seed: int = 42,
) -> list[Invoice]:
    rng = Random(seed)

    invoices: list[Invoice] = []

    invoice_number = 1

    for order in orders:
        if order.order_status in {
            OrderStatus.PENDING,
            OrderStatus.CANCELLED,
        }:
            continue

        if order.order_status == OrderStatus.DELIVERED:
            payment_status = rng.choices(
                population=[
                    PaymentStatus.PAID,
                    PaymentStatus.UNPAID,
                ],
                weights=[85, 15],
                k=1,
            )[0]

        else:
            payment_status = rng.choices(
                population=[
                    PaymentStatus.PAID,
                    PaymentStatus.UNPAID,
                ],
                weights=[55, 45],
                k=1,
            )[0]

        invoices.append(
            Invoice(
                invoice_id=f"INV-{invoice_number:05d}",
                order_id=order.order_id,
                issue_date=min(
                    order.order_date + timedelta(days=rng.randint(0, 2)),
                    REFERENCE_DATE,
                ),
                subtotal=order.subtotal,
                shipping_charge=order.shipping_charge,
                tax=order.tax,
                total=order.total_amount,
                payment_status=payment_status,
            )
        )

        invoice_number += 1

    return invoices


def generate_snapshot(
    *,
    seed: int = 42,
) -> NorthstarSnapshot:
    base_world = generate_base_world(seed=seed)

    orders = generate_orders(
        base_world.customers,
        base_world.products,
        seed=seed + 1,
    )

    shipments = generate_shipments(
        orders,
        seed=seed + 2,
    )

    invoices = generate_invoices(
        orders,
        seed=seed + 3,
    )

    return NorthstarSnapshot(
        customers=base_world.customers,
        products=base_world.products,
        warehouses=base_world.warehouses,
        inventory=base_world.inventory,
        orders=orders,
        shipments=shipments,
        invoices=invoices,
        support_tickets=[],
    )
