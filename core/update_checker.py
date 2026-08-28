"""Pure release-channel and version selection helpers.

Network access and installation are intentionally left to a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    download_url: str | None = None
    prerelease: bool = False
    notes_url: str | None = None


def _version_key(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", str(value))
    return tuple(int(item) for item in numbers) or (0,)


def parse_release(payload: dict[str, Any]) -> ReleaseInfo | None:
    tag = str(payload.get("tag_name") or payload.get("name") or "").strip()
    if not tag:
        return None
    assets = payload.get("assets")
    download = None
    if isinstance(assets, list):
        for asset in assets:
            if isinstance(asset, dict) and asset.get("browser_download_url"):
                download = str(asset["browser_download_url"])
                break
    return ReleaseInfo(
        version=tag.lstrip("vV"),
        download_url=download,
        prerelease=bool(payload.get("prerelease", False)),
        notes_url=str(payload.get("html_url")) if payload.get("html_url") else None,
    )


def select_latest_release(
    payloads: Iterable[dict[str, Any]],
    *,
    channel: str = "stable",
) -> ReleaseInfo | None:
    allow_prerelease = str(channel).strip().lower() in {"beta", "prerelease"}
    releases = []
    for payload in payloads:
        release = parse_release(payload)
        if release is not None and (allow_prerelease or not release.prerelease):
            releases.append(release)
    return max(releases, key=lambda item: _version_key(item.version), default=None)


def is_update_available(current_version: str, release: ReleaseInfo | None) -> bool:
    return release is not None and _version_key(release.version) > _version_key(current_version)


__all__ = ["ReleaseInfo", "is_update_available", "parse_release", "select_latest_release"]
