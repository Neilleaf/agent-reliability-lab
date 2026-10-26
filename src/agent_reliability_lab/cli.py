"""Small standard-library CLI for local ARL experiments and saved reports."""

import argparse
from pathlib import Path

from agent_reliability_lab.experiments import DEFAULT_MODEL, run_experiment


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="arl",
        description="Agent Reliability Lab: synthetic evidence and tool-use benchmarks",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for suite in ("benchmark", "security", "stability"):
        command = subparsers.add_parser(
            suite, help=f"Run the {suite} experiment through local Ollama"
        )
        command.add_argument("--model", default=DEFAULT_MODEL)
        command.add_argument("--output-dir", type=Path)
    summary = subparsers.add_parser(
        "summary", help="Report saved results without calling a model"
    )
    summary.add_argument(
        "--results-root", type=Path, default=Path("experiments/results")
    )
    summary.add_argument(
        "--reviews-root", type=Path, default=Path("experiments/reviews")
    )
    summary.add_argument("--json", type=Path, dest="json_path")
    subparsers.add_parser(
        "world-summary", help="Generate and summarize seed 42 without database writes"
    )
    subparsers.add_parser("seed", help="Seed the local synthetic SQLite database")
    args = parser.parse_args(argv)
    if args.command in ("benchmark", "security", "stability"):
        try:
            run_experiment(args.command, args.output_dir, model=args.model)
        except FileExistsError as exc:
            parser.error(str(exc))
    elif args.command == "summary":
        from agent_reliability_lab.report import (
            collect_reports,
            export_report,
            print_report,
        )

        reports = collect_reports(args.results_root, args.reviews_root)
        print_report(reports)
        if args.json_path:
            try:
                export_report(args.json_path, reports)
            except OSError as exc:
                parser.error(f"Cannot create JSON report: {exc}")
    elif args.command == "seed":
        from agent_reliability_lab.storage.seeder import main as seed

        seed()
    else:
        from agent_reliability_lab.synthetic.generator import generate_snapshot
        from agent_reliability_lab.synthetic.summary import print_snapshot_summary

        world = generate_snapshot(seed=42)
        print("Northstar synthetic world - seed 42")
        print_snapshot_summary(world)


if __name__ == "__main__":
    main()
