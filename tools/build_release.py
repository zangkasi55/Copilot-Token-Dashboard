from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from pypdf import PdfReader
from copilot_token_dashboard import __version__

from publication_check import inspect, public_files

VERSION = __version__
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
            reader = PdfReader(path)
            if reader.is_encrypted or sum(len(page.images) for page in reader.pages) != 10:
                raise ValueError("Each public installation PDF must contain all ten unencrypted screenshot figures")
    sample = root / "docs" / "assets" / "sample-dashboard.html"
    if not sample.is_file():
        raise FileNotFoundError("Build the synthetic dashboard companion before packaging the illustrated manuals")
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
    manual_assets = []
    for suffix in ("EN", "TH"):
        source = root / "docs" / "manuals" / f"Copilot Token Dashboard - Installation {suffix}.pdf"
        target = destination / f"Copilot-Token-Dashboard-Installation-{suffix}.pdf"
        shutil.copyfile(source, target)
        manual_assets.append(target)
    sample_asset = destination / "Copilot-Token-Dashboard-Sample.html"
    shutil.copyfile(sample, sample_asset)
    artifacts = [archive_path, template] + manual_assets + [sample_asset]
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
        "documentation_revision": "thai-installation-retested-1",
        "manual_figures_per_language": 10,
        "sample_dashboard": sample_asset.name,
        "screenshot_provenance": "Synthetic browser illustrations, not verified Power BI screenshots",
    }
    (destination / "release-manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(build(args.root.resolve()), indent=2))
