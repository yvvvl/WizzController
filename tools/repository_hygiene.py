"""Fail CI if local state or generated artifacts become tracked by Git."""

from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DIRECTORIES = {
    ".venv", "venv", "env", "build", "dist", "logs", "models",
    "artifacts", "backups", ".patch_backups", ".pytest_cache",
    ".ruff_cache", "__pycache__", ".idea", ".vscode", ".flet",
    ".flutter",
}
GENERATED_SUFFIXES = {".pyc", ".pyo", ".log", ".spec", ".sqlite", ".sqlite3", ".db"}


def problem_for_path(name: str) -> str | None:
    """Classify tracked paths, not untracked local development files."""
    path = PurePosixPath(name)
    if any(part in LOCAL_DIRECTORIES or part.endswith(".egg-info") for part in path.parts[:-1]):
        return "local or generated directory"
    if path.suffix.lower() in GENERATED_SUFFIXES or path.name in {".env", "console.log"}:
        return "local or generated file"
    if path.name.startswith(".env.") and path.name != ".env.example":
        return "environment-specific configuration"
    if path.parts[:2] == ("config", "json") and path.suffix == ".json":
        if not path.name.endswith(".example.json"):
            return "personal application configuration"
    return None


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    )
    tracked = (name.decode("utf-8") for name in result.stdout.split(b"\0") if name)
    problems = [(name, reason) for name in tracked if (reason := problem_for_path(name))]
    for name, reason in problems:
        print(f"{name}: {reason}")
    if problems:
        print(f"Found {len(problems)} tracked local/generated file(s).")
        return 1
    print("Repository hygiene: no tracked local/generated files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
