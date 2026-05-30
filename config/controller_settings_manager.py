from __future__ import annotations

from typing import Any

from .base_manager import JsonManager


class ControllerSettingsManager(JsonManager):
    """Preferencias pequeñas del controlador/UI.

    Se guarda en config/json/controller_settings.json.
    """

    DEFAULTS: dict[str, Any] = {
        "target_mode": "single",           # single | all
        "active_ip": None,
        "brightness_default": 100,
        "white_default_percent": 50,
        "slider_interval_ms": 55,          # throttle de sliders de brillo/velocidad
        "color_send_interval_ms": 65,      # throttle del picker de color
    }

    def __init__(self) -> None:
        super().__init__("controller_settings.json", default_data=dict(self.DEFAULTS))
        if not isinstance(self.data, dict):
            self.data = dict(self.DEFAULTS)
        changed = False
        for key, value in self.DEFAULTS.items():
            if key not in self.data:
                self.data[key] = value
                changed = True
        if changed:
            self.save()

    def _set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def get_target_mode(self) -> str:
        mode = self.data.get("target_mode", "single")
        return mode if mode in ("single", "all") else "single"

    def set_target_mode(self, mode: str) -> None:
        self._set("target_mode", mode if mode in ("single", "all") else "single")

    def get_active_ip(self) -> str | None:
        value = self.data.get("active_ip")
        return str(value) if value else None

    def set_active_ip(self, ip: str | None) -> None:
        self._set("active_ip", str(ip) if ip else None)

    def get_brightness_default(self) -> int:
        try:
            return int(self.data.get("brightness_default", 100))
        except Exception:
            return 100

    def set_brightness_default(self, value: int) -> None:
        self._set("brightness_default", int(max(10, min(100, value))))

    def get_white_default_percent(self) -> int:
        try:
            return int(self.data.get("white_default_percent", 50))
        except Exception:
            return 50

    def set_white_default_percent(self, value: int) -> None:
        self._set("white_default_percent", int(max(0, min(100, value))))

    def get_slider_interval_ms(self) -> int:
        try:
            return int(self.data.get("slider_interval_ms", 55))
        except Exception:
            return 55

    def get_color_send_interval_ms(self) -> int:
        try:
            return int(self.data.get("color_send_interval_ms", 65))
        except Exception:
            return 65

    def set_slider_interval_ms(self, value: int) -> None:
        self._set("slider_interval_ms", int(max(35, min(160, value))))

    def set_color_send_interval_ms(self, value: int) -> None:
        self._set("color_send_interval_ms", int(max(35, min(180, value))))
