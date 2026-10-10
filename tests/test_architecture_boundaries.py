"""Prevent application services from depending on a specific desktop UI."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PACKAGES = ("core", "config", "localization")
UI_PACKAGES = {"qt_ui", "PySide6", "flet"}


def test_services_do_not_import_desktop_ui():
    violations = []
    for package in SERVICE_PACKAGES:
        for path in (ROOT / package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = (alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    modules = (node.module,)
                else:
                    continue
                for module in modules:
                    if module.split(".", 1)[0] in UI_PACKAGES:
                        violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: {module}")
    assert not violations, "Service-to-UI imports:\n" + "\n".join(violations)
