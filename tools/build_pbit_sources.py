from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PRODUCT = "Copilot Token Dashboard"


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def convert_field(value: dict, aliases: dict[str, str]) -> dict:
    result = json.loads(json.dumps(value))
    definition = result["Measure" if "Measure" in result else "Column"]
    entity = definition["Expression"]["SourceRef"]["Entity"]
    definition["Expression"]["SourceRef"] = {"Source": aliases[entity]}
    return result


def build(project: Path, model_source: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("Use a new compiler source directory; existing files will not be deleted")
    output.mkdir(parents=True)
    (output / "Version.txt").write_text("1.28", encoding="utf-8")
    write(output / "ReportMetadata.json", {"version": 4})
    write(output / "ReportSettings.json", {"isPersistentUserStateDisabled": False})
    shutil.copytree(model_source, output / "Model")
    manifest = json.loads((project / "build-manifest.json").read_text(encoding="utf-8"))
    report = project / (PRODUCT + ".Report")
    report_definition = json.loads((report / "definition" / "report.json").read_text(encoding="utf-8"))
    package_types = {"RegisteredResources": 1, "SharedResources": 2}
    item_types = {"Image": 100, "ShapeMap": 200, "CustomTheme": 201, "BaseTheme": 202}
    themes = {}
    for name, theme in report_definition["themeCollection"].items():
        if theme["type"] not in package_types:
            raise ValueError("The compiler source contains an unsupported theme package type")
        themes[name] = {**theme, "type": package_types[theme["type"]]}
    resource_packages = []
    for package in report_definition.get("resourcePackages", []):
        if package["type"] not in package_types or any(item["type"] not in item_types for item in package["items"]):
            raise ValueError("The compiler source contains an unsupported resource package")
        resource_packages.append({"resourcePackage": {
            **package, "type": package_types[package["type"]],
            "items": [{**item, "type": item_types[item["type"]]} for item in package["items"]],
        }})
    if (report / "StaticResources").is_dir():
        shutil.copytree(report / "StaticResources", output / "StaticResources")
    sections = []
    for ordinal, page in enumerate(manifest["pages"]):
        containers = []
        for visual in page["visuals"]:
            source = json.loads((report / "definition" / "pages" / page["name"] / "visuals" / visual["id"] / "visual.json").read_text(encoding="utf-8"))
            query_state = source["visual"].get("query", {}).get("queryState", {})
            entities = []
            for state in query_state.values():
                for projection in state["projections"]:
                    definition = projection["field"]
                    entity = definition["Measure" if "Measure" in definition else "Column"]["Expression"]["SourceRef"]["Entity"]
                    if entity not in entities:
                        entities.append(entity)
            aliases = {entity: "s" + str(index) for index, entity in enumerate(entities)}
            selections, projections = [], {}
            for role, state in query_state.items():
                projections[role] = []
                for projection in state["projections"]:
                    field = convert_field(projection["field"], aliases)
                    reference = projection["queryRef"]
                    field["Name"] = reference
                    selections.append(field)
                    projections[role].append({"queryRef": reference})
            prototype = {
                "Version": 2,
                "From": [{"Name": aliases[entity], "Entity": entity, "Type": 0} for entity in entities],
                "Select": selections,
            }
            position = source["position"]
            single_visual = {
                "visualType": source["visual"]["visualType"],
                "vcObjects": source["visual"]["visualContainerObjects"],
                "objects": source["visual"].get("objects", {}),
                "drillFilterOtherVisuals": True,
            }
            if selections:
                single_visual.update({"projections": projections, "prototypeQuery": prototype})
            config = {
                "name": visual["id"],
                "layouts": [{"id": 0, "position": position}],
                "singleVisual": single_visual,
            }
            binding = {
                "Primary": {"Groupings": [{"Projections": list(range(len(selections)))}]},
                "DataReduction": {"DataVolume": 3, "Primary": {"Top": {"Count": 1000}}},
                "Version": 1,
            }
            query = {"Commands": [{"SemanticQueryDataShapeCommand": {
                "Query": prototype, "Binding": binding, "ExecutionMetricsKind": 1,
            }}]}
            container = {
                "x": position["x"], "y": position["y"], "z": position["z"],
                "width": position["width"], "height": position["height"],
                "config": json.dumps(config), "filters": "[]",
            }
            if selections:
                container["query"] = json.dumps(query)
            containers.append(container)
        page_definition = json.loads((report / "definition" / "pages" / page["name"] / "page.json").read_text(encoding="utf-8"))
        sections.append({
            "name": page["name"], "displayName": page["title"], "ordinal": ordinal,
            "width": page_definition["width"], "height": page_definition["height"],
            "displayOption": 1 if page_definition["height"] > 1000 else 0,
            "visualContainers": containers, "filters": "[]",
            "config": json.dumps({"objects": page_definition.get("objects", {})}),
        })
    layout = {
        "id": 0, "reportId": "public-template", "sections": sections,
        "config": json.dumps({
            "version": "5.57", "activeSectionIndex": 0,
            "defaultDrillFilterOtherVisuals": True,
            "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": 1},
            "themeCollection": themes,
        }),
        "filters": "[]",
        "resourcePackages": resource_packages,
    }
    write(output / "Report" / "report.json", layout)
    write(output / ".pbixproj.json", {
        "version": "0.15",
        "settings": {"serialization": {"model": {"serializationMode": "Tmdl"}}},
    })
    return {"compiler_source": str(output), "pages": len(sections),
            "visuals": sum(len(page["visualContainers"]) for page in sections)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path("powerbi"))
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(build(options.project, options.model, options.output), indent=2))
