from __future__ import annotations

import random
import time
from typing import Any

import flet as ft

from config.config_manager import ConfigManager
from config.favorites_manager import FavoritesManager
from ui.color_utils import (
    hex_to_rgb,
    hsv_to_rgb,
    kelvin_to_hex,
    kelvin_to_percent,
    percent_to_kelvin,
    pointer_to_ratio,
    ratio_to_thumb_offset,
    rgb_to_hex,
    rgb_to_hsv,
)
from ui.interaction import DragPositionTracker, LocalEditGuard
from ui.responsive import PANEL_BREAKPOINTS, Viewport, clamp_size, quantize_down
from ui.theme import Theme, mounted, supdate

FIELD = 300
HUE_W = 300
HUE_H = 28
FIELD_THUMB = 24
HUE_THUMB = 18
EO = ft.AnimationCurve.EASE_OUT
RECENT_LIMIT = 12

QUICK_SWATCHES = [
    ("Rojo", "#ff0000"),
    ("Naranjo", "#ff7f00"),
    ("Ámbar", "#ffb000"),
    ("Amarillo", "#ffd000"),
    ("Lima", "#b6ff00"),
    ("Verde", "#00ff40"),
    ("Menta", "#00ffb3"),
    ("Cian", "#00d5ff"),
    ("Azul", "#0055ff"),
    ("Índigo", "#3b38ff"),
    ("Violeta", "#7f00ff"),
    ("Magenta", "#ff00cc"),
    ("Rosa", "#ff4fa3"),
    ("Blanco RGB", "#ffffff"),
]

WHITE_PRESETS = [
    (2200, "Vela", "#ff9a3c", "muy cálido"),
    (2700, "Cálido", "#ffc187", "relax"),
    (3500, "Hogar", "#ffe0b8", "suave"),
    (4000, "Neutro", "#fff1df", "diario"),
    (5000, "Día", "#fffdf7", "foco"),
    (6500, "Frío", "#d6ecff", "energía"),
]

MOOD_PALETTES = [
    ("Cyberpunk", ["#00e5ff", "#ff00cc", "#7f00ff", "#0055ff", "#ff2d75"]),
    ("Atardecer", ["#ff3b30", "#ff7f00", "#ffd000", "#ff4fa3", "#7f00ff"]),
    ("Océano", ["#003bff", "#0077ff", "#00d5ff", "#00ffb3", "#b6ff00"]),
    ("Bosque", ["#00ff40", "#34d399", "#b6ff00", "#ffb000", "#ff7f00"]),
    ("Aurora", ["#00ffb3", "#00d5ff", "#7f00ff", "#ff00cc", "#ffffff"]),
    ("Cine", ["#ff9a3c", "#ff4f2f", "#3b38ff", "#141a2e", "#fff1df"]),
]


class _Throttle:
    def __init__(self, interval: float = 0.065) -> None:
        self.interval = float(interval)
        self.last = 0.0

    def ready(self, final: bool = False) -> bool:
        now = time.monotonic()
        if final or now - self.last >= self.interval:
            self.last = now
            return True
        return False


class ColorPanel(ft.Column):
    """Color Studio: picker visual, blancos Kelvin, paletas y favoritos.

    La UI evita assets externos para no depender del loader de Flet dev. Todo el
    picker está construido con controles nativos livianos: gradientes, Stack y
    GestureDetector.
    """

    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.favorites = FavoritesManager()
        self.config = ConfigManager()

        self.hue = 0.0
        self.sat = 100.0
        self.val = 100.0
        self.dimming = 100
        self.temp_kelvin = 4000
        self._last_mode = "rgb"

        self._color_throttle = _Throttle(0.060)
        self._bri_throttle = _Throttle(0.065)
        self._white_throttle = _Throttle(0.075)
        self._bri_guard = LocalEditGuard(1.05)
        self._white_guard = LocalEditGuard(1.10)
        self._color_guard = LocalEditGuard(1.00)

        self._viewport = Viewport(900, 720)
        self._field_size = float(FIELD)
        self._hue_width = float(HUE_W)
        self._field_tracker = DragPositionTracker(self._field_size, self._field_size)
        self._hue_tracker = DragPositionTracker(self._hue_width, HUE_H)
        self._cards: list[ft.Container] = []
        self._build()

    # ------------------------------------------------------------------ #
    # Construcción UI
    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        self.live_switch = ft.Switch(
            value=self._picker_pref("apply_live", True),
            active_color=Theme.PRIMARY,
            on_change=self._live_changed,
        )

        title_block = ft.Column(
            [
                ft.Text("Color Studio", style=Theme.H1),
                ft.Text(
                    "Picker HSV, paletas inteligentes, blancos Kelvin y favoritos rápidos",
                    color=Theme.MUTED,
                    size=13,
                ),
            ],
            spacing=2,
        )
        self.header_actions = ft.Row(
            [
                ft.OutlinedButton(
                    "Sorpresa",
                    icon=ft.Icons.AUTO_AWESOME_ROUNDED,
                    style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
                    on_click=lambda e: self._surprise_color(),
                ),
                ft.ElevatedButton(
                    "Guardar",
                    icon=ft.Icons.STAR_ROUNDED,
                    bgcolor=Theme.PRIMARY,
                    color="white",
                    on_click=lambda e: self._save_current_favorite(),
                ),
            ],
            spacing=10,
            run_spacing=8,
            wrap=True,
            alignment=ft.MainAxisAlignment.END,
        )
        self.header = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=title_block, col={"xs": 12, "md": 7}),
                ft.Container(content=self.header_actions, col={"xs": 12, "md": 5}, alignment=ft.Alignment.CENTER_RIGHT),
            ],
        )

        self.preview_icon = ft.Container(
            width=54,
            height=54,
            border_radius=18,
            bgcolor=ft.Colors.with_opacity(0.22, "white"),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white")),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color="white", size=28),
        )
        self.preview_title = ft.Text("RGB #FF0000", color="white", size=20, weight=ft.FontWeight.BOLD)
        self.preview_subtitle = ft.Text("H 0° · S 100% · V 100%", color=ft.Colors.with_opacity(0.78, "white"), size=12)
        self.preview_mode = self._mini_metric("Modo", "RGB", "#ffffff")
        self.preview_hex = self._mini_metric("HEX", "#FF0000", "#ffffff")
        self.preview_rgb = self._mini_metric("RGB", "255 · 0 · 0", "#ffffff")
        self.preview_bri = self._mini_metric("Brillo", "100%", "#ffffff")
        self.preview_intro = ft.Row(
            [
                self.preview_icon,
                ft.Column([self.preview_title, self.preview_subtitle], spacing=4, expand=True),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
        )
        self.preview_metrics = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=8,
            controls=[
                ft.Container(content=self.preview_mode, col={"xs": 6, "sm": 3}),
                ft.Container(content=self.preview_hex, col={"xs": 6, "sm": 3}),
                ft.Container(content=self.preview_rgb, col={"xs": 6, "sm": 3}),
                ft.Container(content=self.preview_bri, col={"xs": 6, "sm": 3}),
            ],
        )
        self.preview = ft.Container(
            padding=22,
            border_radius=Theme.R_LG,
            gradient=self._preview_gradient(),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.24, "white")),
            shadow=Theme.GLOW(self._hex()),
            animate=ft.Animation(110, EO),
            content=ft.Column([self.preview_intro, self.preview_metrics], spacing=14),
        )

        picker_card = self._color_picker_card()
        precision_card = self._precision_card()
        brightness_card = self._brightness_card()
        white_card = self._white_card()
        harmony_card = self._harmony_card()
        quick_card = self._quick_colors_card()
        palettes_card = self._palettes_card()
        favorites_card = self._favorites_card()

        self.left_column = ft.Container(
            content=ft.Column([picker_card, precision_card], spacing=18),
            col={"xs": 12, "lg": 5},
        )
        self.right_column = ft.Container(
            content=ft.Column([brightness_card, white_card, harmony_card, quick_card, palettes_card, favorites_card], spacing=18),
            col={"xs": 12, "lg": 7},
        )
        self.layout = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=18,
            run_spacing=18,
            controls=[self.left_column, self.right_column],
        )

        self.controls = [self.header, self.preview, self.layout]
        self._render_harmony()
        self._render_recent()
        self._render_favorites()
        self._refresh_color_controls(update=False, render_dynamic=False)
        self._refresh_brightness_controls(update=False)
        self._refresh_white_controls(update=False)
        self._place_thumbs(update=False)

    def _color_picker_card(self) -> ft.Container:
        self.color_field_bg = ft.Container(
            width=self._field_size,
            height=self._field_size,
            border_radius=Theme.R_LG,
            bgcolor=self._hue_hex(),
        )
        self.field_white_layer = ft.Container(
            width=self._field_size,
            height=self._field_size,
            border_radius=Theme.R_LG,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, 0),
                end=ft.Alignment(1, 0),
                colors=["white", ft.Colors.with_opacity(0.0, "white")],
            ),
        )
        self.field_black_layer = ft.Container(
            width=self._field_size,
            height=self._field_size,
            border_radius=Theme.R_LG,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(0, -1),
                end=ft.Alignment(0, 1),
                colors=[ft.Colors.with_opacity(0.0, "black"), "black"],
            ),
        )
        self.field_thumb = ft.Container(
            width=FIELD_THUMB,
            height=FIELD_THUMB,
            border_radius=FIELD_THUMB / 2,
            bgcolor=self._hex(),
            border=ft.Border.all(3, "white"),
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.75, "black")),
        )
        self.field_detector = ft.GestureDetector(
            width=self._field_size,
            height=self._field_size,
            drag_interval=18,
            on_pan_start=self._on_field_start,
            on_pan_update=self._on_field_update,
            on_pan_end=self._on_field_end,
            on_pan_cancel=lambda e: self._field_tracker.cancel(),
            on_tap_up=self._on_field_tap,
        )
        self.field_stack = ft.Stack(
            width=self._field_size,
            height=self._field_size,
            controls=[
                self.color_field_bg,
                self.field_white_layer,
                self.field_black_layer,
                self.field_thumb,
                self.field_detector,
            ],
        )

        self.hue_thumb = ft.Container(
            width=HUE_THUMB,
            height=HUE_THUMB,
            border_radius=HUE_THUMB / 2,
            bgcolor=self._hue_hex(),
            border=ft.Border.all(3, "white"),
            shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.65, "black")),
        )
        self.hue_track = ft.Container(
            width=self._hue_width,
            height=HUE_H,
            border_radius=14,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, 0),
                end=ft.Alignment(1, 0),
                colors=["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff", "#ff0000"],
            ),
        )
        self.hue_detector = ft.GestureDetector(
            width=self._hue_width,
            height=HUE_H,
            drag_interval=16,
            on_pan_start=self._on_hue_start,
            on_pan_update=self._on_hue_update,
            on_pan_end=self._on_hue_end,
            on_pan_cancel=lambda e: self._hue_tracker.cancel(),
            on_tap_up=self._on_hue_tap,
        )
        self.hue_stack = ft.Stack(
            width=self._hue_width,
            height=HUE_H,
            controls=[self.hue_track, self.hue_thumb, self.hue_detector],
        )

        self.hsv_label = ft.Text("H 0° · S 100% · V 100%", color=Theme.MUTED, size=12)
        live_hint = ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.09, Theme.PRIMARY),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.22, Theme.PRIMARY)),
            content=ft.Row(
                [ft.Text("Aplicar en vivo", color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600), self.live_switch],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.END,
            ),
        )
        self.picker_meta = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=self.hsv_label, col={"xs": 12, "sm": 5}, alignment=ft.Alignment.CENTER_LEFT),
                ft.Container(content=live_hint, col={"xs": 12, "sm": 7}, alignment=ft.Alignment.CENTER_RIGHT),
            ],
        )

        return self._card(
            ft.Column(
                [
                    self._section_header("PICKER HSV", "arrastra el cuadro y la barra de matiz"),
                    ft.Row([self.field_stack], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row([self.hue_stack], alignment=ft.MainAxisAlignment.CENTER),
                    self.picker_meta,
                    ft.Row(
                        [self._pill_button("Aplicar", ft.Icons.CHECK_ROUNDED, lambda e: self._apply_current_color())],
                        spacing=10,
                        wrap=True,
                    ),
                ],
                spacing=14,
            )
        )

    def _precision_card(self) -> ft.Container:
        r, g, b = self._rgb()
        self.hex_field = self._text_field("HEX", self._hex(), self._on_hex)
        self.r_field = self._text_field("R", str(r), self._on_rgb_fields)
        self.g_field = self._text_field("G", str(g), self._on_rgb_fields)
        self.b_field = self._text_field("B", str(b), self._on_rgb_fields)
        self.precision_apply = ft.IconButton(
            ft.Icons.CHECK_ROUNDED,
            tooltip="Aplicar valores",
            icon_color=Theme.PRIMARY,
            on_click=self._on_precision_apply,
        )
        self.recent_row = ft.ResponsiveRow(breakpoints=PANEL_BREAKPOINTS, spacing=8, run_spacing=8)
        fields = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=self.hex_field, col={"xs": 12, "sm": 6, "md": 4}),
                ft.Container(content=self.r_field, col={"xs": 4, "sm": 2}),
                ft.Container(content=self.g_field, col={"xs": 4, "sm": 2}),
                ft.Container(content=self.b_field, col={"xs": 4, "sm": 2}),
                ft.Container(content=self.precision_apply, col={"xs": 12, "sm": 12, "md": 2}, alignment=ft.Alignment.CENTER),
            ],
        )
        return self._card(
            ft.Column(
                [
                    self._section_header("CONTROL PRECISO", "HEX, RGB y últimos colores"),
                    fields,
                    self.recent_row,
                ],
                spacing=12,
            )
        )

    def _brightness_card(self) -> ft.Container:
        self.bri_value = ft.Text("100%", size=13, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
        self.bri_slider = ft.Slider(
            min=10,
            max=100,
            value=100,
            divisions=18,
            active_color=Theme.ACCENT,
            thumb_color="white",
            on_change=self._on_brightness,
            on_change_end=self._on_brightness_end,
            expand=True,
        )
        quick = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=8,
            controls=[
                ft.Container(content=self._tiny_choice("25", lambda e: self._set_brightness(25)), col={"xs": 6, "sm": 3}),
                ft.Container(content=self._tiny_choice("50", lambda e: self._set_brightness(50)), col={"xs": 6, "sm": 3}),
                ft.Container(content=self._tiny_choice("75", lambda e: self._set_brightness(75)), col={"xs": 6, "sm": 3}),
                ft.Container(content=self._tiny_choice("100", lambda e: self._set_brightness(100)), col={"xs": 6, "sm": 3}),
            ],
        )
        heading = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=self._section_header("BRILLO", "dimming real WiZ, separado del color RGB"), col={"xs": 9}),
                ft.Container(content=self.bri_value, col={"xs": 3}, alignment=ft.Alignment.CENTER_RIGHT),
            ],
        )
        return self._card(ft.Column([heading, self.bri_slider, quick], spacing=8))

    def _white_card(self) -> ft.Container:
        lo, hi = self._kelvin_range()
        self.temp_kelvin = 4000 if lo <= 4000 <= hi else round((lo + hi) / 2)
        self.white_value = ft.Text(self._white_label(), size=13, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
        self.white_slider = ft.Slider(
            min=0,
            max=100,
            value=self._kelvin_to_pct(self.temp_kelvin),
            divisions=100,
            active_color=Theme.WARNING,
            thumb_color="white",
            on_change=self._on_white_slider,
            on_change_end=self._on_white_slider_end,
            expand=True,
        )
        self.white_presets_row = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=10,
            run_spacing=10,
            controls=[self._white_preset(k, label, col, sub) for k, label, col, sub in WHITE_PRESETS],
        )
        heading = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=self._section_header("BLANCOS KELVIN", f"rango detectado: {lo}K – {hi}K"), col={"xs": 8, "sm": 9}),
                ft.Container(content=self.white_value, col={"xs": 4, "sm": 3}, alignment=ft.Alignment.CENTER_RIGHT),
            ],
        )
        return self._card(ft.Column([heading, self.white_slider, self.white_presets_row], spacing=10))

    def _harmony_card(self) -> ft.Container:
        self.harmony_row = ft.ResponsiveRow(breakpoints=PANEL_BREAKPOINTS, spacing=10, run_spacing=10)
        return self._card(
            ft.Column(
                [
                    self._section_header("PALETA INTELIGENTE", "armonías generadas desde el color actual"),
                    self.harmony_row,
                ],
                spacing=12,
            )
        )

    def _quick_colors_card(self) -> ft.Container:
        return self._card(
            ft.Column(
                [
                    self._section_header("COLORES RÁPIDOS", "colores limpios para acciones instantáneas"),
                    ft.ResponsiveRow(breakpoints=PANEL_BREAKPOINTS, spacing=10, run_spacing=10, controls=[self._swatch(name, color) for name, color in QUICK_SWATCHES]),
                ],
                spacing=12,
            )
        )

    def _palettes_card(self) -> ft.Container:
        return self._card(
            ft.Column(
                [
                    self._section_header("MOODS", "mini paletas listas para cine, ambiente o neón"),
                    ft.ResponsiveRow(breakpoints=PANEL_BREAKPOINTS, spacing=10, run_spacing=10, controls=[self._mood_palette(name, colors) for name, colors in MOOD_PALETTES]),
                ],
                spacing=12,
            )
        )

    def _favorites_card(self) -> ft.Container:
        self.fav_row = ft.ResponsiveRow(breakpoints=PANEL_BREAKPOINTS, spacing=10, run_spacing=10)
        heading = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=self._section_header("FAVORITOS", "atajos guardados desde esta pantalla"), col={"xs": 8, "sm": 9}),
                ft.Container(
                    content=ft.TextButton("Ver todos", icon=ft.Icons.OPEN_IN_NEW_ROUNDED, on_click=lambda e: self._go_favorites()),
                    col={"xs": 4, "sm": 3},
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
        )
        return self._card(ft.Column([heading, self.fav_row], spacing=10))

    # ------------------------------------------------------------------ #
    # Componentes pequeños
    # ------------------------------------------------------------------ #
    def _card(self, content, padding: int = 20) -> ft.Container:
        card = ft.Container(
            content=content,
            padding=padding,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )
        self._cards.append(card)
        return card

    def _section_header(self, title: str, subtitle: str = "") -> ft.Column:
        controls = [ft.Text(title, style=Theme.LABEL)]
        if subtitle:
            controls.append(ft.Text(subtitle, color=Theme.FAINT, size=11))
        return ft.Column(controls, spacing=1)

    def _text_field(self, label: str, value: str, submit_handler) -> ft.TextField:
        return ft.TextField(
            label=label,
            value=value,
            text_size=13,
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            focused_border_color=Theme.PRIMARY,
            dense=True,
            on_submit=submit_handler,
        )

    def _mini_metric(self, label: str, value: str, border_color: str) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=7),
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.18, "black"),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.28, border_color)),
            content=ft.Column(
                [
                    ft.Text(label, color=ft.Colors.with_opacity(0.66, "white"), size=9, weight=ft.FontWeight.BOLD),
                    ft.Text(value, color="white", size=12, weight=ft.FontWeight.W_600),
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _set_metric(self, metric: ft.Container, label: str, value: str) -> None:
        try:
            col = metric.content
            col.controls[0].value = label
            col.controls[1].value = value
        except Exception:
            pass

    def _pill_button(self, text: str, icon, on_click) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=9),
            border_radius=16,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row([ft.Icon(icon, color=Theme.TEXT, size=16), ft.Text(text, color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600)], spacing=7),
            on_click=on_click,
            ink=True,
        )

    def _tiny_choice(self, text: str, on_click) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=13, vertical=7),
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.09, Theme.ACCENT),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.22, Theme.ACCENT)),
            content=ft.Text(f"{text}%", color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
            alignment=ft.Alignment.CENTER,
            on_click=on_click,
            ink=True,
        )

    def _swatch(self, name: str, color: str, *, col: dict[str, Any] | None = None) -> ft.Container:
        return ft.Container(
            col=col or {"xs": 3, "sm": 2, "md": 2},
            height=42,
            border_radius=21,
            bgcolor=color,
            tooltip=name,
            border=ft.Border.all(2, ft.Colors.with_opacity(0.28, "white")),
            shadow=ft.BoxShadow(blur_radius=14, color=ft.Colors.with_opacity(0.18, color)),
            on_click=lambda e, h=color: self._pick_hex(h),
            ink=True,
        )

    def _white_preset(self, kelvin: int, label: str, col: str, subtitle: str) -> ft.Container:
        lo, hi = self._kelvin_range()
        disabled = kelvin < lo or kelvin > hi
        return ft.Container(
            col={"xs": 6, "sm": 4, "md": 3, "lg": 2},
            height=78,
            padding=10,
            border_radius=Theme.R_SM,
            bgcolor=ft.Colors.with_opacity(0.12, col),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.44, col)),
            opacity=0.42 if disabled else 1,
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.LIGHT_MODE_ROUNDED, color=col, size=18),
                    ft.Text(label, size=11, color=Theme.TEXT, weight=ft.FontWeight.W_600),
                    ft.Text(f"{kelvin}K · {subtitle}", size=9, color=Theme.FAINT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            ),
            on_click=(None if disabled else lambda e, kk=kelvin: self._set_white_kelvin(kk)),
            ink=not disabled,
        )

    def _mood_palette(self, name: str, colors: list[str]) -> ft.Container:
        chips = [
            ft.Container(
                width=26,
                height=26,
                border_radius=13,
                bgcolor=h,
                border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white")),
                tooltip=h.upper(),
                on_click=lambda e, hx=h: self._pick_hex(hx),
                ink=True,
            )
            for h in colors
        ]
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4},
            padding=12,
            border_radius=Theme.R_SM,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column([ft.Text(name, color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600), ft.Row(chips, spacing=6)], spacing=8),
        )

    def _harmony_chip(self, name: str, color: str) -> ft.Container:
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4},
            height=58,
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            border_radius=Theme.R_SM,
            bgcolor=ft.Colors.with_opacity(0.11, color),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.38, color)),
            content=ft.Row(
                [
                    ft.Container(width=22, height=22, border_radius=11, bgcolor=color, border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white"))),
                    ft.Column(
                        [ft.Text(name, color=Theme.TEXT, size=11, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Text(color.upper(), color=Theme.FAINT, size=9)],
                        spacing=1,
                        expand=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=lambda e, h=color: self._pick_hex(h),
            ink=True,
        )

    def _fav_chip(self, fav: dict[str, Any]) -> ft.Container:
        ftype = fav.get("type")
        value = fav.get("value")
        color = str(value) if ftype == "rgb" else "#fbbf24" if ftype == "white" else "#8b5cf6"
        subtitle = str(value).upper() if ftype == "rgb" else f"{value}K" if ftype == "white" else "Escena"
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4},
            height=50,
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=14,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [
                    ft.Container(width=20, height=20, border_radius=10, bgcolor=color, border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white"))),
                    ft.Column(
                        [
                            ft.Text(fav.get("name", "Favorito"), color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(subtitle, color=Theme.FAINT, size=9, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=lambda e, f=fav: self._apply_favorite(f),
            ink=True,
        )

    # ------------------------------------------------------------------ #
    # Render dinámico
    # ------------------------------------------------------------------ #
    def _render_harmony(self) -> None:
        if not hasattr(self, "harmony_row"):
            return
        base = self.hue % 360.0
        items = [
            ("Base", base),
            ("Comp", base + 180),
            ("Análogo −", base - 32),
            ("Análogo +", base + 32),
            ("Triada A", base + 120),
            ("Triada B", base + 240),
        ]
        sat = max(35.0, min(100.0, self.sat))
        val = max(55.0, min(100.0, self.val))
        self.harmony_row.controls.clear()
        for label, hue in items:
            self.harmony_row.controls.append(self._harmony_chip(label, self._hsv_hex(hue, sat, val)))
        supdate(self.harmony_row)

    def _render_recent(self) -> None:
        if not hasattr(self, "recent_row"):
            return
        self.recent_row.controls.clear()
        recent = self._recent_colors()
        if not recent:
            self.recent_row.controls.append(ft.Text("Aún no hay recientes. Aplica un color y aparecerá aquí.", color=Theme.MUTED, size=12))
        else:
            for h in recent[:RECENT_LIMIT]:
                self.recent_row.controls.append(self._swatch(h.upper(), h, col={"xs": 2, "sm": 2, "md": 1}))
        supdate(self.recent_row)

    def _render_favorites(self) -> None:
        if not hasattr(self, "fav_row"):
            return
        self.favorites = FavoritesManager()
        favs = self.favorites.get_favorites()[:8]
        self.fav_row.controls.clear()
        if not favs:
            self.fav_row.controls.append(ft.Text("Sin favoritos todavía. Guarda un color o blanco actual.", color=Theme.MUTED, size=12))
        else:
            for fav in favs:
                self.fav_row.controls.append(self._fav_chip(fav))
        supdate(self.fav_row)

    # ------------------------------------------------------------------ #
    # Color math / estado local
    # ------------------------------------------------------------------ #
    def _rgb(self) -> tuple[int, int, int]:
        return hsv_to_rgb(self.hue, self.sat, self.val)

    def _hex(self) -> str:
        return rgb_to_hex(*self._rgb())

    def _hsv_hex(self, hue: float, sat: float, val: float) -> str:
        return rgb_to_hex(*hsv_to_rgb(hue, sat, val))

    def _hue_hex(self, hue: float | None = None) -> str:
        return self._hsv_hex(self.hue if hue is None else hue, 100, 100)

    def _kelvin_hex(self, kelvin: int | None = None) -> str:
        return kelvin_to_hex(self.temp_kelvin if kelvin is None else kelvin)

    def _display_hex(self) -> str:
        return self._kelvin_hex() if self._last_mode == "white" else self._hex()

    def _parse_hex(self, value: Any) -> tuple[int, int, int] | None:
        return hex_to_rgb(value)

    def _apply_rgb_to_local(self, r: int, g: int, b: int) -> None:
        hh, ss, vv = rgb_to_hsv(r, g, b)
        # En grises colorsys devuelve h=0. Mantener el hue previo hace que al subir
        # saturación el usuario vuelva al color que estaba explorando.
        if ss > 0.001:
            self.hue = min(359.999, hh)
        self.sat = ss
        self.val = vv

    def _kelvin_range(self) -> tuple[int, int]:
        try:
            lo, hi = self.wiz.get_kelvin_range()
            return int(lo), int(hi)
        except Exception:
            return 2200, 6500

    def _kelvin_to_pct(self, kelvin: int) -> int:
        lo, hi = self._kelvin_range()
        return kelvin_to_percent(kelvin, lo, hi)

    def _pct_to_kelvin(self, pct: int) -> int:
        lo, hi = self._kelvin_range()
        return percent_to_kelvin(pct, lo, hi)

    def _white_label(self) -> str:
        return f"{self._kelvin_to_pct(self.temp_kelvin)}% · {self.temp_kelvin}K"

    def _preview_gradient(self) -> ft.LinearGradient:
        h = self._display_hex()
        accent = self._kelvin_hex(self.temp_kelvin + 650) if self._last_mode == "white" else self._hsv_hex(self.hue + 34, max(70, self.sat), max(70, self.val))
        return ft.LinearGradient(
            begin=ft.Alignment(-1.0, -1.0),
            end=ft.Alignment(1.0, 1.0),
            colors=[h, ft.Colors.with_opacity(0.76, accent), "#111827"],
        )

    # ------------------------------------------------------------------ #
    # Preferencias Color Studio
    # ------------------------------------------------------------------ #
    def _picker_config(self) -> dict[str, Any]:
        cfg = self.config.get("color_picker", {})
        return dict(cfg) if isinstance(cfg, dict) else {}

    def _picker_pref(self, key: str, default: Any) -> Any:
        return self._picker_config().get(key, default)

    def _save_picker_pref(self, key: str, value: Any) -> None:
        cfg = self._picker_config()
        cfg[key] = value
        self.config.set("color_picker", cfg)

    def _recent_colors(self) -> list[str]:
        raw = self._picker_pref("recent", [])
        out: list[str] = []
        if isinstance(raw, list):
            for value in raw:
                rgb = self._parse_hex(value)
                if rgb:
                    h = "#{:02x}{:02x}{:02x}".format(*rgb)
                    if h not in out:
                        out.append(h)
        return out[:RECENT_LIMIT]

    def _remember_recent(self, hex_color: str) -> None:
        rgb = self._parse_hex(hex_color)
        if not rgb:
            return
        h = "#{:02x}{:02x}{:02x}".format(*rgb)
        recent = [x for x in self._recent_colors() if x != h]
        recent.insert(0, h)
        self._save_picker_pref("recent", recent[:RECENT_LIMIT])
        self._render_recent()

    # ------------------------------------------------------------------ #
    # Responsive / geometría del picker
    # ------------------------------------------------------------------ #
    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        viewport = Viewport(max(280.0, float(width)), max(320.0, float(height)))
        mode_changed = viewport.mode != self._viewport.mode
        self._viewport = viewport

        if viewport.wide:
            # En dos columnas el picker vive dentro del bloque 5/12.
            available = viewport.width * (5.0 / 12.0) - 58.0
        else:
            # En una columna ocupa todo el panel menos padding/bordes.
            available = viewport.width - (54.0 if viewport.compact else 70.0)
        # Redondear hacia abajo evita que el picker gane 2–4 px justo antes de
        # un breakpoint y desborde la card durante un resize lento.
        desired = float(max(220, quantize_down(clamp_size(available, 220.0, 360.0), 8)))
        geometry_changed = abs(desired - self._field_size) >= 1.0

        if geometry_changed:
            self._field_size = desired
            self._hue_width = desired
            self._apply_picker_geometry(update=False)

        if mode_changed:
            pad = 14 if viewport.compact else 18 if viewport.medium else 20
            for card in self._cards:
                card.padding = pad
            self.preview.padding = 16 if viewport.compact else 20 if viewport.medium else 22
            self.preview_title.size = 18 if viewport.compact else 20
            icon_size = 48 if viewport.compact else 54
            self.preview_icon.width = icon_size
            self.preview_icon.height = icon_size
            self.preview_icon.border_radius = 16 if viewport.compact else 18

        if update and (geometry_changed or mode_changed):
            supdate(self)

    def _apply_picker_geometry(self, *, update: bool = True) -> None:
        size = self._field_size
        hue_width = self._hue_width
        for control in (self.color_field_bg, self.field_white_layer, self.field_black_layer, self.field_detector, self.field_stack):
            control.width = size
            control.height = size
        self.hue_track.width = hue_width
        self.hue_detector.width = hue_width
        self.hue_stack.width = hue_width
        self._field_tracker.resize(size, size)
        self._hue_tracker.resize(hue_width, HUE_H)
        self._place_thumbs(update=False)
        if update:
            supdate(self.field_stack)
            supdate(self.hue_stack)

    # ------------------------------------------------------------------ #
    # UI refresh
    # ------------------------------------------------------------------ #
    def _place_thumbs(self, update: bool = True) -> None:
        # La posición visual y la lectura del cursor comparten exactamente el
        # mismo recorrido. Así 0% y 100% quedan accesibles sin salir del picker.
        if hasattr(self, "field_thumb"):
            self.field_thumb.left = ratio_to_thumb_offset(self.sat / 100.0, self._field_size, FIELD_THUMB)
            self.field_thumb.top = ratio_to_thumb_offset((100.0 - self.val) / 100.0, self._field_size, FIELD_THUMB)
        if hasattr(self, "hue_thumb"):
            self.hue_thumb.left = ratio_to_thumb_offset((self.hue % 360.0) / 359.999, self._hue_width, HUE_THUMB)
            self.hue_thumb.top = max(0, (HUE_H - HUE_THUMB) / 2)
        if update:
            supdate(self.field_thumb)
            supdate(self.hue_thumb)

    def _refresh_color_controls(self, update: bool = True, render_dynamic: bool = False) -> None:
        h = self._hex()
        display_h = self._display_hex()
        r, g, b = self._rgb()
        hue_color = self._hue_hex()

        if hasattr(self, "preview"):
            self.preview.gradient = self._preview_gradient()
            self.preview.shadow = Theme.GLOW(display_h)
            self.preview_title.value = f"{self._last_mode.upper()} {h.upper() if self._last_mode == 'rgb' else str(self.temp_kelvin) + 'K'}"
            self.preview_subtitle.value = f"H {round(self.hue)}° · S {round(self.sat)}% · V {round(self.val)}%" if self._last_mode == "rgb" else self._white_label()
            self.preview_icon.bgcolor = ft.Colors.with_opacity(0.24, "white")
            self._set_metric(self.preview_mode, "Modo", "RGB" if self._last_mode == "rgb" else "WHITE")
            self._set_metric(self.preview_hex, "HEX" if self._last_mode == "rgb" else "Kelvin", h.upper() if self._last_mode == "rgb" else f"{self.temp_kelvin}K")
            self._set_metric(self.preview_rgb, "RGB" if self._last_mode == "rgb" else "Blanco", f"{r} · {g} · {b}" if self._last_mode == "rgb" else f"{self._kelvin_to_pct(self.temp_kelvin)}% rango")
            self._set_metric(self.preview_bri, "Brillo", f"{self.dimming}%")

        if hasattr(self, "color_field_bg"):
            self.color_field_bg.bgcolor = hue_color
        if hasattr(self, "field_thumb"):
            self.field_thumb.bgcolor = h
        if hasattr(self, "hue_thumb"):
            self.hue_thumb.bgcolor = hue_color
        if hasattr(self, "hsv_label"):
            self.hsv_label.value = f"H {round(self.hue)}° · S {round(self.sat)}% · V {round(self.val)}%"
        if hasattr(self, "hex_field"):
            self.hex_field.value = h.upper()
        if hasattr(self, "r_field"):
            self.r_field.value = str(r)
            self.g_field.value = str(g)
            self.b_field.value = str(b)

        self._place_thumbs(update=False)
        if render_dynamic:
            self._render_harmony()
        if update:
            for control in (
                getattr(self, "preview", None),
                getattr(self, "color_field_bg", None),
                getattr(self, "field_thumb", None),
                getattr(self, "hue_thumb", None),
                getattr(self, "hsv_label", None),
                getattr(self, "hex_field", None),
                getattr(self, "r_field", None),
                getattr(self, "g_field", None),
                getattr(self, "b_field", None),
            ):
                if control is not None:
                    supdate(control)

    def _refresh_brightness_controls(self, update: bool = True) -> None:
        if hasattr(self, "bri_slider"):
            self.bri_slider.value = self.dimming
        if hasattr(self, "bri_value"):
            self.bri_value.value = f"{self.dimming}%"
        if hasattr(self, "preview_bri"):
            self._set_metric(self.preview_bri, "Brillo", f"{self.dimming}%")
        if update:
            supdate(self.bri_slider)
            supdate(self.bri_value)
            supdate(self.preview)

    def _refresh_white_controls(self, update: bool = True) -> None:
        if hasattr(self, "white_slider"):
            self.white_slider.value = self._kelvin_to_pct(self.temp_kelvin)
        if hasattr(self, "white_value"):
            self.white_value.value = self._white_label()
        if update:
            supdate(self.white_slider)
            supdate(self.white_value)
            self._refresh_color_controls(update=True, render_dynamic=False)

    # ------------------------------------------------------------------ #
    # Eventos color
    # ------------------------------------------------------------------ #
    def _live_enabled(self) -> bool:
        return bool(getattr(self.live_switch, "value", True))

    def _live_changed(self, e=None) -> None:
        self._save_picker_pref("apply_live", self._live_enabled())

    def _apply_field_point(self, point: tuple[float, float] | None, *, emit_live: bool) -> None:
        if point is None:
            return
        x, y = point
        self.sat = pointer_to_ratio(x, self._field_size, FIELD_THUMB) * 100.0
        self.val = 100.0 - pointer_to_ratio(y, self._field_size, FIELD_THUMB) * 100.0
        rgb = self._rgb()
        self._last_mode = "rgb"
        self._color_guard.touch(rgb, hold_seconds=0.85)
        self._refresh_color_controls(update=True, render_dynamic=False)
        if emit_live:
            self._emit_color(final=False)

    def _on_field_tap(self, e) -> None:
        self._apply_field_point(self._field_tracker.tap(e), emit_live=False)
        if self._live_enabled():
            self._emit_color(final=True)
        else:
            self._render_harmony()

    def _on_field_start(self, e) -> None:
        self._apply_field_point(self._field_tracker.begin(e), emit_live=self._live_enabled())

    def _on_field_update(self, e) -> None:
        self._apply_field_point(self._field_tracker.move(e), emit_live=self._live_enabled())

    def _on_field_end(self, e) -> None:
        self._apply_field_point(self._field_tracker.end(e), emit_live=False)
        self._color_guard.touch(self._rgb(), hold_seconds=1.15)
        if self._live_enabled():
            self._emit_color(final=True)
        else:
            self._render_harmony()

    def _apply_hue_point(self, point: tuple[float, float] | None, *, emit_live: bool) -> None:
        if point is None:
            return
        x, _ = point
        self.hue = pointer_to_ratio(x, self._hue_width, HUE_THUMB) * 359.999
        self._last_mode = "rgb"
        self._color_guard.touch(self._rgb(), hold_seconds=0.85)
        self._refresh_color_controls(update=True, render_dynamic=False)
        if emit_live:
            self._emit_color(final=False)

    def _on_hue_tap(self, e) -> None:
        self._apply_hue_point(self._hue_tracker.tap(e), emit_live=False)
        if self._live_enabled():
            self._emit_color(final=True)
        else:
            self._render_harmony()

    def _on_hue_start(self, e) -> None:
        self._apply_hue_point(self._hue_tracker.begin(e), emit_live=self._live_enabled())

    def _on_hue_update(self, e) -> None:
        self._apply_hue_point(self._hue_tracker.move(e), emit_live=self._live_enabled())

    def _on_hue_end(self, e) -> None:
        self._apply_hue_point(self._hue_tracker.end(e), emit_live=False)
        self._color_guard.touch(self._rgb(), hold_seconds=1.15)
        if self._live_enabled():
            self._emit_color(final=True)
        else:
            self._render_harmony()

    def _emit_color(self, final: bool = False) -> None:
        if not final and not self._live_enabled():
            return
        if not self._color_throttle.ready(final):
            return
        r, g, b = self._rgb()
        self._last_mode = "rgb"
        try:
            self.wiz.set_rgb(r, g, b)
        finally:
            if final:
                self._remember_recent(self._hex())
                self._refresh_color_controls(update=True, render_dynamic=True)

    def _apply_current_color(self) -> None:
        self._color_guard.touch(self._rgb(), hold_seconds=1.15)
        self._emit_color(final=True)

    def _on_hex(self, e=None) -> None:
        self._pick_hex(self.hex_field.value)

    def _on_rgb_fields(self, e=None) -> None:
        try:
            r = max(0, min(255, int(float(self.r_field.value))))
            g = max(0, min(255, int(float(self.g_field.value))))
            b = max(0, min(255, int(float(self.b_field.value))))
        except Exception:
            return
        self._pick_rgb(r, g, b)

    def _on_precision_apply(self, e=None) -> None:
        typed_hex = str(getattr(self.hex_field, "value", "") or "").strip().upper()
        if typed_hex and typed_hex != self._hex().upper():
            parsed = self._parse_hex(typed_hex)
            if parsed is not None:
                self._pick_rgb(*parsed)
                return
        self._on_rgb_fields(e)

    def _pick_rgb(self, r: int, g: int, b: int) -> None:
        self._apply_rgb_to_local(r, g, b)
        self._last_mode = "rgb"
        self._color_guard.touch((r, g, b), hold_seconds=1.15)
        self._refresh_color_controls(update=True, render_dynamic=True)
        self.wiz.set_rgb(r, g, b)
        self._remember_recent("#{:02x}{:02x}{:02x}".format(r, g, b))

    def _pick_hex(self, hex_color: Any, final: bool = True) -> None:
        rgb = self._parse_hex(hex_color)
        if rgb is None:
            return
        self._pick_rgb(*rgb) if final else self._apply_rgb_to_local(*rgb)

    def _surprise_color(self) -> None:
        # Aleatorio bonito: evita colores demasiado grises u oscuros.
        palette_bias = random.choice(MOOD_PALETTES)[1]
        if random.random() < 0.45:
            self._pick_hex(random.choice(palette_bias))
            return
        self.hue = random.uniform(0, 359.999)
        self.sat = random.uniform(68, 100)
        self.val = random.uniform(78, 100)
        self._last_mode = "rgb"
        self._refresh_color_controls(update=True, render_dynamic=True)
        self._emit_color(final=True)

    # ------------------------------------------------------------------ #
    # Eventos brillo / blancos
    # ------------------------------------------------------------------ #
    def _on_brightness(self, e) -> None:
        self.dimming = int(self.bri_slider.value)
        self._bri_guard.touch(self.dimming, hold_seconds=0.85)
        self._refresh_brightness_controls(update=True)
        if self._bri_throttle.ready(False):
            self.wiz.set_brightness(self.dimming)

    def _on_brightness_end(self, e) -> None:
        self.dimming = int(self.bri_slider.value)
        self._bri_guard.touch(self.dimming, hold_seconds=1.15)
        self.wiz.set_brightness(self.dimming)
        self._refresh_brightness_controls(update=True)

    def _set_brightness(self, value: int) -> None:
        self.dimming = max(10, min(100, int(value)))
        self._bri_guard.touch(self.dimming, hold_seconds=1.15)
        self.wiz.set_brightness(self.dimming)
        self._refresh_brightness_controls(update=True)

    def _on_white_slider(self, e) -> None:
        self.temp_kelvin = self._pct_to_kelvin(int(self.white_slider.value))
        self._last_mode = "white"
        self._white_guard.touch(self.temp_kelvin, hold_seconds=0.90)
        self._refresh_white_controls(update=True)
        if self._white_throttle.ready(False):
            self.wiz.set_white(self.temp_kelvin)

    def _on_white_slider_end(self, e) -> None:
        self._last_mode = "white"
        self._white_guard.touch(self.temp_kelvin, hold_seconds=1.20)
        self.wiz.set_white(self.temp_kelvin)
        self._refresh_white_controls(update=True)

    def _set_white_kelvin(self, kelvin: int) -> None:
        lo, hi = self._kelvin_range()
        self.temp_kelvin = max(lo, min(hi, int(kelvin)))
        self._last_mode = "white"
        self._white_guard.touch(self.temp_kelvin, hold_seconds=1.20)
        self.wiz.set_white(self.temp_kelvin)
        self._refresh_white_controls(update=True)

    # ------------------------------------------------------------------ #
    # Favoritos / navegación
    # ------------------------------------------------------------------ #
    def _apply_favorite(self, fav: dict[str, Any]) -> None:
        try:
            self.wiz.apply_favorite(fav)
            if fav.get("type") == "rgb":
                rgb = self._parse_hex(fav.get("value"))
                if rgb:
                    self._apply_rgb_to_local(*rgb)
                    self._last_mode = "rgb"
                    self._refresh_color_controls(update=True, render_dynamic=True)
                    self._remember_recent(str(fav.get("value")))
            elif fav.get("type") == "white":
                self.temp_kelvin = int(fav.get("value"))
                self._last_mode = "white"
                self._refresh_white_controls(update=True)
        except Exception:
            pass

    def _save_current_favorite(self) -> None:
        if self._last_mode == "white":
            self.favorites.add_favorite(f"Blanco {self.temp_kelvin}K", "white", self.temp_kelvin, "LIGHT_MODE")
        else:
            h = self._hex()
            self.favorites.add_favorite(h.upper(), "rgb", h, "CIRCLE")
            self._remember_recent(h)
        self._render_favorites()

    def _go_favorites(self) -> None:
        try:
            app = self.page.controls[0]
            navigate = getattr(app, "navigate_to", None)
            if callable(navigate):
                navigate(3)
                return
            app.rail.selected_index = 3
            app.selected_index = 3
            app.content_area.content = app.panels[3]
            app.update()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Sync externo WiZ
    # ------------------------------------------------------------------ #
    def sync_state(self, state: dict) -> None:
        if not mounted(self):
            return
        changed_color = False
        changed_bri = False
        changed_white = False

        try:
            if "dimming" in state and not self._bri_guard.blocks(state["dimming"], tolerance=1):
                self.dimming = int(state["dimming"])
                changed_bri = True
        except Exception:
            pass

        try:
            if "temp" in state and not self._white_guard.blocks(state["temp"], tolerance=20):
                self.temp_kelvin = int(state["temp"])
                changed_white = True
                if not all(k in state for k in ("r", "g", "b")):
                    self._last_mode = "white"
        except Exception:
            pass

        try:
            if all(k in state for k in ("r", "g", "b")):
                r, g, b = int(state["r"]), int(state["g"]), int(state["b"])
                if not self._color_guard.blocks((r, g, b), tolerance=3):
                    self._apply_rgb_to_local(r, g, b)
                    self._last_mode = "rgb"
                    changed_color = True
        except Exception:
            pass

        if changed_color:
            self._refresh_color_controls(update=True, render_dynamic=False)
        if changed_bri:
            self._refresh_brightness_controls(update=True)
        if changed_white:
            self._refresh_white_controls(update=True)
