import pytest

from agent_reliability_lab.retrieval.queries import (
    check_inventory,
    get_customer,
    get_order,
    get_product,
    track_shipment,
)
from agent_reliability_lab.storage.database import create_database_engine
from agent_reliability_lab.storage.seeder import seed_database
from agent_reliability_lab.synthetic.generator import generate_snapshot
from agent_reliability_lab.synthetic.models import OrderStatus


@pytest.fixture
def seeded_engine(tmp_path):
    engine = create_database_engine(tmp_path / "northstar.db")

    world = generate_snapshot(seed=42)
    seed_database(engine, world)

    return engine


def test_get_customer_returns_customer(seeded_engine) -> None:
    customer = get_customer(
        seeded_engine,
        "CUS-00100",
    )

    assert customer is not None
    assert customer.customer_id == "CUS-00100"
    assert customer.company_name == "Stone-Stark"


def test_get_customer_returns_none_for_unknown_customer(
    seeded_engine,
) -> None:
    customer = get_customer(
        seeded_engine,
        "CUS-99999",
    )

    assert customer is None


def test_get_order_returns_order_with_items(
    seeded_engine,
) -> None:
    order = get_order(
        seeded_engine,
        "ORD-00010",
    )

    assert order is not None
    assert order.order_id == "ORD-00010"
    assert order.customer_id == "CUS-00100"
    assert len(order.order_items) > 0


def test_get_order_returns_none_for_unknown_order(
    seeded_engine,
) -> None:
    order = get_order(
        seeded_engine,
        "ORD-99999",
    )

    assert order is None


def test_track_shipment_returns_expected_shipment(
    seeded_engine,
) -> None:
    world = generate_snapshot(seed=42)

    expected_shipment = next(
        shipment
        for shipment in world.shipments
        if shipment.shipment_status.value == "lost"
    )

    retrieved_shipment = track_shipment(
        seeded_engine,
        expected_shipment.order_id,
    )

    assert retrieved_shipment is not None
    assert retrieved_shipment == expected_shipment


def test_track_shipment_returns_none_when_order_has_no_shipment(
    seeded_engine,
) -> None:
    world = generate_snapshot(seed=42)

    order_without_shipment = next(
        order
        for order in world.orders
        if order.order_status
        not in {
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        }
    )

    shipment = track_shipment(
        seeded_engine,
        order_without_shipment.order_id,
    )

    assert shipment is None


def test_check_inventory_returns_all_warehouses(
    seeded_engine,
) -> None:
    records = check_inventory(
        seeded_engine,
        "P1001",
    )

    assert len(records) == 3

    warehouse_ids = {record.warehouse_id for record in records}

    assert warehouse_ids == {
        "WH-NORTH",
        "WH-CENTRAL",
        "WH-SOUTH",
    }


def test_check_inventory_returns_empty_for_unknown_product(
    seeded_engine,
) -> None:
    records = check_inventory(
        seeded_engine,
        "P9999",
    )

    assert records == []


def test_get_product_returns_product(seeded_engine) -> None:
    product = get_product(
        seeded_engine,
        "P1001",
    )

    assert product is not None
    assert product.product_id == "P1001"


def test_get_product_returns_none_for_unknown_product(
    seeded_engine,
) -> None:
    product = get_product(
        seeded_engine,
        "P9999",
    )

    assert product is None
