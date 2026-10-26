import pytest

from agent_reliability_lab.agent.fake_model import ScriptedModel
from agent_reliability_lab.agent.models import (
    AgentRunStatus,
    ModelResponse,
    ToolCall,
)
from agent_reliability_lab.agent.runner import AgentRunner
from agent_reliability_lab.storage.database import create_database_engine
from agent_reliability_lab.storage.seeder import seed_database
from agent_reliability_lab.synthetic.generator import generate_snapshot


@pytest.fixture
def seeded_engine(tmp_path):
    engine = create_database_engine(tmp_path / "northstar.db")

    world = generate_snapshot(seed=42)
    seed_database(engine, world)

    return engine


def test_agent_can_return_final_answer_without_tools(
    seeded_engine,
) -> None:
    model = ScriptedModel(
        responses=[
            ModelResponse(content="I cannot determine that without an order ID.")
        ]
    )

    runner = AgentRunner(
        engine=seeded_engine,
        model=model,
    )

    result = runner.run("Where is my order?")

    assert result.status == AgentRunStatus.COMPLETED
    assert result.final_answer == "I cannot determine that without an order ID."
    assert result.turns == 1
    assert result.tool_call_count == 0


def test_agent_can_call_tool_then_answer(
    seeded_engine,
) -> None:
    world = generate_snapshot(seed=42)
    expected_order = world.orders[0]

    model = ScriptedModel(
        responses=[
            ModelResponse(
                tool_calls=[
                    ToolCall(
                        call_id="call-1",
                        name="get_order",
                        arguments={
                            "order_id": expected_order.order_id,
                        },
                    )
                ]
            ),
            ModelResponse(content="I found the order."),
        ]
    )

    runner = AgentRunner(
        engine=seeded_engine,
        model=model,
    )

    result = runner.run(f"Please check order {expected_order.order_id}.")

    assert result.status == AgentRunStatus.COMPLETED
    assert result.final_answer == "I found the order."
    assert result.turns == 2
    assert result.tool_call_count == 1


def test_agent_can_use_multiple_tools(
    seeded_engine,
) -> None:
    world = generate_snapshot(seed=42)

    expected_shipment = world.shipments[0]
    order_id = expected_shipment.order_id

    model = ScriptedModel(
        responses=[
            ModelResponse(
                tool_calls=[
                    ToolCall(
                        call_id="call-1",
                        name="get_order",
                        arguments={
                            "order_id": order_id,
                        },
                    )
                ]
            ),
            ModelResponse(
                tool_calls=[
                    ToolCall(
                        call_id="call-2",
                        name="track_shipment",
                        arguments={
                            "order_id": order_id,
                        },
                    )
                ]
            ),
            ModelResponse(content="I checked the order and shipment."),
        ]
    )

    runner = AgentRunner(
        engine=seeded_engine,
        model=model,
    )

    result = runner.run(f"Investigate shipment for {order_id}.")

    assert result.status == AgentRunStatus.COMPLETED
    assert result.turns == 3
    assert result.tool_call_count == 2


def test_agent_survives_unknown_tool_call(
    seeded_engine,
) -> None:
    model = ScriptedModel(
        responses=[
            ModelResponse(
                tool_calls=[
                    ToolCall(
                        call_id="call-1",
                        name="delete_everything",
                        arguments={},
                    )
                ]
            ),
            ModelResponse(content="That action is unavailable."),
        ]
    )

    runner = AgentRunner(
        engine=seeded_engine,
        model=model,
    )

    result = runner.run("Delete all customer records.")

    assert result.status == AgentRunStatus.COMPLETED
    assert result.tool_call_count == 1

    tool_messages = [
        message for message in result.messages if message.role.value == "tool"
    ]

    assert len(tool_messages) == 1
    assert tool_messages[0].content is not None
    assert "UNKNOWN_TOOL" in tool_messages[0].content


def test_agent_survives_invalid_tool_arguments(
    seeded_engine,
) -> None:
    model = ScriptedModel(
        responses=[
            ModelResponse(
                tool_calls=[
                    ToolCall(
                        call_id="call-1",
                        name="get_order",
                        arguments={
                            "banana": "ORD-00010",
                        },
                    )
                ]
            ),
            ModelResponse(content="I could not retrieve the order."),
        ]
    )

    runner = AgentRunner(
        engine=seeded_engine,
        model=model,
    )

    result = runner.run("Find the order.")

    assert result.status == AgentRunStatus.COMPLETED

    tool_messages = [
        message for message in result.messages if message.role.value == "tool"
    ]

    assert "INVALID_TOOL_ARGUMENTS" in tool_messages[0].content


def test_agent_stops_at_max_turns(
    seeded_engine,
) -> None:
    world = generate_snapshot(seed=42)
    order_id = world.orders[0].order_id

    model = ScriptedModel(
        responses=[
            ModelResponse(
                tool_calls=[
                    ToolCall(
                        call_id="call-1",
                        name="get_order",
                        arguments={
                            "order_id": order_id,
                        },
                    )
                ]
            ),
            ModelResponse(
                tool_calls=[
                    ToolCall(
                        call_id="call-2",
                        name="get_order",
                        arguments={
                            "order_id": order_id,
                        },
                    )
                ]
            ),
        ]
    )

    runner = AgentRunner(
        engine=seeded_engine,
        model=model,
        max_turns=2,
    )

    result = runner.run("Keep checking the order.")

    assert result.status == AgentRunStatus.MAX_TURNS_REACHED
    assert result.turns == 2
    assert result.tool_call_count == 2


def test_agent_handles_model_failure(
    seeded_engine,
) -> None:
    model = ScriptedModel(
        responses=[],
    )

    runner = AgentRunner(
        engine=seeded_engine,
        model=model,
    )

    result = runner.run("Check something.")

    assert result.status == AgentRunStatus.MODEL_ERROR
    assert result.final_answer is None
