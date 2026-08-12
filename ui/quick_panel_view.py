from __future__ import annotations

from typing import Any

import flet as ft

from localization import get_manager, translated_favorite_name
from ui.components.color_panel import ColorPanel
from ui.components.quick_color_studio_adapter import ColorStudioQuickAdapter
from ui.theme import Theme, mounted, supdate


class QuickPanelView(ft.Column):
    """Card-based overlay composed from existing lighting behavior."""

    def __init__(
        self,
        controller: Any,
        wiz: Any,
        *,
        i18n: Any | None = None,
        color_panel: Any | None = None,
        color_adapter: Any | None = None,
    ) -> None:
        super().__init__(expand=True, spacing=0)
        self.controller = controller
        self.wiz = wiz
        self.i18n = i18n or get_manager()
        self.color_panel = color_panel or ColorPanel(wiz, i18n=self.i18n)
        self.color_adapter = color_adapter or ColorStudioQuickAdapter(
            self.color_panel,
            i18n=self.i18n,
        )
        self._snapshot: dict[str, Any] = {}

        set_viewport = getattr(self.color_adapter, "set_viewport", None)
        if callable(set_viewport):
            set_viewport(390, 620)

        self.title = ft.Text(
            self._t("quick.title"),
            style=ft.TextStyle(
                color=Theme.MUTED,
                size=10,
                weight=ft.FontWeight.BOLD,
                letter_spacing=1.3,
            ),
        )
        self.product_name = ft.Text(self._t("app.name"), style=Theme.H2)
        self.device_name = ft.Text(
            self._t("quick.no_active_light"),
            color=Theme.TEXT,
            size=13,
            weight=ft.FontWeight.W_600,
        )
        self.status_dot = ft.Container(
            width=7,
            height=7,
            border_radius=4,
            bgcolor=Theme.FAINT,
        )
        self.online_status = ft.Text(
            self._t("common.offline"),
            color=Theme.FAINT,
            size=11,
        )
        self.settings_button = ft.IconButton(
            icon=ft.Icons.SETTINGS_OUTLINED,
            icon_color=Theme.MUTED,
            tooltip=self._t("quick.open_settings"),
            on_click=lambda event: self._open_full_section(5),
        )
        self.brand_icon = ft.Image(
            src="icon.png",
            width=38,
            height=38,
            fit=ft.BoxFit.CONTAIN,
        )
        self.device_selector = ft.Dropdown(
            label=self._t("tray.target"),
            options=[],
            dense=True,
            filled=True,
            fill_color=ft.Colors.with_opacity(0.45, Theme.SURFACE),
            border_color=Theme.STROKE,
            focused_border_color=Theme.PRIMARY,
            on_select=self._on_device_selected,
        )
        self.device_section = ft.Container(content=self.device_selector)
        self.header_card = self._card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=self.brand_icon,
                                width=42,
                                height=42,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Column(
                                [
                                    self.title,
                                    self.product_name,
                                    ft.Row(
                                        [
                                            self.status_dot,
                                            self.online_status,
                                            self.device_name,
                                        ],
                                        spacing=6,
                                        wrap=True,
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                            self.settings_button,
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.device_section,
                ],
                spacing=12,
            ),
        )

        self.target_title = ft.Text(self._t("tray.target"), style=Theme.LABEL)
        self.individual = ft.OutlinedButton(
            self._t("routines.target.single"),
            icon=ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,
            on_click=lambda event: self.controller.set_target_mode("single"),
            expand=True,
        )
        self.all_lights = ft.OutlinedButton(
            self._t("tray.all_lights"),
            icon=ft.Icons.LIGHTBULB_ROUNDED,
            on_click=lambda event: self.controller.set_target_mode("all"),
            expand=True,
        )
        self.target_row = ft.Row([self.individual, self.all_lights], spacing=8)
        self.target_card = self._card(
            ft.Column([self.target_title, self.target_row], spacing=8),
        )

        self.power_title = ft.Text(self._t("home.master"), style=Theme.LABEL)
        self.power_on = ft.FilledButton(
            self._t("home.on"),
            icon=ft.Icons.POWER_SETTINGS_NEW_ROUNDED,
            bgcolor=Theme.PRIMARY,
            color="white",
            height=48,
            on_click=lambda event: self.controller.turn_on(),
            expand=True,
        )
        self.power_off = ft.OutlinedButton(
            self._t("home.off"),
            icon=ft.Icons.POWER_OFF_ROUNDED,
            height=48,
            on_click=lambda event: self.controller.turn_off(),
            expand=True,
        )
        self.power_row = ft.Row([self.power_on, self.power_off], spacing=8)
        self.power_card = self._card(
            ft.Column([self.power_title, self.power_row], spacing=8),
        )

        self.studio_card = self._card(
            self.color_adapter,
            padding=10,
        )
        self.color_host = self.studio_card

        self.favorites_title = ft.Text(
            self._t("quick.favorites"),
            style=Theme.LABEL,
        )
        self.view_all = ft.TextButton(
            self._t("color_studio.view_all"),
            icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
            on_click=lambda event: self._open_full_section(3),
        )
        self.favorite_row = ft.ResponsiveRow(spacing=8, run_spacing=8)
        self.favorites_card = self._card(
            ft.Column(
                [
                    ft.Row(
                        [
                            self.favorites_title,
                            ft.Container(expand=True),
                            self.view_all,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.favorite_row,
                ],
                spacing=8,
            ),
        )
        self.favorites_section = self.favorites_card

        self.shell = ft.Container(
            content=ft.Column(
                [
                    self.header_card,
                    self.power_card,
                    self.target_card,
                    self.studio_card,
                    self.favorites_card,
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            expand=True,
            padding=14,
            bgcolor=Theme.BG,
            gradient=Theme.GRADIENT,
        )
        self.controls = [self.shell]
        self._language_unsubscribe = self.i18n.subscribe(self.set_language)

    def _t(self, key: str, **values: Any) -> str:
        return self.i18n.translate(key, **values)

    @staticmethod
    def _card(content: ft.Control, *, padding: int = 12) -> ft.Container:
        return ft.Container(
            content=content,
            padding=padding,
            border_radius=Theme.R_MD,
            bgcolor=ft.Colors.with_opacity(0.94, Theme.CARD),
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )

    def _open_full_section(self, index: int) -> None:
        handler = getattr(self.controller, "open_full_section", None)
        if callable(handler):
            handler(index)
            return
        fallback = getattr(self.controller, "open_full", None)
        if callable(fallback):
            fallback()

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
        self.status_dot.bgcolor = Theme.SUCCESS if online else Theme.FAINT
        self.device_name.value = str(
            status.get("name")
            or self._t("quick.no_active_light")
        )
        self._refresh_target_styles(str(target.get("mode") or "single"))
        self._render_favorites(favorites)

        state = status.get("state")
        sync_state = getattr(self.color_adapter, "sync_state", None)
        if isinstance(state, dict) and callable(sync_state):
            sync_state(dict(state))

        if mounted(self):
            supdate(self)

    def _refresh_target_styles(self, mode: str) -> None:
        selected = ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.20, Theme.PRIMARY),
            color=Theme.TEXT,
            side=ft.BorderSide(1, Theme.PRIMARY),
        )
        idle = ft.ButtonStyle(
            color=Theme.MUTED,
            side=ft.BorderSide(1, Theme.STROKE),
        )
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
        for favorite in favorites[:6]:
            if not isinstance(favorite, dict) or not favorite.get("id"):
                continue
            uid = str(favorite["id"])
            kind = str(favorite.get("type") or "")
            name = (
                translated_favorite_name(self.i18n, favorite)
                or self._t("color_studio.favorite_default")
            )
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                icons.get(kind, ft.Icons.STAR_ROUNDED),
                                color=Theme.PRIMARY,
                                size=20,
                            ),
                            ft.Text(
                                name,
                                color=Theme.TEXT,
                                size=11,
                                weight=ft.FontWeight.W_600,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=5,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    data=uid,
                    col=4,
                    height=70,
                    alignment=ft.Alignment.CENTER,
                    border_radius=Theme.R_SM,
                    bgcolor=Theme.CARD_HI,
                    border=ft.Border.all(1, Theme.STROKE),
                    ink=True,
                    on_click=lambda event, selected=uid: self.controller.run_favorite(
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
        self.product_name.value = self._t("app.name")
        self.device_selector.label = self._t("tray.target")
        self.settings_button.tooltip = self._t("quick.open_settings")
        self.target_title.value = self._t("tray.target")
        self.individual.content = self._t("routines.target.single")
        self.all_lights.content = self._t("tray.all_lights")
        self.power_title.value = self._t("home.master")
        self.power_on.content = self._t("home.on")
        self.power_off.content = self._t("home.off")
        self.favorites_title.value = self._t("quick.favorites")
        self.view_all.content = self._t("color_studio.view_all")

        set_language = getattr(self.color_adapter, "set_language", None)
        if callable(set_language):
            set_language(language)
        if self._snapshot:
            self.update_snapshot(self._snapshot)
        elif mounted(self):
            supdate(self)


__all__ = ["QuickPanelView"]
