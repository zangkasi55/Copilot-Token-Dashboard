from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from pypdf import PdfReader

TOKEN = re.compile(r"(?:gh[opusr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{30,}|sk-ant-[A-Za-z0-9_-]{24,})")
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b", re.I)
PRIVATE_PATH = re.compile(r"[A-Z]:\\Users\\(?!<|example|Public|Default)[^\\\r\n\"']+", re.I)
PRIVATE_APP = re.compile(r"https://[a-z0-9.-]+/groups/me/apps/[a-f0-9-]{30,}", re.I)
ROOT_FILES = {
    "README.md", "LICENSE", "Install.ps1", "pyproject.toml", "package.json",
    "package-lock.json", ".env.example", ".gitignore", ".gitattributes",
}
PUBLIC_DIRECTORIES = {"src", "tools", "tests", "config", "powerbi", "sample_data", "docs", ".github", ".vscode"}
TEXT_SUFFIXES = {".py", ".json", ".bim", ".pbip", ".pbir", ".pbism", ".tmdl", ".md",
                 ".txt", ".csv", ".ps1", ".yml", ".yaml", ".html", ".cjs", ".toml"}


def public_files(root: Path) -> list[Path]:
    result = []
    for file in sorted(root.rglob("*")):
        if not file.is_file():
            continue
        relative = file.relative_to(root)
        if relative.parts[0] not in PUBLIC_DIRECTORIES and relative.as_posix() not in ROOT_FILES:
            continue
        if any(part in {".pbi", "__pycache__", "node_modules", ".pytest_cache"} for part in relative.parts):
            continue
        if relative.parts[0] == "docs" and file.suffix == ".docx":
            continue
        if relative.parts[0] == "config" and file.name not in {"settings.example.json", "build-tools.json"}:
            continue
        result.append(file)
    return result


def check_text(text: str, label: str) -> list[str]:
    problems = []
    if TOKEN.search(text):
        problems.append(label + ": a credential-shaped token was found")
    if PRIVATE_PATH.search(text):
        problems.append(label + ": a machine-specific private user path was found")
    if any(domain.lower() != "example.com" for domain in EMAIL.findall(text)):
        problems.append(label + ": a non-synthetic email identity was found")
    if PRIVATE_APP.search(text):
        problems.append(label + ": a private personal-app reference was found")
    return problems


def check_bytes(data: bytes, label: str, depth: int = 0) -> list[str]:
    if data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return [label + ": protected/compound Office content is not eligible for publication"]
    problems = []
    if data.startswith(b"%PDF"):
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            return [label + ": encrypted PDF content is not eligible for publication"]
        for index, page in enumerate(reader.pages):
            problems.extend(check_text(page.extract_text() or "", label + f":page {index + 1}"))
        return problems
    if zipfile.is_zipfile(io.BytesIO(data)) and depth < 2:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 200_000_000:
                return [label + ": archive exceeds the public-artifact inspection limit"]
            for item in archive.infolist():
                if item.is_dir():
                    continue
                if ".." in Path(item.filename).parts or item.filename.startswith(("/", "\\")):
                    problems.append(label + ": unsafe archive member")
                content = archive.read(item)
                if item.filename.endswith((".xml", ".json", ".csv", ".txt", ".py", ".md", ".ps1")):
                    for encoding in ("utf-8-sig", "utf-16-le"):
                        try:
                            text = content.decode(encoding)
                        except UnicodeDecodeError:
                            continue
                        problems.extend(check_text(text, label + ":" + item.filename))
                        break
                elif item.filename in {"DataModelSchema", "Report/Layout", "Metadata", "Settings"}:
                    problems.extend(check_text(content.decode("utf-16-le"), label + ":" + item.filename))
                elif item.filename.endswith((".docx", ".zip", ".pbit")):
                    problems.extend(check_bytes(content, label + ":" + item.filename, depth + 1))
        return problems
    if Path(label).suffix in TEXT_SUFFIXES or Path(label).name in ROOT_FILES:
        text = data.decode("utf-8-sig")
        problems.extend(check_text(text, label))
        for encoded in re.findall(r'"([A-Za-z0-9+/=]{100,})"', text):
            try:
                decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                continue
            if "," in decoded and "\n" in decoded:
                problems.extend(check_text(decoded, label + ":embedded CSV"))
    return problems


def inspect(root: Path, extras: list[Path] | None = None) -> dict:
    files = public_files(root) + (extras or [])
    problems = []
    for file in files:
        problems.extend(check_bytes(file.read_bytes(), str(file.relative_to(root))))
    return {"files_inspected": len(files), "errors": len(problems), "problems": sorted(set(problems))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--artifact", type=Path, action="append", default=[])
    args = parser.parse_args()
    result = inspect(args.root.resolve(), [file.resolve() for file in args.artifact])
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["errors"] else 0)
