from sqlalchemy import func, select

from agent_reliability_lab.storage.database import create_database_engine
from agent_reliability_lab.storage.schema import (
    customers,
    inventory,
    invoices,
    order_items,
    orders,
    products,
    shipments,
    warehouses,
)
from agent_reliability_lab.storage.seeder import seed_database
from agent_reliability_lab.synthetic.generator import generate_snapshot


def test_seed_database_matches_snapshot_counts(tmp_path) -> None:
    database_path = tmp_path / "northstar.db"

    engine = create_database_engine(database_path)
    world = generate_snapshot(seed=42)

    seed_database(
        engine,
        world,
    )

    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(customers)) == len(
            world.customers
        )

        assert connection.scalar(select(func.count()).select_from(products)) == len(
            world.products
        )

        assert connection.scalar(select(func.count()).select_from(warehouses)) == len(
            world.warehouses
        )

        assert connection.scalar(select(func.count()).select_from(inventory)) == len(
            world.inventory
        )

        assert connection.scalar(select(func.count()).select_from(orders)) == len(
            world.orders
        )

        assert connection.scalar(select(func.count()).select_from(shipments)) == len(
            world.shipments
        )

        assert connection.scalar(select(func.count()).select_from(invoices)) == len(
            world.invoices
        )

        expected_order_items = sum(len(order.order_items) for order in world.orders)

        assert (
            connection.scalar(select(func.count()).select_from(order_items))
            == expected_order_items
        )


def test_reseeding_does_not_duplicate_data(tmp_path) -> None:
    database_path = tmp_path / "northstar.db"

    engine = create_database_engine(database_path)
    world = generate_snapshot(seed=42)

    seed_database(
        engine,
        world,
    )

    seed_database(
        engine,
        world,
    )

    with engine.connect() as connection:
        customer_count = connection.scalar(select(func.count()).select_from(customers))

        order_count = connection.scalar(select(func.count()).select_from(orders))

    assert customer_count == 100
    assert order_count == 400
