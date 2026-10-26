from agent_reliability_lab.agent.ollama_model import OllamaModelClient
from agent_reliability_lab.agent.runner import AgentRunner
from agent_reliability_lab.storage.database import create_database_engine
from agent_reliability_lab.storage.seeder import seed_database
from agent_reliability_lab.synthetic.generator import generate_snapshot


def main() -> None:
    world = generate_snapshot(seed=42)

    lost_shipment = next(
        shipment
        for shipment in world.shipments
        if shipment.shipment_status.value == "lost"
    )

    order_id = lost_shipment.order_id

    engine = create_database_engine()
    seed_database(engine, world)

    model = OllamaModelClient(
        model="qwen3:4b-instruct",
    )

    runner = AgentRunner(
        engine=engine,
        model=model,
        max_turns=8,
    )

    task = (
        f"A customer says order {order_id} is lost. "
        "Investigate the order using Northstar's records and tell me "
        "what is actually happening. Do not assume the customer's "
        "claim is correct."
    )

    print("=" * 70)
    print("TASK")
    print("=" * 70)
    print(task)

    result = runner.run(task)

    print("\n" + "=" * 70)
    print("TRACE")
    print("=" * 70)

    for index, message in enumerate(result.messages, start=1):
        print(f"\n[{index}] {message.role.value.upper()}")

        if message.content:
            print(message.content)

        for tool_call in message.tool_calls:
            print(f"TOOL CALL: {tool_call.name}({tool_call.arguments})")

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)

    print(f"Status: {result.status.value}")
    print(f"Turns: {result.turns}")
    print(f"Tool calls: {result.tool_call_count}")
    print(f"\nFinal answer:\n{result.final_answer}")


if __name__ == "__main__":
    main()
