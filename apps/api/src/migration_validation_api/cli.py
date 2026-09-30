"""Console entry point: ``migration-workbench`` runs the local API server."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run Migration Validation Workbench")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    import uvicorn

    from migration_validation_api.server import app

    print(f"Migration Validation Workbench (FastAPI): http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
