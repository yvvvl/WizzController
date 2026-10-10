"""Keep installer requirements aligned with the package metadata."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = ("requirements.txt", "requirements-qt-linux.txt", "requirements-qt-macos.txt")
NAME_AND_SPEC = re.compile(r"^([A-Za-z0-9_.-]+)(.*)$")


def _dependencies(lines):
    result = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = line.split(";", 1)[0].strip()
        match = NAME_AND_SPEC.fullmatch(requirement)
        assert match is not None, f"Unsupported requirement: {line}"
        name = match.group(1).lower().replace("_", "-")
        result[name] = match.group(2).replace(" ", "")
    return result


def test_runtime_requirement_versions_match_project_metadata():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = _dependencies(project["project"]["dependencies"])
    for filename in RUNTIME_FILES:
        listed = _dependencies((ROOT / filename).read_text(encoding="utf-8").splitlines())
        assert listed.items() <= declared.items(), f"{filename} drifted from pyproject.toml"
