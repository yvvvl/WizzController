from core.action_sequence import ActionSequenceExecutor


class FakeWiz:
    def __init__(self):
        self.calls = []
        self.state = {"dimming": 50}

    def turn_on(self): self.calls.append(("turn_on",))
    def turn_off(self): self.calls.append(("turn_off",))
    def toggle(self): self.calls.append(("toggle",))
    def set_brightness(self, value): self.calls.append(("brightness", int(value))); self.state["dimming"] = int(value)
    def set_rgb(self, r, g, b): self.calls.append(("rgb", int(r), int(g), int(b)))
    def set_white(self, k): self.calls.append(("white", int(k)))
    def set_scene(self, sid, speed=None): self.calls.append(("scene", int(sid), speed))
    def get_state(self): return dict(self.state)


def test_sequence_executes_in_order():
    wiz = FakeWiz()
    ex = ActionSequenceExecutor(wiz)
    ex.execute([
        {"type":"turn_on"},
        {"type":"rgb", "value":"#ff0000"},
        {"type":"brightness", "value":50},
    ], threaded=False)
    assert wiz.calls == [("turn_on",), ("rgb",255,0,0), ("brightness",50)]


def test_brightness_delta_uses_dimming():
    wiz = FakeWiz()
    ex = ActionSequenceExecutor(wiz)
    ex.execute({"type":"brightness_delta", "value":10}, threaded=False)
    assert ("brightness", 60) in wiz.calls
