from __future__ import annotations

import flet as ft
from localization import LocalizationManager
from ui.responsive import PANEL_BREAKPOINTS, Viewport
from ui.theme import Theme, mounted, supdate


class TargetSelector(ft.Container):
    """Selector compacto de destino (modo + ampolleta activa).

    Reutilizable desde el panel principal y desde Ajustes para cambiar el
    destino del control sin salir de la vista actual. El estado se lee de
    ``LightController`` (``get_target_config`` / ``get_bulbs_detailed``) y se
    refresca en cada callback de estado.
    """

    def __init__(self, wiz, *, i18n=None, compact: bool = False):
        self.wiz = wiz
        self.i18n = i18n or LocalizationManager(preference="es")
        self._viewport = Viewport(900, 720)
        super().__init__(
            padding=16 if compact else 18,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )
        self._build()

    # ------------------------------------------------------------------ #
    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def _build(self):
        self.mode_dropdown = ft.Dropdown(
            label=self._t("settings.target.mode"),
            value="single",
            options=[
                ft.DropdownOption(key="single", text=self._t("bulbs.mode.single")),
                ft.DropdownOption(key="all", text=self._t("bulbs.mode.all")),
            ],
            border_color=Theme.STROKE,
            bgcolor=Theme.BG,
            color=Theme.TEXT,
            dense=True,
            on_select=self._mode_changed,
            expand=True,
        )
        self.active_dropdown = ft.Dropdown(
            label=self._t("bulbs.active"),
            options=[],
            border_color=Theme.STROKE,
            bgcolor=Theme.BG,
            color=Theme.TEXT,
            dense=True,
            on_select=self._active_changed,
            expand=True,
        )

        self.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ADS_CLICK_ROUNDED, color=Theme.ACCENT, size=17),
                        ft.Text(self._t("settings.target.section"), style=Theme.LABEL),
                    ],
                    spacing=8,
                ),
                ft.ResponsiveRow(
                    breakpoints=PANEL_BREAKPOINTS,
                    spacing=12,
                    run_spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            content=self.mode_dropdown,
                            col={"xs": 12, "sm": 6, "lg": 5},
                        ),
                        ft.Container(
                            content=self.active_dropdown,
                            col={"xs": 12, "sm": 6, "lg": 7},
                        ),
                    ],
                ),
                ft.Text(self._t("settings.target.help"), color=Theme.FAINT, size=10),
            ],
            spacing=8,
        )

    # ------------------------------------------------------------------ #
    def _mode_changed(self, e):
        mode = self.mode_dropdown.value or "single"
        self.wiz.set_target_mode(mode)
        self.refresh()

    def _active_changed(self, e):
        if self.active_dropdown.value:
            self.wiz.set_active_bulb(self.active_dropdown.value)
            self.refresh()

    # ------------------------------------------------------------------ #
    def refresh(self) -> None:
        """Re-sincroniza dropdowns con el estado actual del controlador."""
        cfg = self.wiz.get_target_config()
        bulbs = self.wiz.get_bulbs_detailed()
        mode = str(cfg.get("mode", "single") or "single")

        self.mode_dropdown.value = mode
        self.mode_dropdown.disabled = not bulbs

        self.active_dropdown.options = [
            ft.DropdownOption(
                key=b["ip"],
                text=f"{'●' if b.get('online') else '○'} {b.get('name') or b['ip']} · {b['ip']}",
            )
            for b in bulbs
        ]
        active = cfg.get("active_ip")
        self.active_dropdown.value = active if active and active in {b["ip"] for b in bulbs} else None
        self.active_dropdown.disabled = (mode == "all") or (not bulbs)

        if mounted(self):
            supdate(self.mode_dropdown)
            supdate(self.active_dropdown)

    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        viewport = Viewport(max(280.0, float(width)), max(320.0, float(height)))
        self._viewport = viewport
        self.padding = 14 if viewport.compact else 18
        if update and mounted(self):
            supdate(self)