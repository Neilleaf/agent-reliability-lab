from agent_reliability_lab.synthetic.generator import generate_base_world


def test_base_world_contains_expected_counts() -> None:
    world = generate_base_world(seed=42)

    assert len(world.customers) == 100
    assert len(world.products) == 50
    assert len(world.warehouses) == 3
    assert len(world.inventory) == 150


def test_generation_is_reproducible() -> None:
    first_world = generate_base_world(seed=42)
    second_world = generate_base_world(seed=42)

    assert first_world == second_world


def test_different_seeds_create_different_worlds() -> None:
    first_world = generate_base_world(seed=42)
    second_world = generate_base_world(seed=99)

    assert first_world != second_world


def test_inventory_references_valid_products_and_warehouses() -> None:
    world = generate_base_world(seed=42)

    product_ids = {product.product_id for product in world.products}
    warehouse_ids = {warehouse.warehouse_id for warehouse in world.warehouses}

    for record in world.inventory:
        assert record.product_id in product_ids
        assert record.warehouse_id in warehouse_ids


def test_reserved_inventory_never_exceeds_available_inventory() -> None:
    world = generate_base_world(seed=42)

    for record in world.inventory:
        assert record.quantity_reserved <= record.quantity_available
