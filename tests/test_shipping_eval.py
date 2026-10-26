from agent_reliability_lab.agent.models import (
    AgentMessage,
    AgentRunResult,
    AgentRunStatus,
    MessageRole,
    ToolCall,
)
from agent_reliability_lab.evals.shipping import (
    score_shipping_run,
)


def test_shipping_scorer_recognises_complete_evidence() -> None:
    result = AgentRunResult(
        status=AgentRunStatus.COMPLETED,
        final_answer="The shipment is lost.",
        turns=2,
        tool_call_count=2,
        messages=[
            AgentMessage(
                role=MessageRole.ASSISTANT,
                tool_calls=[
                    ToolCall(
                        call_id="1",
                        name="get_order",
                        arguments={
                            "order_id": "ORD-00043",
                        },
                    ),
                    ToolCall(
                        call_id="2",
                        name="track_shipment",
                        arguments={
                            "order_id": "ORD-00043",
                        },
                    ),
                ],
            ),
            AgentMessage(
                role=MessageRole.TOOL,
                tool_name="track_shipment",
                tool_call_id="2",
                content=(
                    '{"status":"success","data":{"shipment":'
                    '{"shipment_status":"lost"}},"error_code":null,'
                    '"message":"Shipment retrieved successfully."}'
                ),
            ),
        ],
    )

    score = score_shipping_run(
        result,
        expected_order_id="ORD-00043",
        expected_shipment_status="lost",
    )

    assert score["tool_selection_pass"] is True
    assert score["argument_accuracy_pass"] is True
    assert score["evidence_complete"] is True
    assert score["observed_shipment_status"] == "lost"
