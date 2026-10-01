"""Console entry point: ``migration-workbench`` runs the local API server."""

from __future__ import annotations

import argparse

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run Migration Validation Workbench")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="bind a non-loopback --host; the API has no authentication, so anyone who can reach it can upload data",
    )
    args = parser.parse_args(argv)
    if args.host not in LOOPBACK_HOSTS and not args.allow_remote:
        # The workbench has no access control (deploy/README.md): uploads and
        # reconciliation results must stay on this machine unless the operator
        # opts in explicitly.
        parser.error(f"--host {args.host} is not loopback; the API is unauthenticated (pass --allow-remote to bind it)")

    import uvicorn

    from migration_validation_api.server import app

    print(f"Migration Validation Workbench (FastAPI): http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
