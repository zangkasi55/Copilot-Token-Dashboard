from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
from pathlib import Path

import requests

from .collect import collect_directory, collect_github, collect_m365, load_settings
from .demo import generate_demo
from .gold import build_from_folder, validate_tables
from .http import ApiError
from .imports import import_source
from .schema import TABLES, read_table


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="ctd", description="Tenant-owned AI usage reporting tools")
    commands = root.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Generate explicitly synthetic installation-test data")
    demo.add_argument("--output", type=Path, required=True)
    demo.add_argument("--scratch", type=Path, default=Path(".work/demo-inputs"))
    build = commands.add_parser("build-data", help="Build privacy-filtered reporting tables from customer metadata")
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--minimum-group-size", type=int, default=6)
    build.add_argument("--currency", default="USD")
    validate = commands.add_parser("validate-data", help="Validate a complete reporting-table folder")
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--production", action="store_true")
    source = commands.add_parser("import-source", help="Normalize approved metadata exports without retaining content")
    source.add_argument("--kind", choices=["gateway", "credits", "audit", "focus", "normalized"], required=True)
    source.add_argument("--input", type=Path, required=True)
    source.add_argument("--output", type=Path, required=True)
    source.add_argument("--scope", required=True)
    source.add_argument("--currency", default="USD")
    source.add_argument("--unit-price", type=float)
    source.add_argument("--service-filter", default="")
    for name in ("collect-github", "collect-m365", "collect-directory"):
        command = commands.add_parser(name)
        command.add_argument("--settings", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        if name == "collect-github":
            command.add_argument("--day", type=dt.date.fromisoformat, required=True)
            command.add_argument("--include-billing", action="store_true")
    return root


def main() -> int:
    arguments = parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if arguments.command == "demo":
            result = generate_demo(arguments.output, arguments.scratch)
        elif arguments.command == "build-data":
            result = build_from_folder(
                arguments.input, arguments.output, arguments.minimum_group_size, arguments.currency)
        elif arguments.command == "validate-data":
            tables = {name: read_table(arguments.input, name) for name in TABLES}
            minimum = int(tables["Settings"][0]["MinimumGroupSize"])
            validate_tables(tables, minimum, arguments.production)
            result = {"validated": True, "tables": len(tables), "production": arguments.production}
        elif arguments.command == "import-source":
            result = import_source(arguments.kind, arguments.input, arguments.output, arguments.scope,
                                   arguments.currency, arguments.unit_price, arguments.service_filter)
        else:
            settings = load_settings(arguments.settings)
            if arguments.command == "collect-github":
                result = collect_github(settings, arguments.day, arguments.output, arguments.include_billing)
            elif arguments.command == "collect-m365":
                result = collect_m365(settings, arguments.output)
            else:
                result = collect_directory(settings, arguments.output)
    except requests.RequestException:
        logging.error("Network request failed. Check connectivity and source configuration; credentials were not logged.")
        return 1
    except (ValueError, FileNotFoundError, ApiError, RuntimeError) as error:
        logging.error("%s", error)
        return 1
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
