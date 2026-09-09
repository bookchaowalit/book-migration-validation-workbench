#!/usr/bin/env python3
"""Run the local Migration Validation Workbench server."""

from pathlib import Path
import sys
import argparse


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "reconciliation-core" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "data-engine" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "connectors" / "file-input" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "privacy" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "audit" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api" / "src"))

def main() -> None:
    parser = argparse.ArgumentParser(description="Run Migration Validation Workbench")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    import uvicorn
    from migration_validation_api.server import app

    print(f"Migration Validation Workbench (FastAPI): http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
