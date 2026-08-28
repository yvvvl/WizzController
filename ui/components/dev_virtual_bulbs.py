"""Visual development fixture for :mod:`core.dev_virtual_lights`."""
from __future__ import annotations

import math

import flet as ft

from ui.theme import Theme, supdate


def _kelvin_rgb(kelvin: int) -> str:
    """Compact, presentation-only CCT approximation."""
    temperature = max(1000.0, min(40000.0, float(kelvin))) / 100.0
    if temperature <= 66:
        red = 255
        green = 99.4708025861 * math.log(temperature) - 161.1195681661
        blue = 0 if temperature <= 19 else 138.5177312231 * math.log(temperature - 10) - 305.0447927307
    else:
        red = 329.698727446 * ((temperature - 60) ** -0.1332047592)
        green = 288.1221695283 * ((temperature - 60) ** -0.0755148492)
        blue = 255
    values = [max(0, min(255, round(value))) for value in (red, green, blue)]
    return "#{:02x}{:02x}{:02x}".format(*values)


def _state_color(state: dict) -> str:
    if not state.get("state", True):
        return "#334155"
    if isinstance(state.get("_virtual_rgb"), (tuple, list)) and len(state["_virtual_rgb"]) == 3:
        values = [max(0, min(255, int(value))) for value in state["_virtual_rgb"]]
        return "#{:02x}{:02x}{:02x}".format(*values)
    if all(key in state for key in ("r", "g", "b")):
        values = [max(0, min(255, int(state[key]))) for key in ("r", "g", "b")]
        return "#{:02x}{:02x}{:02x}".format(*values)
    return _kelvin_rgb(int(state.get("temp", 4000)))


class DevVirtualBulbPreview(ft.Container):
    """Live visual state of virtual lights, rendered only in DEV mode."""

    def __init__(self, wiz, *, i18n, on_target_selected=None):
        super().__init__(
            padding=16,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.ACCENT),
        )
        self.wiz = wiz
        self.i18n = i18n
        self.on_target_selected = on_target_selected
        self._cards: dict[str, ft.Container] = {}
        self.rows = ft.ResponsiveRow(spacing=10, run_spacing=10)
        self.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.SCIENCE_ROUNDED, color=Theme.ACCENT, size=18),
                                ft.Text(self._t("dev.virtual.title"), style=Theme.LABEL),
                            ],
                            spacing=8,
                        ),
                        ft.Text(self._t("dev.virtual.no_network"), color=Theme.WARNING, size=11),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(self._t("dev.virtual.hint"), color=Theme.MUTED, size=12),
                self.rows,
            ],
            spacing=10,
        )
        self.refresh()

    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def refresh(self) -> None:
        items = self.wiz.get_virtual_bulbs()
        self._cards = {str(item["ip"]): self._bulb_card(item) for item in items}
        self.rows.controls = list(self._cards.values())
        supdate(self.rows)

    def refresh_selection(self) -> None:
        """Update target borders without reading or redrawing scene colours."""
        targeted = {str(item["ip"]) for item in self.wiz.get_virtual_bulbs() if item.get("targeted")}
        for ip, card in self._cards.items():
            active = ip in targeted
            card.bgcolor = Theme.CARD_HI if active else Theme.SURFACE
            card.border = ft.Border.all(1, Theme.PRIMARY if active else Theme.STROKE)
            supdate(card)

    def _bulb_card(self, item: dict) -> ft.Container:
        state = dict(item.get("state") or {})
        color = _state_color(state)
        on = bool(state.get("state", True))
        brightness = int(state.get("dimming", 100) or 100)
        targeted = bool(item.get("targeted"))
        glow = ft.Colors.with_opacity(max(0.10, min(0.55, brightness / 180)), color) if on else None
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4},
            padding=12,
            border_radius=Theme.R_SM,
            bgcolor=Theme.CARD_HI if targeted else Theme.SURFACE,
            border=ft.Border.all(1, Theme.PRIMARY if targeted else Theme.STROKE),
            on_click=lambda _e, ip=item["ip"]: self._select_bulb(ip),
            ink=True,
            content=ft.Row(
                [
                    ft.Container(
                        width=38,
                        height=38,
                        border_radius=19,
                        bgcolor=color,
                        shadow=ft.BoxShadow(blur_radius=18, color=glow) if glow else None,
                        content=ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color="#ffffff" if on else Theme.MUTED, size=21),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(str(item["name"]), color=Theme.TEXT, weight=ft.FontWeight.W_600, size=12),
                            ft.Text(
                                self._t("dev.virtual.state", power=self._t("dev.virtual.on") if on else self._t("dev.virtual.off"), brightness=brightness),
                                color=Theme.MUTED,
                                size=11,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=10,
            ),
        )

    def _select_bulb(self, ip: str) -> None:
        self.wiz.set_active_bulb(ip)
        # Repaint synchronously: this is a direct selection interaction, not
        # a light command that can wait for a controller callback.
        self.refresh_selection()
        callback = self.on_target_selected
        if callable(callback):
            try:
                callback()
            except Exception:
                pass
