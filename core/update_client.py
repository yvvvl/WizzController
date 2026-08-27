"""Read-only GitHub Releases client for the future updater UI."""

from __future__ import annotations

import json
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
        return select_latest_release(payload, channel=channel)


__all__ = ["ReleaseClient"]
