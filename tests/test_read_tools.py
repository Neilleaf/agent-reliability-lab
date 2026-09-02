import pytest

from agent_reliability_lab.storage.database import create_database_engine
from agent_reliability_lab.storage.seeder import seed_database
from agent_reliability_lab.synthetic.generator import generate_snapshot
from agent_reliability_lab.tools.models import ToolStatus
from agent_reliability_lab.tools.read_tools import (
    check_inventory_tool,
    get_customer_tool,
    get_order_tool,
    track_shipment_tool,
)


@pytest.fixture
def seeded_engine(tmp_path):
    engine = create_database_engine(tmp_path / "northstar.db")

    world = generate_snapshot(seed=42)
    seed_database(engine, world)

    return engine


def test_get_customer_tool_returns_structured_success(
    seeded_engine,
) -> None:
    result = get_customer_tool(
        seeded_engine,
        "CUS-00100",
    )

    assert result.status == ToolStatus.SUCCESS
    assert result.error_code is None
    assert result.data is not None

    customer = result.data["customer"]

    assert isinstance(customer, dict)
    assert customer["customer_id"] == "CUS-00100"


def test_get_customer_tool_returns_explicit_not_found(
    seeded_engine,
) -> None:
    result = get_customer_tool(
        seeded_engine,
        "CUS-99999",
    )

    assert result.status == ToolStatus.ERROR
    assert result.error_code == "CUSTOMER_NOT_FOUND"
    assert result.data is None


def test_get_order_tool_returns_structured_order(
    seeded_engine,
) -> None:
    world = generate_snapshot(seed=42)
    expected_order = world.orders[0]

    result = get_order_tool(
        seeded_engine,
        expected_order.order_id,
    )

    assert result.status == ToolStatus.SUCCESS
    assert result.data is not None

    order = result.data["order"]

    assert isinstance(order, dict)
    assert order["order_id"] == expected_order.order_id


def test_get_order_tool_returns_explicit_not_found(
    seeded_engine,
) -> None:
    result = get_order_tool(
        seeded_engine,
        "ORD-99999",
    )

    assert result.status == ToolStatus.ERROR
    assert result.error_code == "ORDER_NOT_FOUND"


def test_track_shipment_tool_returns_shipment(
    seeded_engine,
) -> None:
    world = generate_snapshot(seed=42)
    expected_shipment = world.shipments[0]

    result = track_shipment_tool(
        seeded_engine,
        expected_shipment.order_id,
    )

    assert result.status == ToolStatus.SUCCESS
    assert result.data is not None

    shipment = result.data["shipment"]

    assert isinstance(shipment, dict)
    assert shipment["shipment_id"] == expected_shipment.shipment_id


def test_track_shipment_tool_distinguishes_missing_order(
    seeded_engine,
) -> None:
    result = track_shipment_tool(
        seeded_engine,
        "ORD-99999",
    )

    assert result.status == ToolStatus.ERROR
    assert result.error_code == "ORDER_NOT_FOUND"


def test_track_shipment_tool_distinguishes_unshipped_order(
    seeded_engine,
) -> None:
    world = generate_snapshot(seed=42)

    shipment_order_ids = {shipment.order_id for shipment in world.shipments}

    order_without_shipment = next(
        order for order in world.orders if order.order_id not in shipment_order_ids
    )

    result = track_shipment_tool(
        seeded_engine,
        order_without_shipment.order_id,
    )

    assert result.status == ToolStatus.ERROR
    assert result.error_code == "SHIPMENT_NOT_FOUND"


def test_check_inventory_tool_calculates_usable_inventory(
    seeded_engine,
) -> None:
    result = check_inventory_tool(
        seeded_engine,
        "P1001",
    )

    assert result.status == ToolStatus.SUCCESS
    assert result.data is not None

    locations = result.data["locations"]

    assert isinstance(locations, list)
    assert len(locations) == 3

    for location in locations:
        assert isinstance(location, dict)

        assert location["usable_quantity"] == (
            location["quantity_available"] - location["quantity_reserved"]
        )


def test_check_inventory_tool_returns_product_not_found(
    seeded_engine,
) -> None:
    result = check_inventory_tool(
        seeded_engine,
        "P9999",
    )

    assert result.status == ToolStatus.ERROR
    assert result.error_code == "PRODUCT_NOT_FOUND"


def test_tool_response_is_json_serializable(
    seeded_engine,
) -> None:
    result = get_order_tool(
        seeded_engine,
        generate_snapshot(seed=42).orders[0].order_id,
    )

    payload = result.model_dump_json()

    assert isinstance(payload, str)
    assert '"status":"success"' in payload
