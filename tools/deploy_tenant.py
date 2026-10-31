import argparse
import json
from pathlib import Path

from copilot_token_dashboard.deploy import deploy

parser = argparse.ArgumentParser(description="Provision this package in your own Power BI/Fabric workspace")
parser.add_argument("--project", type=Path, required=True)
parser.add_argument("--tenant", required=True)
parser.add_argument("--workspace", required=True)
parser.add_argument("--mode", choices=["Demo", "CSV", "SharePoint"], default="Demo")
parser.add_argument("--data-folder", type=Path)
parser.add_argument("--sharepoint-site", default="")
parser.add_argument("--sharepoint-folder", default="")
parser.add_argument("--update", action="store_true")
parser.add_argument("--output", type=Path, default=Path("runtime/deployment.json"))
arguments = parser.parse_args()
print(json.dumps(deploy(
    arguments.project, arguments.tenant, arguments.workspace, arguments.mode,
    arguments.data_folder, arguments.sharepoint_site, arguments.sharepoint_folder,
    arguments.update, arguments.output,
), indent=2))

