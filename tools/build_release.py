from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from publication_check import inspect, public_files

VERSION = "1.0.0"
PREFIX = "Copilot-Token-Dashboard-" + VERSION


def verify_template(template: Path) -> dict:
    if not template.is_file():
        raise FileNotFoundError("Compile the model-containing Power BI template before building a release")
    with zipfile.ZipFile(template) as archive:
        required = {"Version", "Metadata", "Settings", "Report/Layout", "DataModelSchema"}
        if not required.issubset(archive.namelist()):
            raise ValueError("The template is missing required Power BI package parts")
        layout = json.loads(archive.read("Report/Layout").decode("utf-16-le"))
        model = json.loads(archive.read("DataModelSchema").decode("utf-16-le"))
        pages = len(layout["sections"])
        visuals = sum(len(page["visualContainers"]) for page in layout["sections"])
        measures = sum(len(table.get("measures", [])) for table in model["model"]["tables"])
        if pages != 10 or visuals < 100 or measures < 80:
            raise ValueError("The compiled template does not contain the complete report/model")
        return {"pages": pages, "visuals": visuals, "tables": len(model["model"]["tables"]), "measures": measures}


def build(root: Path) -> dict:
    destination = root / "dist"
    destination.mkdir(exist_ok=True)
    template = destination / (PREFIX + ".pbit")
    template_info = verify_template(template)
    for suffix in ("EN", "TH"):
        for extension in ("pdf",):
            path = root / "docs" / "manuals" / f"Copilot Token Dashboard - Installation {suffix}.{extension}"
            if not path.is_file():
                raise FileNotFoundError("Both public installation manuals must be built and validated")
    checked = inspect(root, [template])
    if checked["errors"]:
        raise ValueError("Public-safety validation failed: " + json.dumps(checked["problems"]))
    archive_path = destination / (PREFIX + "-Install.zip")
    files = public_files(root)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in files:
            name = file.relative_to(root).as_posix()
            archive.write(file, name)
        archive.write(template, template.name)
    archive_check = inspect(root, [archive_path])
    if archive_check["errors"]:
        raise ValueError("The release archive failed public-safety validation")
    artifacts = [archive_path, template] + [
        root / "docs" / "manuals" / f"Copilot Token Dashboard - Installation {suffix}.{extension}"
        for suffix in ("EN", "TH") for extension in ("pdf",)
    ]
    checksums = []
    for file in artifacts:
        checksums.append(hashlib.sha256(file.read_bytes()).hexdigest() + "  " + file.name)
    (destination / (PREFIX + "-SHA256SUMS.txt")).write_text("\n".join(checksums) + "\n", encoding="utf-8")
    result = {
        "version": VERSION, "installation_zip": archive_path.name,
        "channel": "public-preview",
        "template": template.name, "template_verified": template_info,
        "source_files": len(files), "public_safety_errors": 0,
        "manual_languages": ["English", "Thai"],
    }
    (destination / "release-manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(build(args.root.resolve()), indent=2))
