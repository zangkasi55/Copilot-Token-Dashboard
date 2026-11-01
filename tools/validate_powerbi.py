from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import jsonschema
import requests
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

THEME_SCHEMA_URL = (
    "https://raw.githubusercontent.com/microsoft/powerbi-desktop-samples/main/"
    "Report%20Theme%20JSON%20Schema/reportThemeSchema-2.159.json"
)


def validate_scbx_theme(folder: Path, cache: Path) -> list[str]:
    theme_path = folder / "SCBX_Theme.json"
    if not theme_path.is_file():
        return ["The SCBX branch requires its supplied SCBX_Theme.json"]
    cache.mkdir(parents=True, exist_ok=True)
    schema_path = cache / "reportThemeSchema-2.159.json"
    if not schema_path.is_file():
        response = requests.get(THEME_SCHEMA_URL, timeout=(15, 45))
        response.raise_for_status()
        schema_path.write_bytes(response.content)
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    problems = [
        "SCBX theme: " + "/".join(map(str, error.path)) + ": " + error.message
        for error in jsonschema.Draft7Validator(schema).iter_errors(theme)
    ]
    reports = list(folder.glob("*.Report"))
    if len(reports) != 1:
        problems.append("The SCBX theme must bind to exactly one report")
    else:
        embedded = reports[0] / "StaticResources" / "RegisteredResources" / theme_path.name
        if not embedded.is_file() or embedded.read_bytes() != theme_path.read_bytes():
            problems.append("The report's registered SCBX theme must match the canonical theme file")
    return problems


def schema_loader(cache: Path):
    cache.mkdir(parents=True, exist_ok=True)
    loaded = {}

    def load(uri: str):
        if uri in loaded:
            return loaded[uri]
        parsed = urlparse(uri)
        if parsed.scheme != "https" or parsed.hostname != "developer.microsoft.com":
            raise ValueError("Only official Microsoft schema URLs may be retrieved")
        file = cache / (hashlib.sha256(uri.encode()).hexdigest() + ".json")
        if not file.is_file():
            response = requests.get(uri, timeout=(15, 45))
            response.raise_for_status()
            file.write_bytes(response.content)
        value = json.loads(file.read_text(encoding="utf-8"))
        loaded[uri] = value
        if value.get("$id"):
            loaded[urljoin(uri, value["$id"])] = value
        return value

    return load


def validate(folder: Path, cache: Path) -> dict:
    load = schema_loader(cache)
    problems, validated = validate_scbx_theme(folder, cache), 0
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or ".pbi" in path.parts:
            continue
        if path.suffix not in {".json", ".pbip", ".pbir", ".pbism"}:
            continue
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        uri = value.get("$schema")
        if not uri:
            continue
        schema = load(uri)
        registry = Registry(
            retrieve=lambda reference: Resource.from_contents(
                load(reference), default_specification=DRAFT7)
        ).with_resource(uri, Resource.from_contents(schema, default_specification=DRAFT7))
        validator = jsonschema.validators.validator_for(schema)(schema, registry=registry)
        errors = list(validator.iter_errors(value))
        for error in errors[:5]:
            problems.append(f"{path.relative_to(folder)}: {'/'.join(map(str, error.path))}: {error.message}")
        validated += 1
    models = list(folder.glob("*.SemanticModel/model.bim"))
    if len(models) != 1:
        problems.append("The package must contain exactly one semantic model")
    else:
        model = json.loads(models[0].read_text(encoding="utf-8"))["model"]
        table_names = [table["name"] for table in model["tables"]]
        if len(table_names) != len(set(table_names)):
            problems.append("Semantic model table names are duplicated")
        columns = {table["name"]: {column["name"] for column in table["columns"]}
                   for table in model["tables"]}
        measures = {table["name"]: {measure["name"] for measure in table.get("measures", [])}
                    for table in model["tables"]}
        for relationship in model["relationships"]:
            for prefix in ("from", "to"):
                if relationship[prefix + "Column"] not in columns.get(relationship[prefix + "Table"], set()):
                    problems.append("A relationship references an unknown column")
        roles = model.get("roles", [])
        if [role["name"] for role in roles] != ["Viewer"]:
            problems.append("The package must contain its explicit Viewer role")
        else:
            permissions = {permission["name"]: permission["filterExpression"]
                           for permission in roles[0]["tablePermissions"]}
            for name in ("People", "Accounts", "ScopeAccess", "Scopes"):
                if "USERPRINCIPALNAME()" not in permissions.get(name, ""):
                    problems.append(f"Viewer RLS is missing dynamic identity protection for {name}")
            for name in ("ScopeDaily", "ScopeWeekly", "ScopePeriod", "AgentPeriod"):
                if permissions.get(name) != "[PrivacySuppressed]=FALSE()":
                    problems.append(f"Viewer RLS is missing aggregate suppression for {name}")
        visuals = list(folder.glob("*.Report/definition/pages/*/visuals/*/visual.json"))
        for path in visuals:
            visual = json.loads(path.read_text(encoding="utf-8"))
            page = json.loads((path.parents[2] / "page.json").read_text(encoding="utf-8"))
            position = visual["position"]
            if position["x"] < 0 or position["y"] < 0 or position["x"] + position["width"] > page["width"]:
                problems.append(f"{path.name}: visual position exceeds its page")
            if position["y"] + position["height"] > page["height"]:
                problems.append(f"{path.name}: visual height exceeds its page")
            roles = visual.get("visual", {}).get("query", {}).get("queryState", {})
            for role in roles.values():
                for projection in role["projections"]:
                    definition = projection["field"]
                    kind = "Measure" if "Measure" in definition else "Column"
                    entity = definition[kind]["Expression"]["SourceRef"]["Entity"]
                    property_name = definition[kind]["Property"]
                    dictionary = measures if kind == "Measure" else columns
                    if property_name not in dictionary.get(entity, set()):
                        problems.append(f"{path}: unknown {kind.lower()} reference {entity}.{property_name}")
        pages = list(folder.glob("*.Report/definition/pages/*/page.json"))
        if len(pages) != 10:
            problems.append("The release must contain all ten report pages")
    result = {"schema_files_validated": validated, "theme_schema": "Microsoft 2.159",
              "errors": len(problems), "problems": problems}
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path("powerbi"))
    parser.add_argument("--cache", type=Path, default=Path(".work/schema-cache"))
    arguments = parser.parse_args()
    result = validate(arguments.project, arguments.cache)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["errors"] else 0)
