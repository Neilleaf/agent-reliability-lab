from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine

from agent_reliability_lab.tools.models import (
    ToolResponse,
    ToolStatus,
)
from agent_reliability_lab.tools.read_tools import (
    check_inventory_tool,
    get_customer_tool,
    get_damage_report_tool,
    get_invoice_tool,
    get_order_tool,
    get_policy_tool,
    get_product_tool,
    track_shipment_tool,
)


class CustomerLookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(
        description="Northstar customer ID, for example CUS-00100."
    )


class OrderLookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(description="Northstar order ID, for example ORD-00010.")


class ShipmentLookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(
        description="Northstar order ID whose shipment should be retrieved."
    )


class InventoryLookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(description="Northstar product ID, for example P1001.")


ToolExecutor = Callable[[Engine, Any], ToolResponse]


class PolicyLookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    policy_id: str = Field(
        description="Policy ID: refund, damage, invoice, or replacement."
    )


class DamageReportLookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: str
    product_id: str


class ToolDefinition(BaseModel):
    """Description and execution metadata for an agent-facing tool."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
    )

    name: str
    description: str
    argument_model: type[BaseModel]
    executor: Callable[..., ToolResponse]


TOOL_REGISTRY = {
    "get_product": ToolDefinition(
        name="get_product",
        description="Retrieve product facts and replacement eligibility.",
        argument_model=InventoryLookupArgs,
        executor=get_product_tool,
    ),
    "get_invoice": ToolDefinition(
        name="get_invoice",
        description="Retrieve the stored invoice for an order, including payment status and monetary fields.",
        argument_model=OrderLookupArgs,
        executor=get_invoice_tool,
    ),
    "get_policy": ToolDefinition(
        name="get_policy",
        description="Retrieve authoritative refund, damage, invoice, or replacement policy and the assessment date.",
        argument_model=PolicyLookupArgs,
        executor=get_policy_tool,
    ),
    "get_damage_report": ToolDefinition(
        name="get_damage_report",
        description="Retrieve verified/unverified damage evidence for an exact order and product.",
        argument_model=DamageReportLookupArgs,
        executor=get_damage_report_tool,
    ),
    "get_customer": ToolDefinition(
        name="get_customer",
        description=("Retrieve a Northstar customer using an exact customer ID."),
        argument_model=CustomerLookupArgs,
        executor=get_customer_tool,
    ),
    "get_order": ToolDefinition(
        name="get_order",
        description=(
            "Retrieve a Northstar order, including its order items, "
            "using an exact order ID."
        ),
        argument_model=OrderLookupArgs,
        executor=get_order_tool,
    ),
    "track_shipment": ToolDefinition(
        name="track_shipment",
        description=("Retrieve shipment information for a Northstar order."),
        argument_model=ShipmentLookupArgs,
        executor=track_shipment_tool,
    ),
    "check_inventory": ToolDefinition(
        name="check_inventory",
        description=(
            "Check current inventory for a product across all Northstar "
            "warehouses, including usable replacement quantity."
        ),
        argument_model=InventoryLookupArgs,
        executor=check_inventory_tool,
    ),
}


def get_tool_definition(
    tool_name: str,
) -> ToolDefinition | None:
    """Return a registered tool definition by name."""
    return TOOL_REGISTRY.get(tool_name)


def execute_tool(
    engine: Engine,
    tool_name: str,
    arguments: dict[str, object],
) -> ToolResponse:
    """Validate arguments and execute a registered tool."""
    definition = get_tool_definition(tool_name)

    if definition is None:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="UNKNOWN_TOOL",
            message=f"Tool {tool_name} is not registered.",
        )

    try:
        validated_arguments = definition.argument_model.model_validate(arguments)
    except ValueError as exc:
        return ToolResponse(
            status=ToolStatus.ERROR,
            error_code="INVALID_TOOL_ARGUMENTS",
            message=str(exc),
        )

    return definition.executor(
        engine,
        **validated_arguments.model_dump(),
    )


def get_tool_schema(
    tool_name: str,
) -> dict[str, object] | None:
    """Return a provider-neutral schema for a registered tool."""
    definition = get_tool_definition(tool_name)

    if definition is None:
        return None

    return {
        "name": definition.name,
        "description": definition.description,
        "parameters": definition.argument_model.model_json_schema(),
    }


def get_all_tool_schemas() -> list[dict[str, object]]:
    """Return schemas for all registered tools."""
    return [
        schema
        for tool_name in TOOL_REGISTRY
        if (schema := get_tool_schema(tool_name)) is not None
    ]
