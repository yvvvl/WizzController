from __future__ import annotations

import argparse
import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from localization.catalogs import CATALOGS
from localization.manager import format_fields

SCAN_PATHS = (
    ROOT / "main.py",
    ROOT / "ui",
    ROOT / "core" / "background",
)
TEXT_CALLS = {
    "Text",
    "TextButton",
    "ElevatedButton",
    "OutlinedButton",
    "DropdownOption",
}
USER_TEXT_KEYWORDS = {
    "label",
    "hint_text",
    "tooltip",
    "message",
    "title",
    "subtitle",
}


def catalog_errors() -> list[str]:
    errors: list[str] = []
    languages = sorted(CATALOGS)
    baseline_language = languages[0]
    baseline = CATALOGS[baseline_language]
    baseline_keys = set(baseline)

    for language in languages[1:]:
        catalog = CATALOGS[language]
        missing = sorted(baseline_keys - set(catalog))
        extra = sorted(set(catalog) - baseline_keys)
        if missing:
            errors.append(f"{language}: missing keys: {', '.join(missing)}")
        if extra:
            errors.append(f"{language}: extra keys: {', '.join(extra)}")
        for key in sorted(baseline_keys & set(catalog)):
            if format_fields(baseline[key]) != format_fields(catalog[key]):
                errors.append(f"{language}: placeholder mismatch: {key}")
    return errors


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for path in SCAN_PATHS:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return files


def call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def literal_text(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.strip()
    if isinstance(node, ast.JoinedStr):
        return "<f-string>"
    return None


def hardcoded_ui_strings() -> list[str]:
    findings: list[str] = []
    for path in iter_python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = call_name(node)
            candidates: list[ast.AST] = []
            if name in TEXT_CALLS and node.args:
                candidates.append(node.args[0])
            for keyword in node.keywords:
                if keyword.arg in USER_TEXT_KEYWORDS:
                    candidates.append(keyword.value)
            for candidate in candidates:
                value = literal_text(candidate)
                if not value or value.startswith(("#", "http", "WizZ")):
                    continue
                relative = path.relative_to(ROOT)
                findings.append(f"{relative}:{getattr(node, 'lineno', '?')}: {value}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit WizZ Desktop translations")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return a failure code when hardcoded UI strings remain",
    )
    args = parser.parse_args()

    errors = catalog_errors()
    if errors:
        print("Catalog errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    findings = hardcoded_ui_strings()
    print(f"Catalogs OK: {len(CATALOGS['en'])} keys · en/es")
    print(f"Potential hardcoded UI strings: {len(findings)}")
    for finding in findings:
        print(f"  {finding}")

    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
