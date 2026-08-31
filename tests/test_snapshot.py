from agent_reliability_lab.synthetic.generator import REFERENCE_DATE, generate_snapshot
from agent_reliability_lab.synthetic.models import OrderStatus, ShipmentStatus


def test_snapshot_contains_expected_orders() -> None:
    world = generate_snapshot(seed=42)

    assert len(world.orders) == 400
    assert len(world.shipments) > 0
    assert len(world.invoices) > 0


def test_every_order_references_a_real_customer() -> None:
    world = generate_snapshot(seed=42)

    customer_ids = {customer.customer_id for customer in world.customers}

    for order in world.orders:
        assert order.customer_id in customer_ids


def test_every_order_item_references_a_real_product() -> None:
    world = generate_snapshot(seed=42)

    product_ids = {product.product_id for product in world.products}

    for order in world.orders:
        for item in order.order_items:
            assert item.product_id in product_ids


def test_every_shipment_references_a_real_order() -> None:
    world = generate_snapshot(seed=42)

    order_ids = {order.order_id for order in world.orders}

    for shipment in world.shipments:
        assert shipment.order_id in order_ids


def test_shipped_and_delivered_orders_have_shipments() -> None:
    world = generate_snapshot(seed=42)

    shipment_order_ids = {shipment.order_id for shipment in world.shipments}

    for order in world.orders:
        if order.order_status in {
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        }:
            assert order.order_id in shipment_order_ids

        else:
            assert order.order_id not in shipment_order_ids


def test_delivered_orders_have_delivered_shipments() -> None:
    world = generate_snapshot(seed=42)

    shipment_by_order = {shipment.order_id: shipment for shipment in world.shipments}

    for order in world.orders:
        if order.order_status == OrderStatus.DELIVERED:
            shipment = shipment_by_order[order.order_id]

            assert shipment.shipment_status == ShipmentStatus.DELIVERED

            assert shipment.actual_delivery_date is not None


def test_invoices_match_their_orders() -> None:
    world = generate_snapshot(seed=42)

    orders_by_id = {order.order_id: order for order in world.orders}

    for invoice in world.invoices:
        order = orders_by_id[invoice.order_id]

        assert invoice.subtotal == order.subtotal
        assert invoice.shipping_charge == order.shipping_charge
        assert invoice.tax == order.tax
        assert invoice.total == order.total_amount


def test_pending_and_cancelled_orders_do_not_have_invoices() -> None:
    world = generate_snapshot(seed=42)

    invoice_order_ids = {invoice.order_id for invoice in world.invoices}

    for order in world.orders:
        if order.order_status in {
            OrderStatus.PENDING,
            OrderStatus.CANCELLED,
        }:
            assert order.order_id not in invoice_order_ids


def test_snapshot_is_reproducible() -> None:
    first_world = generate_snapshot(seed=42)
    second_world = generate_snapshot(seed=42)

    assert first_world == second_world


def test_historical_events_do_not_occur_after_reference_date() -> None:
    world = generate_snapshot(seed=42)

    for order in world.orders:
        assert order.order_date <= REFERENCE_DATE

    for shipment in world.shipments:
        if shipment.shipped_date is not None:
            assert shipment.shipped_date <= REFERENCE_DATE

        if shipment.actual_delivery_date is not None:
            assert shipment.actual_delivery_date <= REFERENCE_DATE

    for invoice in world.invoices:
        assert invoice.issue_date <= REFERENCE_DATE


def test_shipment_chronology_is_consistent() -> None:
    world = generate_snapshot(seed=42)

    for shipment in world.shipments:
        if (
            shipment.shipped_date is not None
            and shipment.expected_delivery_date is not None
        ):
            assert shipment.shipped_date <= shipment.expected_delivery_date

        if (
            shipment.shipped_date is not None
            and shipment.actual_delivery_date is not None
        ):
            assert shipment.shipped_date <= shipment.actual_delivery_date
