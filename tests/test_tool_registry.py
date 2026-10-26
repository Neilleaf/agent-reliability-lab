import pytest

from agent_reliability_lab.storage.database import create_database_engine
from agent_reliability_lab.storage.seeder import seed_database
from agent_reliability_lab.synthetic.generator import generate_snapshot
from agent_reliability_lab.tools.models import ToolStatus
from agent_reliability_lab.tools.registry import (
    TOOL_REGISTRY,
    execute_tool,
    get_all_tool_schemas,
    get_tool_definition,
    get_tool_schema,
)


@pytest.fixture
def seeded_engine(tmp_path):
    engine = create_database_engine(tmp_path / "northstar.db")

    world = generate_snapshot(seed=42)
    seed_database(engine, world)

    return engine


def test_registry_contains_expected_tools() -> None:
    assert set(TOOL_REGISTRY) == {
        "get_customer",
        "get_order",
        "track_shipment",
        "check_inventory",
        "get_product",
        "get_invoice",
        "get_policy",
        "get_damage_report",
    }


def test_get_tool_definition_returns_registered_tool() -> None:
    definition = get_tool_definition("get_order")

    assert definition is not None
    assert definition.name == "get_order"


def test_get_tool_definition_returns_none_for_unknown_tool() -> None:
    assert get_tool_definition("delete_everything") is None


def test_get_order_schema_contains_required_argument() -> None:
    schema = get_tool_schema("get_order")

    assert schema is not None
    assert schema["name"] == "get_order"

    parameters = schema["parameters"]

    assert isinstance(parameters, dict)
    assert "order_id" in parameters["properties"]
    assert "order_id" in parameters["required"]


def test_all_tool_schemas_match_registry() -> None:
    schemas = get_all_tool_schemas()

    assert len(schemas) == len(TOOL_REGISTRY)

    schema_names = {schema["name"] for schema in schemas}

    assert schema_names == set(TOOL_REGISTRY)


def test_execute_tool_runs_registered_tool(
    seeded_engine,
) -> None:
    result = execute_tool(
        seeded_engine,
        "get_customer",
        {
            "customer_id": "CUS-00100",
        },
    )

    assert result.status == ToolStatus.SUCCESS
    assert result.data is not None


def test_execute_tool_rejects_unknown_tool(
    seeded_engine,
) -> None:
    result = execute_tool(
        seeded_engine,
        "delete_everything",
        {},
    )

    assert result.status == ToolStatus.ERROR
    assert result.error_code == "UNKNOWN_TOOL"


def test_execute_tool_rejects_invalid_arguments(
    seeded_engine,
) -> None:
    result = execute_tool(
        seeded_engine,
        "get_order",
        {
            "wrong_argument": "ORD-00010",
        },
    )

    assert result.status == ToolStatus.ERROR
    assert result.error_code == "INVALID_TOOL_ARGUMENTS"


def test_execute_tool_rejects_extra_arguments(
    seeded_engine,
) -> None:
    result = execute_tool(
        seeded_engine,
        "get_order",
        {
            "order_id": "ORD-00010",
            "admin": True,
        },
    )

    assert result.status == ToolStatus.ERROR
    assert result.error_code == "INVALID_TOOL_ARGUMENTS"
