from decimal import Decimal

import pytest
from pydantic import ValidationError

from agent_reliability_lab.synthetic.models import InventoryRecord, OrderItem


def test_valid_inventory_record() -> None:
    record = InventoryRecord(
        warehouse_id="WH-NORTH",
        product_id="P1001",
        quantity_available=20,
        quantity_reserved=5,
    )

    assert record.quantity_available - record.quantity_reserved == 15


def test_reserved_inventory_cannot_exceed_available() -> None:
    with pytest.raises(ValidationError):
        InventoryRecord(
            warehouse_id="WH-NORTH",
            product_id="P1001",
            quantity_available=5,
            quantity_reserved=6,
        )


def test_order_item_total_must_be_correct() -> None:
    with pytest.raises(ValidationError):
        OrderItem(
            product_id="P1001",
            quantity=2,
            unit_price=Decimal("10.00"),
            line_total=Decimal("19.99"),
        )


def test_valid_order_item() -> None:
    item = OrderItem(
        product_id="P1001",
        quantity=3,
        unit_price=Decimal("12.50"),
        line_total=Decimal("37.50"),
    )

    assert item.line_total == Decimal("37.50")
