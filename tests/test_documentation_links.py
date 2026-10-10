"""Keep local Markdown references navigable after documentation moves."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_local_documentation_links_resolve() -> None:
    documents = [ROOT / "README.md", ROOT / "README.es.md"]
    documents.extend((ROOT / "docs").rglob("*.md"))
    missing: list[str] = []

    for document in documents:
        for match in MARKDOWN_LINK.finditer(document.read_text(encoding="utf-8")):
            destination = match.group(1).strip().split("#", 1)[0]
            if not destination or destination.startswith(("https://", "http://", "mailto:")):
                continue
            target = (document.parent / unquote(destination)).resolve()
            if not target.exists():
                missing.append(f"{document.relative_to(ROOT)} → {destination}")

    assert not missing, "Broken local documentation links:\n" + "\n".join(missing)
