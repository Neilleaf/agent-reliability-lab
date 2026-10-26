"""Compatibility script for the packaged ARL experiment runner."""

import sys

from agent_reliability_lab.cli import main
from agent_reliability_lab.experiments import run_security

__all__ = ["run_security"]

if __name__ == "__main__":
    main(["security", *sys.argv[1:]])
