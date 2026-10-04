"""Read-only GitHub Releases client for the future updater UI."""

from __future__ import annotations

import json
import platform as host_platform
import sys
from urllib.request import Request, urlopen
from typing import Any

from .update_checker import ReleaseInfo, select_latest_release


class ReleaseClient:
    def __init__(self, owner: str = "yvvvl", repo: str = "WizzController", *, timeout: float = 5.0):
        self.owner = owner
        self.repo = repo
        self.timeout = float(timeout)

    @property
    def endpoint(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repo}/releases"

    @staticmethod
    def current_platform_asset() -> str:
        if sys.platform == "darwin":
            # macOS packages are published as macos-arm64 or macos-x64 ZIPs;
            # use the shared prefix so either architecture can be discovered.
            return "macos"
        if not sys.platform.startswith("linux"):
            return "windows"
        machine = host_platform.machine().strip().lower()
        if machine in {"aarch64", "arm64"}:
            return "linux-arm64"
        if machine in {"x86_64", "amd64"}:
            return "linux-x64"
        return f"linux-{machine}"

    def latest(self, *, channel: str = "stable") -> ReleaseInfo | None:
        request = Request(
            self.endpoint,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "WizZ-Desktop-Updater",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            payload: Any = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, list):
            return None
        return select_latest_release(
            payload,
            channel=channel,
            platform=self.current_platform_asset(),
        )


__all__ = ["ReleaseClient"]
