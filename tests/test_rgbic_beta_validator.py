from __future__ import annotations

from tools.rgbic_beta_validator import sanitize_validation_record


def test_beta_validator_sanitizes_ip_and_mac_from_payload_and_notes():
    record = {
        "payload": {
            "mac": "aa:bb:cc:dd:ee:ff",
            "ip": "192.168.1.4",
            "elm": {"steps": [[0, 255, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, 1]]},
        },
        "notes": "Tested against 192.168.1.4 and aa:bb:cc:dd:ee:ff",
        "visual_status": "unconfirmed",
    }

    sanitized = sanitize_validation_record(record)

    assert sanitized["payload"].get("mac") == "<redacted>"
    assert "192.168.1.4" not in sanitized["notes"]
    assert "aa:bb:cc:dd:ee:ff" not in sanitized["notes"]
