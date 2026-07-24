from __future__ import annotations

"""Read-only audit of the pywizlight dependency and packaged runtime."""

import argparse
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
import zipfile

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _iter_source_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() not in {".py", ".toml", ".txt", ".md", ".ps1", ".yml", ".yaml"}:
            continue
        yield path


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _find_mentions(root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    pattern = re.compile(r"pywizlight|rgb2rgbcw|rgbcw2hs|get_bulbtype", re.I)
    for path in _iter_source_files(root):
        text = _read(path)
        for number, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                results.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "line": number,
                        "text": line.strip(),
                    }
                )
    return results


def _pins(root: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for name in ("requirements.txt", "pyproject.toml"):
        path = root / name
        matches = [
            line.strip()
            for line in _read(path).splitlines()
            if "pywizlight" in line.lower()
        ]
        result[name] = matches
    return result


def _installed_distribution() -> dict[str, Any]:
    try:
        dist = importlib.metadata.distribution("pywizlight")
    except importlib.metadata.PackageNotFoundError:
        return {"installed": False}

    files = list(dist.files or [])
    root = Path(dist.locate_file("")).resolve()
    total_size = 0
    license_files: list[str] = []
    for entry in files:
        candidate = Path(dist.locate_file(entry))
        try:
            if candidate.is_file():
                total_size += candidate.stat().st_size
        except OSError:
            pass
        lower = str(entry).lower()
        if "license" in lower or "copying" in lower:
            license_files.append(str(candidate))

    return {
        "installed": True,
        "version": dist.version,
        "root": str(root),
        "installed_bytes": total_size,
        "license_files": sorted(set(license_files)),
    }


def _project_license(root: Path) -> dict[str, Any]:
    names = (
        "LICENSE",
        "LICENSE.txt",
        "LICENSE.md",
        "LICENSE.rst",
        "LICENCE",
        "COPYING",
    )
    found = [name for name in names if (root / name).is_file()]
    return {"present": bool(found), "files": found}


def _package_evidence(root: Path) -> dict[str, Any]:
    dist_root = root / "dist" / "windows"
    evidence: dict[str, Any] = {
        "dist_windows_present": dist_root.is_dir(),
        "directories": [],
        "app_zips": [],
    }
    if not dist_root.is_dir():
        return evidence

    for path in dist_root.rglob("pywizlight"):
        if path.is_dir():
            evidence["directories"].append(str(path.relative_to(root)))

    for app_zip in dist_root.rglob("app.zip"):
        record: dict[str, Any] = {
            "path": str(app_zip.relative_to(root)),
            "contains_pywizlight": False,
            "sample_entries": [],
        }
        try:
            with zipfile.ZipFile(app_zip) as archive:
                matches = [
                    name
                    for name in archive.namelist()
                    if "pywizlight/" in name.replace("\\", "/").lower()
                ]
            record["contains_pywizlight"] = bool(matches)
            record["sample_entries"] = matches[:12]
        except (OSError, zipfile.BadZipFile) as exc:
            record["error"] = str(exc)
        evidence["app_zips"].append(record)

    return evidence


def _classification(root: Path, mentions: list[dict[str, Any]]) -> dict[str, Any]:
    direct_color_import = any(
        item["path"] == "core/wiz_color.py"
        and re.search(r"^\s*(from|import)\s+pywizlight", item["text"])
        for item in mentions
    )
    ui_imports = [
        item
        for item in mentions
        if item["path"].startswith("ui/")
        and re.search(r"^\s*(from|import)\s+pywizlight", item["text"])
    ]
    pinned = any(_pins(root).values())
    required = bool(direct_color_import or pinned)
    return {
        "runtime_required_in_current_tree": required,
        "reason": (
            "Direct color-pipeline import and dependency pin"
            if direct_color_import and pinned
            else "Direct import"
            if direct_color_import
            else "Dependency pin"
            if pinned
            else "No direct evidence"
        ),
        "direct_color_import": direct_color_import,
        "ui_imports": ui_imports,
    }


def build_report(root: Path) -> dict[str, Any]:
    mentions = _find_mentions(root)
    return {
        "schema": 1,
        "repository": {
            "root": str(root),
            "branch": _git(root, "branch", "--show-current"),
            "head": _git(root, "rev-parse", "HEAD"),
            "status": _git(root, "status", "--short").splitlines(),
        },
        "pins": _pins(root),
        "installed_distribution": _installed_distribution(),
        "mentions": mentions,
        "classification": _classification(root, mentions),
        "project_license": _project_license(root),
        "packaged_runtime": _package_evidence(root),
        "notes": [
            "This tool performs no WiZ network requests.",
            "A missing dist/windows directory means packaging has not been audited yet.",
            "No project license is created automatically.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    if not (root / "main.py").is_file():
        parser.error(f"Not a WizZ Desktop repository root: {root}")

    report = build_report(root)
    encoded = json.dumps(report, indent=2, ensure_ascii=False)

    if args.write:
        output = args.write
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
        print(f"Written: {output}")
    else:
        print(encoded)

    classification = report["classification"]
    print(
        "Classification:",
        "required" if classification["runtime_required_in_current_tree"] else "undetermined",
    )
    print(
        "Project license:",
        "present" if report["project_license"]["present"] else "MISSING",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
