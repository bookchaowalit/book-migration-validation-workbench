#!/usr/bin/env python3
"""Run the local Migration Validation Workbench server.

Install the project first (``pip install -e .``); this is the same as the
``migration-workbench`` console script.
"""

import sys

try:
    from migration_validation_api.cli import main
except ModuleNotFoundError as exc:  # pragma: no cover - guidance only
    sys.exit(f"{exc}. Install the workbench first: python3 -m pip install -e .")


if __name__ == "__main__":
    main()
