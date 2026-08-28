import json

from core.update_client import ReleaseClient


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps([
            {"tag_name": "v1.3.0-beta.1", "prerelease": True},
            {"tag_name": "v1.2.0", "prerelease": False},
        ]).encode("utf-8")


def test_release_client_selects_stable(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout, request.get_header("User-agent")))
        return _Response()

    monkeypatch.setattr("core.update_client.urlopen", fake_urlopen)
    release = ReleaseClient(timeout=3).latest()

    assert release is not None
    assert release.version == "1.2.0"
    assert calls[0][0].endswith("/repos/yvvvl/WizzController/releases")
    assert calls[0][1] == 3


def test_release_client_can_select_beta(monkeypatch):
    monkeypatch.setattr("core.update_client.urlopen", lambda *args, **kwargs: _Response())
    release = ReleaseClient().latest(channel="beta")

    assert release is not None
    assert release.version == "1.3.0-beta.1"
