"""Compatibility command for a guarded Golden Demo reset.

All destructive work is delegated to ``bootstrap_golden_demo.py``. That
script selects ``RESEARCHOS_DATABASE_URL_DEMO`` before importing application
services, backs up only ``demo/`` data, and refuses any target outside it.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.bootstrap_golden_demo import bootstrap


CONFIRMATION = "RESET_RESEARCHOS_DEMO_DATA"


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset only the isolated ResearchOS Golden Demo environment")
    parser.add_argument("--apply", action="store_true", help="back up and rebuild only the configured demo/ environment")
    args = parser.parse_args()
    if args.apply and os.getenv("RESEARCHOS_DEMO_RESET_CONFIRM", "").strip() != CONFIRMATION:
        print(f"DEMO RESET BLOCKED: RESEARCHOS_DEMO_RESET_CONFIRM must equal {CONFIRMATION}", file=sys.stderr)
        return 1
    try:
        return bootstrap(args.apply)
    except Exception as error:
        print(f"DEMO RESET BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
