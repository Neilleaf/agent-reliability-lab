from datetime import date

import pytest
from sqlalchemy import insert, inspect
from sqlalchemy.exc import IntegrityError

from agent_reliability_lab.storage.database import (
    create_database_engine,
    initialise_database,
)
from agent_reliability_lab.storage.schema import orders


def test_database_creates_expected_tables(tmp_path) -> None:
    database_path = tmp_path / "test_northstar.db"

    engine = create_database_engine(database_path)
    initialise_database(engine)

    inspector = inspect(engine)

    table_names = set(inspector.get_table_names())

    assert table_names == {
        "customers",
        "products",
        "warehouses",
        "inventory",
        "orders",
        "order_items",
        "shipments",
        "invoices",
        "support_tickets",
        "damage_reports",
    }


def test_database_rejects_order_for_unknown_customer(tmp_path) -> None:
    database_path = tmp_path / "test_northstar.db"

    engine = create_database_engine(database_path)
    initialise_database(engine)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            insert(orders),
            {
                "order_id": "ORD-99999",
                "customer_id": "CUS-99999",
                "order_date": date(2026, 8, 1),
                "order_status": "confirmed",
                "shipping_line1": "1 Test Street",
                "shipping_city": "Test City",
                "shipping_state": "Texas",
                "shipping_postal_code": "00000",
                "shipping_country": "United States",
                "billing_line1": "1 Test Street",
                "billing_city": "Test City",
                "billing_state": "Texas",
                "billing_postal_code": "00000",
                "billing_country": "United States",
                "subtotal": 100,
                "shipping_charge": 18,
                "tax": 8.25,
                "total_amount": 126.25,
            },
        )
