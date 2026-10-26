import json
from pathlib import Path

from agent_reliability_lab.agent.ollama_model import (
    OllamaModelClient,
)
from agent_reliability_lab.agent.runner import AgentRunner
from agent_reliability_lab.evals.shipping import (
    score_shipping_run,
)
from agent_reliability_lab.storage.database import (
    create_database_engine,
)
from agent_reliability_lab.storage.seeder import seed_database
from agent_reliability_lab.synthetic.generator import (
    generate_snapshot,
)

OUTPUT_DIRECTORY = Path("experiments/results/shipping_baseline_v1")

STATUSES = [
    "lost",
    "delayed",
    "in_transit",
    "delivered",
]


def main() -> None:
    world = generate_snapshot(seed=42)

    engine = create_database_engine()
    seed_database(engine, world)

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    for shipment_status in STATUSES:
        shipment = next(
            shipment
            for shipment in world.shipments
            if shipment.shipment_status.value == shipment_status
        )

        order_id = shipment.order_id

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
            "Investigate the order using Northstar's records "
            "and tell me what is actually happening. "
            "Do not assume the customer's claim is correct."
        )

        print("\n" + "=" * 70)
        print(f"ACTUAL STATUS: {shipment_status}")
        print(f"ORDER: {order_id}")
        print("=" * 70)

        result = runner.run(task)

        score = score_shipping_run(
            result,
            expected_order_id=order_id,
            expected_shipment_status=shipment_status,
        )

        record = {
            "model": "qwen3:4b-instruct",
            "seed": 42,
            "task": task,
            "order_id": order_id,
            "ground_truth": {
                "shipment_status": shipment_status,
                "customer_claim_lost": (shipment_status == "lost"),
            },
            "score": score,
            "final_answer": result.final_answer,
            "trace": result.model_dump(mode="json"),
            "manual_review": {
                "conclusion_correct": None,
                "internal_consistency": None,
                "unsupported_claims": None,
                "failure_types": [],
                "notes": None,
            },
        }

        output_path = OUTPUT_DIRECTORY / f"{shipment_status}.json"

        output_path.write_text(
            json.dumps(
                record,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(json.dumps(score, indent=2))
        print("\nFINAL ANSWER")
        print(result.final_answer)


if __name__ == "__main__":
    main()
