from __future__ import annotations

import time
from typing import Any
import flet as ft

from config.favorites_manager import FavoritesManager
from localization import LocalizationManager
from ui.components.target_selector import TargetSelector
from ui.responsive import PANEL_BREAKPOINTS, Viewport
from ui.theme import Theme, mounted, supdate

class _Throttle:
    def __init__(self, interval_sec: float) -> None:
        self.interval = max(0.01, float(interval_sec))
        self.last_run = 0.0

    def allow(self) -> bool:
        now = time.monotonic()
        if now - self.last_run >= self.interval:
            self.last_run = now
            return True
        return False

class LocalEditGuard:
    def __init__(self, ttl_sec: float = 1.0) -> None:
        self.ttl = ttl_sec
        self.expiry = 0.0

    def lock(self) -> None:
        self.expiry = time.monotonic() + self.ttl

    def is_locked(self) -> bool:
        return time.monotonic() < self.expiry

class HomePanel(ft.Column):
    """Panel de inicio principal con selección por chips, control maestro y paleta rápida."""

    def __init__(self, wiz: Any, *, i18n: Any = None) -> None:
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=16, expand=True)
        self.wiz = wiz
        self.i18n = i18n or LocalizationManager(preference="es")
        self._last_state: dict[str, Any] = {}
        self.is_on = False
        self._bri_throttle = _Throttle(0.065)
        self._bri_guard = LocalEditGuard(1.05)
        self.favorites = FavoritesManager()
        self._viewport = Viewport(900, 720)
        self._build()

    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def _card(self, content: ft.Control, padding: int = 16) -> ft.Container:
        return ft.Container(
            content=content,
            padding=padding,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )

    def _build(self) -> None:
        # 1. Target Selector por Chips
        self.target_selector = TargetSelector(self.wiz, i18n=self.i18n)

        # 2. Tarjeta Master ON / OFF
        self.master_icon = ft.Icon(ft.Icons.POWER_OFF_ROUNDED, size=32, color=ft.Colors.WHITE)
        self.master_label = ft.Text(self._t("home.off"), size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.master_text = ft.Column(
            [
                ft.Text(self._t("home.master"), color=ft.Colors.WHITE70, size=12),
                self.master_label,
            ],
            spacing=2,
        )
        self.master_icon_box = ft.Container(
            content=self.master_icon,
            width=54,
            height=54,
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
            alignment=ft.Alignment.CENTER,
        )
        self.master_card = ft.Container(
            content=ft.Row(
                [
                    self.master_icon_box,
                    self.master_text,
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.TOUCH_APP_ROUNDED, color=ft.Colors.WHITE70, size=20),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=20,
            border_radius=Theme.R_LG,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[Theme.CARD_HI, Theme.CARD],
            ),
            on_click=self._toggle_master,
            ink=True,
            animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
        )

        # 3. Slider de Brillo
        self.bri_value = ft.Text(
            self._t("common.percent_value", value=100),
            size=14,
            weight=ft.FontWeight.BOLD,
            color=Theme.TEXT,
        )
        self.bri_slider = ft.Slider(
            min=10,
            max=100,
            value=100,
            divisions=18,
            active_color=Theme.ACCENT,
            thumb_color=ft.Colors.WHITE,
            on_change=self._on_brightness,
            expand=True,
        )
        bri_card = self._card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.BRIGHTNESS_6_ROUNDED, color=Theme.ACCENT, size=18),
                                    ft.Text(self._t("home.brightness_section"), style=Theme.LABEL),
                                ],
                                spacing=8,
                            ),
                            self.bri_value,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.bri_slider,
                ],
                spacing=6,
            )
        )

        # 4. Colores Rápidos
        self.color_cards = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=10,
            run_spacing=10,
            controls=[
                self._color_chip("Rojo", "#EF4444"),
                self._color_chip("Verde", "#22C55E"),
                self._color_chip("Azul", "#3B82F6"),
                self._color_chip("Amarillo", "#EAB308"),
                self._color_chip("Morado", "#A855F7"),
                self._color_chip("Cian", "#06B6D4"),
                self._color_chip("Cálido", 2700, is_kelvin=True),
                self._color_chip("Neutro", 4000, is_kelvin=True),
                self._color_chip("Frío", 6500, is_kelvin=True),
            ],
        )

        # 5. Escenas y Acciones Rápidas
        quick_actions = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=10,
            run_spacing=10,
            controls=[
                self._quick_action("Cine", ft.Icons.MOVIE_ROUNDED, "#8B5CF6", lambda: self._apply_scene(18)),
                self._quick_action("Lectura", ft.Icons.MENU_BOOK_ROUNDED, "#F59E0B", lambda: self._apply_white(4000)),
                self._quick_action("Relax", ft.Icons.SPA_ROUNDED, "#10B981", lambda: self._apply_scene(16)),
                self._quick_action("Fiesta", ft.Icons.CELEBRATION_ROUNDED, "#EC4899", lambda: self._apply_scene(4)),
            ],
        )

        self.controls = [
            self.target_selector,
            self.master_card,
            bri_card,
            ft.Text(self._t("home.color_section"), style=Theme.LABEL),
            self.color_cards,
            ft.Text(self._t("home.quick_section"), style=Theme.LABEL),
            quick_actions,
        ]

    def _color_chip(self, name: str, value: Any, *, is_kelvin: bool = False) -> ft.Container:
        preview_color = "#FFA94D" if is_kelvin and value == 2700 else (
            "#FFE8D6" if is_kelvin and value == 4000 else (
                "#D0EBFF" if is_kelvin else str(value)
            )
        )
        return ft.Container(
            col={"xs": 4, "sm": 3, "md": 2.4, "lg": 1.33},
            height=72,
            padding=8,
            border_radius=Theme.R_SM,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column(
                [
                    ft.Container(
                        width=28,
                        height=28,
                        border_radius=14,
                        bgcolor=preview_color,
                    ),
                    ft.Text(
                        name,
                        color=Theme.TEXT,
                        size=11,
                        weight=ft.FontWeight.W_500,
                        no_wrap=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            on_click=lambda e: self._apply_white(value) if is_kelvin else self._apply_color(value),
            ink=True,
        )

    def _quick_action(self, name: str, icon: str, color: str, action: Any) -> ft.Container:
        return ft.Container(
            col={"xs": 6, "sm": 3},
            height=54,
            padding=ft.Padding(12, 12, 12, 12),
            border_radius=Theme.R_SM,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [
                    ft.Icon(icon, color=color, size=20),
                    ft.Text(name, color=Theme.TEXT, size=12, weight=ft.FontWeight.W_500),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            on_click=lambda e: action(),
            ink=True,
        )

    def _toggle_master(self, e: Any) -> None:
        self.is_on = not self.is_on
        if hasattr(self.wiz, "turn_on") and hasattr(self.wiz, "turn_off"):
            if self.is_on:
                self.wiz.turn_on()
            else:
                self.wiz.turn_off()
        self._update_master_ui()

    def _update_master_ui(self) -> None:
        if self.is_on:
            self.master_label.value = self._t("home.on")
            self.master_icon.name = ft.Icons.LIGHTBULB_ROUNDED
            self.master_card.gradient = ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[Theme.ACCENT, Theme.ACCENT + "80"],
            )
        else:
            self.master_label.value = self._t("home.off")
            self.master_icon.name = ft.Icons.POWER_OFF_ROUNDED
            self.master_card.gradient = ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[Theme.CARD_HI, Theme.CARD],
            )
        if mounted(self.master_card):
            supdate(self.master_card)

    def _on_brightness(self, e: Any) -> None:
        val = int(e.control.value)
        self.bri_value.value = self._t("common.percent_value", value=val)
        if mounted(self.bri_value):
            supdate(self.bri_value)

        if self._bri_throttle.allow() and hasattr(self.wiz, "set_brightness"):
            self.wiz.set_brightness(val)

    def _apply_color(self, hex_color: str) -> None:
        if hasattr(self.wiz, "set_color"):
            self.wiz.set_color(hex_color)

    def _apply_white(self, temp_kelvin: int) -> None:
        if hasattr(self.wiz, "set_white"):
            self.wiz.set_white(int(temp_kelvin))

    def _apply_scene(self, scene_id: int) -> None:
        if hasattr(self.wiz, "set_scene"):
            self.wiz.set_scene(int(scene_id))

    def sync_state(self, state: dict[str, Any] | None = None) -> None:
        if state is None and hasattr(self.wiz, "get_state"):
            state = self.wiz.get_state()
        if not isinstance(state, dict):
            return

        self._last_state = state
        self.is_on = bool(state.get("state", False))
        dimming = state.get("dimming")

        if dimming is not None and not self._bri_guard.is_locked():
            bri_val = max(10, min(100, int(dimming)))
            self.bri_slider.value = bri_val
            self.bri_value.value = self._t("common.percent_value", value=bri_val)

        self._update_master_ui()
        if hasattr(self.target_selector, "refresh"):
            self.target_selector.refresh()

        if mounted(self):
            supdate(self)

    def set_language(self, language: str | None = None) -> None:
        if hasattr(self.target_selector, "set_language"):
            self.target_selector.set_language(language)
        self.sync_state(self._last_state)

    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        self._viewport = Viewport(max(280.0, float(width)), max(320.0, float(height)))
        if hasattr(self.target_selector, "set_viewport"):
            self.target_selector.set_viewport(width, height, update=False)
        if update and mounted(self):
            supdate(self)
