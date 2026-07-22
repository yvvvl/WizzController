from __future__ import annotations

import main as app_main


class FakeLoop:
    def __init__(self) -> None:
        self.pending: list[object] = []
        self.closed = False

    def is_closed(self) -> bool:
        return self.closed

    def call_soon_threadsafe(self, callback) -> None:
        self.pending.append(callback)

    def flush(self) -> None:
        while self.pending:
            callback = self.pending.pop(0)
            callback()


class FakePage:
    def __init__(self) -> None:
        self.loop = FakeLoop()
        self.updates = 0

    def update(self) -> None:
        self.updates += 1


def test_wiz_callback_is_dispatched_through_page_loop() -> None:
    page = FakePage()
    received: list[dict] = []
    state = {
        "state": True,
        "_scan": {
            "running": False,
            "found": 1,
        },
    }

    scheduled = app_main._dispatch_wiz_state(
        page,
        received.append,
        state,
    )

    assert scheduled is True
    assert received == []
    assert page.updates == 0

    page.loop.flush()

    assert received == [state]
    assert page.updates == 1


def test_closed_page_loop_rejects_callback() -> None:
    page = FakePage()
    page.loop.closed = True
    received: list[dict] = []

    scheduled = app_main._dispatch_wiz_state(
        page,
        received.append,
        {"state": True},
    )

    assert scheduled is False
    assert received == []
    assert page.updates == 0
