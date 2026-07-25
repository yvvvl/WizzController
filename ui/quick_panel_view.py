from __future__ import annotations

from typing import Any

import flet as ft

from localization import get_manager, translated_favorite_name
from ui.components.color_panel import ColorPanel
from ui.theme import Theme, mounted, supdate


class QuickPanelView(ft.Column):
    """Compact view composed from existing lighting UI and services."""

    def __init__(
        self,
        controller: Any,
        wiz: Any,
        *,
        i18n: Any | None = None,
        color_panel: Any | None = None,
    ) -> None:
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.controller = controller
        self.wiz = wiz
        self.i18n = i18n or get_manager()
        self.color_panel = color_panel or ColorPanel(wiz, i18n=self.i18n)
        self._snapshot: dict[str, Any] = {}

        set_viewport = getattr(self.color_panel, "set_viewport", None)
        if callable(set_viewport):
            set_viewport(390, 620)

        self.title = ft.Text(self._t("quick.title"), style=Theme.H2)
        self.online_status = ft.Text(
            self._t("common.offline"),
            color=Theme.FAINT,
            size=11,
        )
        self.header = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color=Theme.PRIMARY),
                    self.title,
                    ft.Container(expand=True),
                    self.online_status,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.only(left=4, right=4, top=4),
        )

        self.device_selector = ft.Dropdown(
            label=self._t("tray.target"),
            options=[],
            dense=True,
            filled=True,
            fill_color=Theme.CARD,
            border_color=Theme.STROKE,
            focused_border_color=Theme.PRIMARY,
            on_select=self._on_device_selected,
        )
        self.device_section = ft.Container(
            content=self.device_selector,
            padding=ft.Padding.symmetric(horizontal=2),
        )

        self.individual = ft.OutlinedButton(
            self._t("routines.target.single"),
            icon=ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,
            on_click=lambda e: self.controller.set_target_mode("single"),
            expand=True,
        )
        self.all_lights = ft.OutlinedButton(
            self._t("tray.all_lights"),
            icon=ft.Icons.LIGHTBULB_ROUNDED,
            on_click=lambda e: self.controller.set_target_mode("all"),
            expand=True,
        )
        self.target_row = ft.Row([self.individual, self.all_lights], spacing=8)

        self.power_on = ft.FilledButton(
            self._t("home.on"),
            icon=ft.Icons.POWER_SETTINGS_NEW_ROUNDED,
            bgcolor=Theme.PRIMARY,
            color="white",
            on_click=lambda e: self.controller.turn_on(),
            expand=True,
        )
        self.power_off = ft.OutlinedButton(
            self._t("home.off"),
            icon=ft.Icons.POWER_OFF_ROUNDED,
            on_click=lambda e: self.controller.turn_off(),
            expand=True,
        )
        self.power_row = ft.Row([self.power_on, self.power_off], spacing=8)

        self.color_host = ft.Container(
            content=self.color_panel.main_layout,
            border_radius=Theme.R_MD,
        )

        self.favorites_title = ft.Text(
            self._t("quick.favorites"),
            style=Theme.LABEL,
        )
        self.favorite_row = ft.ResponsiveRow(spacing=8, run_spacing=8)
        self.favorites_section = ft.Column(
            [self.favorites_title, self.favorite_row],
            spacing=8,
        )

        self.controls = [
            self.header,
            self.device_section,
            self.target_row,
            self.power_row,
            self.color_host,
            self.favorites_section,
        ]
        self._language_unsubscribe = self.i18n.subscribe(self.set_language)

    def _t(self, key: str, **values: Any) -> str:
        return self.i18n.translate(key, **values)

    def _on_device_selected(self, event: Any) -> None:
        control = getattr(event, "control", None)
        value = str(getattr(control, "value", "") or "").strip()
        if value:
            self.controller.select_device(value)

    def update_snapshot(self, snapshot: dict[str, Any]) -> None:
        self._snapshot = dict(snapshot or {})
        target = (
            self._snapshot.get("target")
            if isinstance(self._snapshot.get("target"), dict)
            else {}
        )
        devices = (
            self._snapshot.get("devices")
            if isinstance(self._snapshot.get("devices"), list)
            else []
        )
        status = (
            self._snapshot.get("status")
            if isinstance(self._snapshot.get("status"), dict)
            else {}
        )
        favorites = (
            self._snapshot.get("favorites")
            if isinstance(self._snapshot.get("favorites"), list)
            else []
        )

        self.device_selector.options = [
            ft.DropdownOption(
                key=str(device.get("ip") or ""),
                text=str(device.get("name") or device.get("ip") or ""),
            )
            for device in devices
            if isinstance(device, dict) and device.get("ip")
        ]
        active_ip = str(target.get("active_ip") or "")
        self.device_selector.value = active_ip or None

        online = bool(status.get("online"))
        self.online_status.value = self._t(
            "common.online" if online else "common.offline"
        )
        self.online_status.color = Theme.SUCCESS if online else Theme.FAINT
        self._refresh_target_styles(str(target.get("mode") or "single"))
        self._render_favorites(favorites)

        state = status.get("state")
        sync_state = getattr(self.color_panel, "sync_state", None)
        if isinstance(state, dict) and callable(sync_state):
            sync_state(dict(state))

        if mounted(self):
            supdate(self)

    def _refresh_target_styles(self, mode: str) -> None:
        selected = ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.20, Theme.PRIMARY),
            color=Theme.TEXT,
        )
        idle = ft.ButtonStyle(color=Theme.MUTED)
        self.individual.style = selected if mode == "single" else idle
        self.all_lights.style = selected if mode == "all" else idle

    def _render_favorites(self, favorites: list[Any]) -> None:
        icons = {
            "rgb": ft.Icons.PALETTE_ROUNDED,
            "white": ft.Icons.LIGHT_MODE_ROUNDED,
            "scene": ft.Icons.AUTO_AWESOME_ROUNDED,
            "brightness": ft.Icons.BRIGHTNESS_6_ROUNDED,
        }
        controls: list[ft.Control] = []
        for favorite in favorites:
            if not isinstance(favorite, dict) or not favorite.get("id"):
                continue
            uid = str(favorite["id"])
            kind = str(favorite.get("type") or "")
            name = (
                translated_favorite_name(self.i18n, favorite)
                or self._t("color_studio.favorite_default")
            )
            controls.append(
                ft.TextButton(
                    name,
                    icon=icons.get(kind, ft.Icons.STAR_ROUNDED),
                    data=uid,
                    col={"xs": 6, "sm": 4},
                    on_click=lambda e, selected=uid: self.controller.run_favorite(
                        selected
                    ),
                )
            )
        if not controls:
            controls = [
                ft.Container(
                    content=ft.Text(
                        self._t("favorites.empty"),
                        color=Theme.FAINT,
                        size=11,
                    ),
                    col=12,
                )
            ]
        self.favorite_row.controls = controls

    def set_language(self, language: str | None = None) -> None:
        self.title.value = self._t("quick.title")
        self.device_selector.label = self._t("tray.target")
        self.individual.content = self._t("routines.target.single")
        self.all_lights.content = self._t("tray.all_lights")
        self.power_on.content = self._t("home.on")
        self.power_off.content = self._t("home.off")
        self.favorites_title.value = self._t("quick.favorites")

        set_language = getattr(self.color_panel, "set_language", None)
        if callable(set_language):
            set_language(language)
            self.color_host.content = self.color_panel.main_layout
        if self._snapshot:
            self.update_snapshot(self._snapshot)
        elif mounted(self):
            supdate(self)

__all__ = ["QuickPanelView"]
