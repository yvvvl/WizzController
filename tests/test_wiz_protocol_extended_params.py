import json

from core.wiz_protocol import WIZ_PORT, WizProtocol


class RecordingTransport:
    def __init__(self):
        self.sent = []

    def sendto(self, data, address):
        self.sent.append((data, address))


def send_and_decode(params):
    protocol = WizProtocol()
    transport = RecordingTransport()
    protocol.connection_made(transport)

    protocol.send_pilot("192.0.2.10", params)

    assert len(transport.sent) == 1
    data, address = transport.sent[0]
    assert address == ("192.0.2.10", WIZ_PORT)
    return json.loads(data.decode("utf-8"))


def test_send_pilot_preserves_normal_payload():
    message = send_and_decode({"state": True, "dimming": 42})

    assert message == {
        "id": 1,
        "method": "setPilot",
        "params": {"state": True, "dimming": 42},
    }


def test_send_pilot_preserves_nested_elm_payload():
    params = {
        "sceneId": 257,
        "elm": {
            "steps": [
                {"r": 255, "g": 0, "b": 0, "weight": 2},
                {"r": 0, "g": 255, "b": 0, "weight": 1},
            ]
        },
    }

    message = send_and_decode(params)

    assert message["params"] == params


def test_send_pilot_preserves_unknown_keys_without_special_cases():
    params = {
        "futureMode": "experimental",
        "extension": {
            "vendorKey": [1, {"unexpected": True}],
        },
    }

    message = send_and_decode(params)

    assert message["params"] == params
