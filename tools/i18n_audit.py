from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from localization.catalogs import CATALOGS
from localization.manager import format_fields

SCAN_PATHS = (
    ROOT / "qt_ui",
)
QML_DIR = ROOT / "qt_ui" / "qml"
VISIBLE_QML_PROPERTIES = re.compile(
    r"\b(?P<property>text|title|subtitle|label|description|placeholderText|"
    r"toolTipText|Accessible\.name|Accessible\.description)\s*:\s*"
    r"(?P<literal>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"
)
QML_TRANSLATION_CALL = re.compile(r"\broot\.t\s*\(")
QML_TRANSLATION_PAIR = re.compile(
    r'\broot\.t\s*\(\s*(?P<spanish>"(?:\\.|[^"\\])*")\s*,\s*'
    r'(?P<english>"(?:\\.|[^"\\])*")\s*\)',
    re.DOTALL,
)
# Product names, technical labels and the shared navigation word "Color" are
# intentionally identical in both languages. Keep this list small.
SHARED_QML_LABELS = {
    "WizZ", "WizZ Desktop", "WizZ Quick Panel", "Color Studio",
    "Color", "Hotkeys", "HEX", "KELVIN", "OLED", "IP", "MAC", "RGB", "Firmware",
}
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


def _without_qml_comments(source: str) -> str:
    """Mask comments while preserving string literals, offsets and line numbers."""
    result = list(source)
    index = 0
    state = "code"
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if char in ('"', "'"):
                state = char
            elif char == "/" and next_char in ("/", "*"):
                state = "line" if next_char == "/" else "block"
                result[index] = result[index + 1] = " "
                index += 1
        elif state in ('"', "'"):
            if char == "\\":
                index += 1
            elif char == state:
                state = "code"
        elif state == "line":
            if char == "\n":
                state = "code"
            else:
                result[index] = " "
        elif state == "block":
            if char == "*" and next_char == "/":
                result[index] = result[index + 1] = " "
                index += 1
                state = "code"
            elif char != "\n":
                result[index] = " "
        index += 1
    return "".join(result)


def _qml_location(path: Path, source: str, offset: int) -> str:
    try:
        name = path.relative_to(ROOT).as_posix()
    except ValueError:
        name = path.name
    return f"{name}:{source.count(chr(10), 0, offset) + 1}"


def _qml_sources(paths: Iterable[Path] | None = None) -> Iterable[tuple[Path, str]]:
    for path in paths if paths is not None else sorted(QML_DIR.rglob("*.qml")):
        yield path, _without_qml_comments(path.read_text(encoding="utf-8"))


def qml_hardcoded_strings(paths: Iterable[Path] | None = None) -> list[str]:
    """Report direct, human-readable QML literals on visible properties."""
    findings: list[str] = []
    for path, source in _qml_sources(paths):
        for match in VISIBLE_QML_PROPERTIES.finditer(source):
            line_start = source.rfind("\n", 0, match.start()) + 1
            prefix = source[line_start:match.start()]
            if re.search(r"\b(?:required\s+)?property\s+\w+\s+$", prefix):
                continue  # a property declaration, not displayed text
            value = match.group("literal")[1:-1].strip()
            if not value or value in SHARED_QML_LABELS:
                continue
            if re.fullmatch(r"#[0-9a-fA-F]{6,8}|\d+(?:\.\d+)?(?:ms|s|K)", value):
                continue  # color examples, durations and Kelvin values
            if not any(char.isalpha() for char in value):
                continue  # punctuation, numbers, IP addresses or color values
            findings.append(
                f"{_qml_location(path, source, match.start())}: "
                f"{match.group('property')}: {value}"
            )
    return findings


def qml_translation_pair_errors(paths: Iterable[Path] | None = None) -> list[str]:
    """Ensure every root.t call supplies a nonempty Spanish and English literal."""
    errors: list[str] = []
    for path, source in _qml_sources(paths):
        pairs = {match.start(): match for match in QML_TRANSLATION_PAIR.finditer(source)}
        for call in QML_TRANSLATION_CALL.finditer(source):
            pair = pairs.get(call.start())
            if pair is None or not all(pair.group(language)[1:-1].strip() for language in ("spanish", "english")):
                errors.append(f"{_qml_location(path, source, call.start())}: incomplete root.t(es, en) pair")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit WizZ Desktop translations")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return a failure code when hardcoded UI strings remain",
    )
    args = parser.parse_args()

    errors = catalog_errors() + qml_translation_pair_errors()
    if errors:
        print("Translation errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    python_findings = hardcoded_ui_strings()
    qml_findings = qml_hardcoded_strings()
    findings = python_findings + qml_findings
    print(f"Catalogs OK: {len(CATALOGS['en'])} keys · en/es")
    print(f"Potential hardcoded UI strings: {len(python_findings)} Python, {len(qml_findings)} QML")
    for finding in findings:
        print(f"  {finding}")

    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
