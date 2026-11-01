import argparse
import json
import logging
from pathlib import Path

from copilot_token_dashboard.deploy import PRODUCT, configured_model, source_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and configure a local tenant-owned Power BI project")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--mode", choices=["Demo", "CSV", "SharePoint"], required=True)
    parser.add_argument("--data-folder", type=Path)
    parser.add_argument("--sharepoint-site", default="")
    parser.add_argument("--sharepoint-folder", default="")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        source_settings(args.mode, args.data_folder, args.sharepoint_site, args.sharepoint_folder)
        if not args.validate_only:
            model = configured_model(args.project, args.mode, args.data_folder,
                                     args.sharepoint_site, args.sharepoint_folder)
            path = args.project / (PRODUCT + ".SemanticModel") / "model.bim"
            path.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (ValueError, FileNotFoundError) as error:
        logging.error("%s", error)
        return 1
    print(json.dumps({"source_mode": args.mode, "source_validated": True,
                      "model_updated": not args.validate_only}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
