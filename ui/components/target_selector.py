from __future__ import annotations

import flet as ft
from localization import LocalizationManager
from ui.responsive import PANEL_BREAKPOINTS, Viewport
from ui.theme import Theme, mounted, supdate

class TargetSelector(ft.Container):
    """Selector visual de bombillas con chips interactivos para selección individual y múltiple."""

    def __init__(self, wiz, *, i18n=None, compact: bool = False, on_selection_changed=None):
        self.wiz = wiz
        self.i18n = i18n or LocalizationManager(preference="es")
        self.on_selection_changed = on_selection_changed
        self._viewport = Viewport(900, 720)
        self.selected_targets: list[str] = []

        super().__init__(
            padding=14 if compact else 16,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )
        self._build()
        self.refresh()

    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def _build(self):
        self.selection_status = ft.Text("", size=11, color=Theme.ACCENT, weight=ft.FontWeight.W_500)
        self.chip_container = ft.Row(
            spacing=8,
            wrap=True,
            run_spacing=8,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.btn_select_all = ft.IconButton(
            icon=ft.Icons.SELECT_ALL_ROUNDED,
            on_click=self.select_all,
            tooltip=self._t("bulbs.select_all"),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(8, 4, 8, 4),
            ),
        )

        self.btn_invert = ft.IconButton(
            icon=ft.Icons.SWAP_HORIZ_ROUNDED,
            on_click=self.invert_selection,
            tooltip=self._t("bulbs.invert_selection"),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(8, 4, 8, 4),
            ),
        )

        self.action_buttons = ft.Row(
            spacing=4,
            controls=[self.btn_select_all, self.btn_invert],
        )

        self.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color=Theme.ACCENT, size=17),
                                ft.Text(self._t("settings.target.section"), style=Theme.LABEL),
                            ],
                            spacing=8,
                        ),
                        self.selection_status,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    spacing=8,
                ),
                ft.Row(
                    [
                        self.action_buttons,
                        self.chip_container,
                    ],
                    spacing=12,
                    wrap=True,
                ),
                ft.Text(self._t("settings.target.help"), color=Theme.FAINT, size=10),
            ],
            spacing=8,
        )

    def _create_chip(self, bulb: dict) -> ft.Chip:
        ip = str(bulb.get("ip", ""))
        name = bulb.get("name") or ip or "Luz"
        is_selected = ip in self.selected_targets
        state = bulb.get("state", {})
        is_on = state.get("state", False) if isinstance(state, dict) else False

        return ft.Chip(
            label=ft.Text(name, size=12, color=ft.Colors.WHITE if is_selected else Theme.TEXT),
            on_click=lambda e, target_ip=ip: self.toggle_selection(target_ip),
            bgcolor=Theme.ACCENT if is_selected else Theme.SURFACE,
            elevation=2 if is_selected else 0,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding(8, 4, 8, 4),
            leading=ft.Icon(
                ft.Icons.LIGHTBULB if is_on else ft.Icons.LIGHTBULB_OUTLINE,
                size=14,
                color=ft.Colors.AMBER_300 if is_on else (ft.Colors.WHITE_70 if is_selected else Theme.MUTED),
            ),
        )

    def toggle_selection(self, ip: str):
        if not ip:
            return

        if ip in self.selected_targets:
            if len(self.selected_targets) > 1:
                self.selected_targets.remove(ip)
        else:
            self.selected_targets.append(ip)

        self._apply_targets()
        self._update_chips()

    def select_all(self, e=None):
        bulbs = self.wiz.get_bulbs_detailed() if hasattr(self.wiz, "get_bulbs_detailed") else []
        self.selected_targets = [str(b["ip"]) for b in bulbs if b.get("ip")]
        self._apply_targets()
        self._update_chips()

    def invert_selection(self, e=None):
        bulbs = self.wiz.get_bulbs_detailed() if hasattr(self.wiz, "get_bulbs_detailed") else []
        all_ips = {str(b["ip"]) for b in bulbs if b.get("ip")}
        current = set(self.selected_targets)
        inverted = list(all_ips - current)
        if inverted:
            self.selected_targets = inverted
        elif all_ips:
            self.selected_targets = [next(iter(all_ips))]

        self._apply_targets()
        self._update_chips()

    def _apply_targets(self):
        bulbs = self.wiz.get_bulbs_detailed() if hasattr(self.wiz, "get_bulbs_detailed") else []
        total_bulbs = len(bulbs)

        if total_bulbs > 0 and len(self.selected_targets) >= total_bulbs:
            if hasattr(self.wiz, "set_target_mode"):
                self.wiz.set_target_mode("all")
        elif len(self.selected_targets) == 1:
            if hasattr(self.wiz, "set_active_bulb"):
                self.wiz.set_active_bulb(self.selected_targets[0])
        elif self.selected_targets:
            if len(self.selected_targets) > 1 and hasattr(self.wiz, "set_target_selection"):
                self.wiz.set_target_selection(self.selected_targets)
            elif hasattr(self.wiz, "set_active_bulb"):
                self.wiz.set_active_bulb(self.selected_targets[0])

    def _update_chips(self):
        bulbs = self.wiz.get_bulbs_detailed() if hasattr(self.wiz, "get_bulbs_detailed") else []
        self.chip_container.controls = [self._create_chip(b) for b in bulbs]
        self.selection_status.value = self._selection_label(len(bulbs))
        if mounted(self):
            supdate(self)

        # A destination click is UI state in its own right.  Consumers such as
        # the DEV virtual-bulb preview must not wait for a later light command
        # or the asynchronous controller callback to repaint their selection.
        callback = self.on_selection_changed
        if callable(callback):
            try:
                callback()
            except Exception:
                pass

    def _selection_label(self, total_bulbs: int) -> str:
        selected = len(self.selected_targets)
        if total_bulbs <= 0:
            return self._t("target.selection.none")
        if selected <= 1:
            return self._t("target.selection.single")
        if selected >= total_bulbs:
            return self._t("target.selection.all", total=total_bulbs)
        return self._t("target.selection.partial", selected=selected, total=total_bulbs)

    def refresh(self) -> None:
        cfg = self.wiz.get_target_config() if hasattr(self.wiz, "get_target_config") else {}
        bulbs = self.wiz.get_bulbs_detailed() if hasattr(self.wiz, "get_bulbs_detailed") else []
        mode = cfg.get("mode", "single")
        active_ip = cfg.get("active_ip")
        selected_ips = cfg.get("selected_ips", [])
        available_ips = {str(b["ip"]) for b in bulbs if b.get("ip")}

        if not available_ips:
            self.selected_targets = []
        elif mode == "all":
            self.selected_targets = sorted(available_ips)
        elif mode == "selected" and isinstance(selected_ips, (list, tuple, set)):
            selected = [str(ip) for ip in selected_ips if str(ip) in available_ips]
            self.selected_targets = selected or ([str(active_ip)] if active_ip in available_ips else [])
        elif active_ip:
            self.selected_targets = [str(active_ip)]
        elif bulbs:
            self.selected_targets = [str(bulbs[0].get("ip"))]
        else:
            self.selected_targets = []

        self._update_chips()

    def set_language(self, language: str | None = None) -> None:
        self._build()
        self.refresh()

    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        viewport = Viewport(max(280.0, float(width)), max(320.0, float(height)))
        self._viewport = viewport
        self.padding = 14 if viewport.compact else 16
        if update and mounted(self):
            supdate(self)
