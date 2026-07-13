from types import SimpleNamespace

from ui.interaction import DragPositionTracker


def _p(x, y):
    return SimpleNamespace(x=x, y=y)


def _event(*, local=None, global_pos=None, local_delta=None, global_delta=None):
    return SimpleNamespace(
        local_position=_p(*local) if local is not None else None,
        global_position=_p(*global_pos) if global_pos is not None else None,
        local_delta=_p(*local_delta) if local_delta is not None else None,
        global_delta=_p(*global_delta) if global_delta is not None else None,
    )


def test_drag_tracker_ignores_wrapped_local_position_at_right_edge():
    tracker = DragPositionTracker(300, 300)
    assert tracker.begin(_event(local=(150, 120), global_pos=(500, 400))) == (150.0, 120.0)

    # Simula el frame defectuoso observado: local x vuelve a 0, pero la
    # posición global avanzó realmente 150 px hacia la derecha.
    point = tracker.move(_event(local=(0, 120), global_pos=(650, 400)))
    assert point == (299.0, 120.0)


def test_drag_tracker_ignores_wrapped_local_position_at_left_edge():
    tracker = DragPositionTracker(300, 300)
    tracker.begin(_event(local=(150, 120), global_pos=(500, 400)))
    point = tracker.move(_event(local=(299, 120), global_pos=(350, 400)))
    assert point == (0.0, 120.0)


def test_drag_tracker_clamps_pointer_outside_control():
    tracker = DragPositionTracker(300, 300)
    tracker.begin(_event(local=(100, 100), global_pos=(500, 400)))
    assert tracker.move(_event(local=(999, -999), global_pos=(1000, -100))) == (299.0, 0.0)


def test_drag_tracker_falls_back_to_local_delta_and_tap():
    tracker = DragPositionTracker(100, 80)
    tracker.begin(_event(local=(20, 30)))
    assert tracker.move(_event(local=(0, 0), local_delta=(90, 100))) == (99.0, 79.0)
    assert tracker.tap(_event(local=(5, 7))) == (5.0, 7.0)


def test_drag_tracker_prefers_accumulated_delta_when_local_wraps():
    tracker = DragPositionTracker(300, 300)
    tracker.begin(_event(local=(150, 120), global_pos=(500, 400)))
    point = tracker.move(
        _event(
            local=(0, 120),
            global_pos=(0, 0),  # frame global defectuoso
            local_delta=(150, 0),
            global_delta=(150, 0),
        )
    )
    assert point == (299.0, 120.0)


def test_drag_tracker_rejects_opposite_edge_wrap_without_delta_sources():
    tracker = DragPositionTracker(300, 300)
    tracker.begin(_event(local=(280, 120)))
    assert tracker.move(_event(local=(290, 120))) == (290.0, 120.0)
    # Sin delta/global no hay evidencia de un recorrido real completo; mantener
    # el último punto evita el flash al borde contrario.
    assert tracker.move(_event(local=(0, 120))) == (290.0, 120.0)
