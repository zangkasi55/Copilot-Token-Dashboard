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
    sections = []
    for ordinal, page in enumerate(manifest["pages"]):
        containers = []
        for visual in page["visuals"]:
            source = json.loads((report / "definition" / "pages" / page["name"] / "visuals" / visual["id"] / "visual.json").read_text(encoding="utf-8"))
            query_state = source["visual"]["query"]["queryState"]
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
            config = {
                "name": visual["id"],
                "layouts": [{"id": 0, "position": position}],
                "singleVisual": {
                    "visualType": source["visual"]["visualType"],
                    "projections": projections, "prototypeQuery": prototype,
                    "vcObjects": source["visual"]["visualContainerObjects"],
                    "objects": source["visual"].get("objects", {}),
                    "drillFilterOtherVisuals": True,
                },
            }
            binding = {
                "Primary": {"Groupings": [{"Projections": list(range(len(selections)))}]},
                "DataReduction": {"DataVolume": 3, "Primary": {"Top": {"Count": 1000}}},
                "Version": 1,
            }
            query = {"Commands": [{"SemanticQueryDataShapeCommand": {
                "Query": prototype, "Binding": binding, "ExecutionMetricsKind": 1,
            }}]}
            containers.append({
                "x": position["x"], "y": position["y"], "z": position["z"],
                "width": position["width"], "height": position["height"],
                "config": json.dumps(config), "query": json.dumps(query), "filters": "[]",
            })
        page_definition = json.loads((report / "definition" / "pages" / page["name"] / "page.json").read_text(encoding="utf-8"))
        sections.append({
            "name": page["name"], "displayName": page["title"], "ordinal": ordinal,
            "width": page_definition["width"], "height": page_definition["height"],
            "displayOption": 1 if page_definition["height"] > 1000 else 0,
            "visualContainers": containers, "filters": "[]", "config": "{}",
        })
    layout = {
        "id": 0, "reportId": "public-template", "sections": sections,
        "config": json.dumps({
            "version": "5.57", "activeSectionIndex": 0,
            "defaultDrillFilterOtherVisuals": True,
            "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": 1},
            "themeCollection": {
                "baseTheme": {"name": "CY24SU10", "type": 2,
                              "reportVersionAtImport": {"visual": "2.4.0", "page": "2.0.0", "report": "3.0.0"}},
            },
        }),
        "filters": "[]",
        "resourcePackages": [],
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
