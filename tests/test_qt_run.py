from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from qt_ui import run


def test_qt_controller_factory_uses_real_lights(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(run, "LightController", lambda: sentinel)

    assert run.create_controller() is sentinel
