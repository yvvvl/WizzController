from __future__ import annotations

from typing import Any

import flet as ft

from ui.theme import Theme, mounted, supdate


class ColorStudioQuickAdapter(ft.Column):
    """Mount compact views while Color Studio retains behavior ownership."""

    def __init__(self, color_panel: Any, *, i18n: Any) -> None:
        super().__init__(spacing=10)
        self.color_panel = color_panel
        self.i18n = i18n
        self.mode = "color"

        self.mode_buttons = {
            "color": self._mode_button("color", ft.Icons.PALETTE_ROUNDED),
            "white": self._mode_button("white", ft.Icons.LIGHT_MODE_ROUNDED),
        }
        self.mode_selector = ft.Container(
            content=ft.Row(
                list(self.mode_buttons.values()),
                spacing=6,
            ),
            padding=4,
            border_radius=Theme.R_MD,
            bgcolor=Theme.SURFACE,
            border=ft.Border.all(1, Theme.STROKE),
        )
        self.mode_host = ft.Container()
        self.brightness_host = ft.Container(
            content=self.color_panel.brightness_card,
        )
        self.apply_host = ft.Container(
            content=self.color_panel.apply_row,
        )
        self.controls = [
            self.mode_selector,
            self.mode_host,
            self.brightness_host,
            self.apply_host,
        ]
        initial_mode = (
            "white"
            if getattr(self.color_panel, "view_mode", "color") == "white"
            else "color"
        )
        self._mount_mode(initial_mode, update=False)

    def _t(self, key: str, **values: Any) -> str:
        return self.i18n.translate(key, **values)

    def _mode_button(self, mode: str, icon: Any) -> ft.Container:
        key = "color_studio.color" if mode == "color" else "color_studio.white"
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, size=16),
                    ft.Text(self._t(key), size=12, weight=ft.FontWeight.W_600),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
            ),
            expand=True,
            padding=ft.Padding.symmetric(horizontal=12, vertical=9),
            border_radius=Theme.R_SM,
            ink=True,
            on_click=lambda event, selected=mode: self.set_mode(selected),
        )

    def _color_tree(self) -> ft.Column:
        return ft.Column(
            [
                self.color_panel.color_section,
                self.color_panel.precise_section,
            ],
            spacing=12,
        )

    def set_mode(self, mode: str, *, update: bool = True) -> None:
        if mode not in {"color", "white"}:
            raise ValueError(f"Unsupported Color Studio mode: {mode}")

        select_view = getattr(self.color_panel, "_select_view", None)
        if callable(select_view):
            select_view(mode, update=False)
        self._mount_mode(mode, update=update)

    def _mount_mode(self, mode: str, *, update: bool = True) -> None:
        self.mode = mode
        self.mode_host.content = (
            self._color_tree()
            if mode == "color"
            else self.color_panel.white_section
        )
        self._refresh_mode_buttons()
        if update and mounted(self):
            supdate(self)

    def _refresh_mode_buttons(self) -> None:
        for mode, button in self.mode_buttons.items():
            selected = mode == self.mode
            button.bgcolor = (
                ft.Colors.with_opacity(0.20, Theme.PRIMARY)
                if selected
                else "transparent"
            )
            button.border = ft.Border.all(
                1,
                Theme.PRIMARY if selected else "transparent",
            )
            row = button.content
            if isinstance(row, ft.Row):
                for control in row.controls:
                    if isinstance(control, (ft.Text, ft.Icon)):
                        control.color = Theme.TEXT if selected else Theme.MUTED

    def set_language(self, language: str | None = None) -> None:
        set_language = getattr(self.color_panel, "set_language", None)
        if callable(set_language):
            set_language(language)

        for mode, button in self.mode_buttons.items():
            row = button.content
            if not isinstance(row, ft.Row) or len(row.controls) < 2:
                continue
            label = row.controls[1]
            if isinstance(label, ft.Text):
                key = (
                    "color_studio.color"
                    if mode == "color"
                    else "color_studio.white"
                )
                label.value = self._t(key)

        self.brightness_host.content = self.color_panel.brightness_card
        self.apply_host.content = self.color_panel.apply_row
        self._mount_mode(self.mode, update=False)
        if mounted(self):
            supdate(self)

    def set_viewport(self, width: float, height: float) -> None:
        set_viewport = getattr(self.color_panel, "set_viewport", None)
        if callable(set_viewport):
            set_viewport(width, height)

    def sync_state(self, state: dict[str, Any]) -> None:
        sync_state = getattr(self.color_panel, "sync_state", None)
        if callable(sync_state):
            sync_state(dict(state or {}))
        studio_mode = getattr(self.color_panel, "view_mode", self.mode)
        adapter_mode = "white" if studio_mode == "white" else "color"
        if adapter_mode != self.mode:
            self._mount_mode(adapter_mode)


__all__ = ["ColorStudioQuickAdapter"]
