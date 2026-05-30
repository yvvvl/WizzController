from __future__ import annotations

from .base_manager import JsonManager


class ControllerSettingsManager(JsonManager):
    """Preferencias livianas del controlador LAN."""

    DEFAULTS = {
        "target_mode": "single",      # single | all
        "active_ip": None,
        "slider_interval_ms": 65,      # throttle UI/envío para sliders/drag
    }

    def __init__(self):
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

    def get_target_mode(self) -> str:
        mode = str(self.data.get("target_mode") or "single").lower()
        return mode if mode in ("single", "all") else "single"

    def set_target_mode(self, mode: str) -> None:
        mode = str(mode or "single").lower()
        self.data["target_mode"] = mode if mode in ("single", "all") else "single"
        self.save()

    def get_active_ip(self) -> str | None:
        ip = self.data.get("active_ip")
        return str(ip) if ip else None

    def set_active_ip(self, ip: str | None) -> None:
        self.data["active_ip"] = str(ip) if ip else None
        self.save()

    def get_slider_interval_ms(self) -> int:
        try:
            return max(35, min(200, int(self.data.get("slider_interval_ms", 65))))
        except Exception:
            return 65

    def set_slider_interval_ms(self, value: int) -> None:
        self.data["slider_interval_ms"] = max(35, min(200, int(value)))
        self.save()
