"""Launch FastAPI against the isolated Golden Demo environment only.

This is an operator entry point, not a replacement runtime. It loads the
ignored ``demo/.env``, validates that all persistence stays under ``demo/``,
then imports the ordinary application and starts it without reload workers.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.demo_environment import DemoEnvironmentError, apply_demo_environment, isolated_demo_environment


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ResearchOS against the isolated Golden Demo environment")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    try:
        environment = isolated_demo_environment()
    except DemoEnvironmentError as error:
        print(f"DEMO SERVER BLOCKED: {error}", file=sys.stderr)
        return 2
    if os.getenv("DEMO_MODE", "").strip().lower() != "true":
        print("DEMO SERVER BLOCKED: DEMO_MODE=true is required", file=sys.stderr)
        return 2
    if not os.getenv("DEMO_OWNER_PASSWORD") or not os.getenv("DEMO_REVIEWER_PASSWORD"):
        print("DEMO SERVER BLOCKED: Demo Owner and Demo Reviewer passwords are required", file=sys.stderr)
        return 2

    apply_demo_environment(environment)
    try:
        import uvicorn
        from app.main import app
    except RuntimeError as error:
        print(f"DEMO SERVER BLOCKED: {error}", file=sys.stderr)
        return 2
    print(f"ResearchOS Demo API: http://{args.host}:{args.port}")
    print(f"Demo database: {environment.database_path}")
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
