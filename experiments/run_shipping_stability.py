"""Compatibility script for the packaged ARL experiment runner."""

import sys

from agent_reliability_lab.cli import main
from agent_reliability_lab.experiments import run_stability

__all__ = ["run_stability"]

if __name__ == "__main__":
    main(["stability", *sys.argv[1:]])
