"""Compatibility script for the packaged ARL experiment runner."""

import sys

from agent_reliability_lab.cli import main
from agent_reliability_lab.experiments import run_benchmark

__all__ = ["run_benchmark"]

if __name__ == "__main__":
    main(["benchmark", *sys.argv[1:]])
