"""Pure release-channel and version selection helpers."""

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
    checksum_url: str | None = None


def _version_key(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", str(value))
    return tuple(int(item) for item in numbers) or (0,)


def parse_release(payload: dict[str, Any], *, platform: str = "windows") -> ReleaseInfo | None:
    tag = str(payload.get("tag_name") or payload.get("name") or "").strip()
    if not tag:
        return None
    assets = payload.get("assets")
    download = None
    checksum = None
    if isinstance(assets, list):
        expected = f"-{platform}-"
        package = next(
            (asset for asset in assets if isinstance(asset, dict)
             and expected in str(asset.get("name") or "").lower()
             and str(asset.get("name") or "").lower().endswith(".zip")),
            None,
        )
        if isinstance(package, dict):
            download = str(package.get("browser_download_url") or "") or None
            package_name = str(package.get("name") or "")
            checksum_asset = next(
                (asset for asset in assets if isinstance(asset, dict)
                 and str(asset.get("name") or "") == package_name + ".sha256"),
                None,
            )
            if isinstance(checksum_asset, dict):
                checksum = str(checksum_asset.get("browser_download_url") or "") or None
    return ReleaseInfo(
        version=tag.lstrip("vV"),
        download_url=download,
        prerelease=bool(payload.get("prerelease", False)),
        notes_url=str(payload.get("html_url")) if payload.get("html_url") else None,
        checksum_url=checksum,
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
