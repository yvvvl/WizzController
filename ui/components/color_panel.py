from __future__ import annotations

"""Polished Color Studio for WizZ Desktop.

The primary palette is designed for smart lighting rather than image editing:
hue runs horizontally, perceptual purity vertically and physical intensity is
controlled exclusively with WiZ dimming.
"""

from dataclasses import dataclass
import logging
import threading
import time
from typing import Any, Callable

import flet as ft
from localization import LocalizationManager

from config.config_manager import ConfigManager
from config.controller_settings_manager import ControllerSettingsManager
from config.favorites_manager import FavoritesManager
from core.action_sequence import ActionSequenceExecutor
from ui.color_studio import (
    GlobalDragTracker,
    PaletteGeometry,
    RGB,
    TrackGeometry,
    clamp,
    clamp_int,
    contrast_text_color,
    hue_purity_to_rgb,
    hue_saturation_to_rgb,
    kelvin_gradient_png,
    kelvin_to_ratio,
    kelvin_to_rgb,
    palette_png,
    parse_hex_color,
    ratio_to_kelvin,
    rgb_to_hex,
    rgb_to_hsv,
    rgb_to_hue_purity,
    white_label,
)
from ui.interaction import LocalEditGuard
from ui.theme import Theme, mounted, supdate

try:
    from config.color_history_manager import ColorHistoryManager
except Exception:  # pragma: no cover - compatibility with older branches
    ColorHistoryManager = None  # type: ignore[assignment,misc]

_LOG = logging.getLogger(__name__)

PICKER_DRAG_INTERVAL_MS = 6
PALETTE_THUMB = 24.0
CCT_THUMB = 24.0
# Compatibility names from Color Studio v1.
FIELD_THUMB = PALETTE_THUMB
HUE_THUMB = CCT_THUMB
CCT_HEIGHT = 34.0
BRIGHTNESS_MIN = 10
BRIGHTNESS_MAX = 100

QUICK_COLORS: tuple[tuple[str, str], ...] = (
    ("Rojo", "#ff0000"),
    ("Naranjo", "#ff7800"),
    ("Amarillo", "#ffff00"),
    ("Lima", "#9dff00"),
    ("Verde", "#00ff00"),
    ("Cian", "#00ffff"),
    ("Celeste", "#00aaff"),
    ("Azul", "#0000ff"),
    ("Violeta", "#8000ff"),
    ("Magenta", "#ff00ff"),
    ("Rosa", "#ff4fa3"),
)

WHITE_PRESETS: tuple[tuple[int, str, str], ...] = (
    (2200, "Vela", "muy cálido"),
    (2700, "Cálido", "relax"),
    (3500, "Hogar", "suave"),
    (4000, "Neutro", "diario"),
    (5000, "Día", "foco"),
    (6500, "Frío", "energía"),
)


@dataclass(slots=True)
class _RateGate:
    interval: float
    last: float = 0.0

    def ready(self, *, force: bool = False) -> bool:
        now = time.monotonic()
        if force or now - self.last >= self.interval:
            self.last = now
            return True
        return False


class ColorPanel(ft.Column):
    """Smart-light colour editor with separate RGB, CCT and dimming models."""

    def __init__(self, wiz: Any, *args: Any, **kwargs: Any) -> None:
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.i18n = kwargs.pop("i18n", None) or LocalizationManager(preference="es")
        self.executor = ActionSequenceExecutor(wiz)
        self.favorites = FavoritesManager()
        self._navigate: Callable[..., Any] | None = (
            kwargs.get("navigate")
            or kwargs.get("navigate_to")
            or kwargs.get("on_navigate")
        )
        if self._navigate is None:
            self._navigate = next((item for item in args if callable(item)), None)

        self._config = ConfigManager()
        self._controller_settings = ControllerSettingsManager()
        self._history = self._make_history_manager()
        self._fallback_recent_colors: list[str] = []
        self._fallback_recent_whites: list[int] = []

        prefs = self._config.get("color_studio", {})
        if not isinstance(prefs, dict):
            prefs = {}

        self.mode = "rgb"  # rgb | white
        self.view_mode = str(prefs.get("view_mode", "color"))
        if self.view_mode not in {"color", "white", "precise"}:
            self.view_mode = "color"
        self.hue = float(prefs.get("hue", 0.0)) % 360.0
        self.purity = clamp(
            float(prefs.get("purity", prefs.get("saturation", 1.0))),
            0.0,
            1.0,
        )
        self._exact_rgb: RGB | None = None
        self.temp_kelvin = int(prefs.get("kelvin", 4000) or 4000)
        self.dimming = clamp_int(
            prefs.get("dimming", self._controller_settings.get_brightness_default()),
            BRIGHTNESS_MIN,
            BRIGHTNESS_MAX,
        )
        self._pending = False
        self._pending_reason = ""
        self._dragging_palette = False
        self._dragging_cct = False
        self._dragging_brightness = False
        self._refreshing_fields = False
        self._last_error = ""

        color_interval = max(0.035, self._controller_settings.get_color_send_interval_ms() / 1000.0)
        slider_interval = max(0.035, self._controller_settings.get_slider_interval_ms() / 1000.0)
        self._color_gate = _RateGate(color_interval)
        self._white_gate = _RateGate(max(color_interval, 0.055))
        self._brightness_gate = _RateGate(slider_interval)
        self._preview_gate = _RateGate(1.0 / 60.0)

        self._color_guard = LocalEditGuard(1.05)
        self._white_guard = LocalEditGuard(1.05)
        self._brightness_guard = LocalEditGuard(1.0)

        self._viewport_width = 1080.0
        self._viewport_height = 720.0
        palette_width, palette_height = self._palette_size_for_viewport(self._viewport_width)
        self._palette_geometry = PaletteGeometry(palette_width, palette_height, PALETTE_THUMB)
        self._cct_geometry = TrackGeometry(palette_width, CCT_THUMB, CCT_HEIGHT)
        self._palette_tracker = GlobalDragTracker(
            self._palette_geometry.outer_width,
            self._palette_geometry.outer_height,
        )
        self._cct_tracker = GlobalDragTracker(
            self._cct_geometry.outer_width,
            self._cct_geometry.outer_height,
        )

        self._kelvin_min, self._kelvin_max = self._read_kelvin_range()
        self.temp_kelvin = clamp_int(self.temp_kelvin, self._kelvin_min, self._kelvin_max)

        self._build()
        self._install_compatibility_aliases()
        self._refresh_all(update=False)

    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def _white_name(self, kelvin: int) -> str:
        raw = white_label(kelvin)
        key = {
            "Vela": "white.name.candle",
            "Cálido": "white.name.warm",
            "Hogar": "white.name.home",
            "Neutro": "white.name.neutral",
            "Día": "white.name.daylight",
            "Frío": "white.name.cool",
        }.get(raw)
        return self._t(key) if key else raw

    def set_language(self, language: str | None = None) -> None:
        self._build()
        self._install_compatibility_aliases()
        self._refresh_all(update=False)
        if mounted(self):
            supdate(self)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build(self) -> None:
        header_copy = ft.Column(
            [
                ft.Text(self._t("color_studio.title"), style=Theme.H1),
                ft.Text(
                    self._t("color_studio.subtitle"),
                    color=Theme.MUTED,
                    size=13,
                ),
            ],
            spacing=2,
        )
        header_save = ft.OutlinedButton(
            self._t("color_studio.save_current"),
            icon=ft.Icons.STAR_BORDER_ROUNDED,
            style=ft.ButtonStyle(
                color=Theme.TEXT,
                side=ft.BorderSide(1, Theme.STROKE),
            ),
            on_click=lambda e: self._save_current_favorite(),
        )
        self.header = ft.ResponsiveRow(
            [
                ft.Container(content=header_copy, col={"xs": 12, "md": 8}),
                ft.Container(
                    content=header_save,
                    col={"xs": 12, "md": 4},
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
            spacing=12,
            run_spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.preview_icon = ft.Container(
            width=50,
            height=50,
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.20, "white"),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color="white", size=27),
        )
        self.preview_title = ft.Text(size=20, weight=ft.FontWeight.BOLD)
        self.preview_subtitle = ft.Text(size=12, weight=ft.FontWeight.W_500)
        self.preview_mode = self._status_chip("RGB", ft.Icons.PALETTE_ROUNDED)
        self.preview_pending = self._status_chip(self._t("color_studio.live"), ft.Icons.BOLT_ROUNDED)
        self.preview = ft.Container(
            height=126,
            padding=ft.Padding.symmetric(horizontal=22, vertical=18),
            border_radius=Theme.R_LG,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.24, "white")),
            content=ft.Row(
                [
                    self.preview_icon,
                    ft.Column(
                        [self.preview_title, self.preview_subtitle],
                        spacing=3,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        [self.preview_mode, self.preview_pending],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        self.mode_buttons: dict[str, ft.Container] = {
            "color": self._mode_button("color", self._t("color_studio.color"), ft.Icons.PALETTE_ROUNDED),
            "white": self._mode_button("white", self._t("color_studio.white"), ft.Icons.LIGHT_MODE_ROUNDED),
            "precise": self._mode_button("precise", self._t("color_studio.precise"), ft.Icons.TUNE_ROUNDED),
        }
        self.mode_row = ft.Row(
            list(self.mode_buttons.values()),
            spacing=8,
            wrap=True,
        )

        self._build_palette_controls()
        self._build_white_controls()
        self._build_precise_controls()

        self.picker_card = self._card(
            ft.Column(
                [
                    self.mode_row,
                    self.color_section,
                    self.white_section,
                    self.precise_section,
                ],
                spacing=16,
            ),
            padding=18,
        )

        self._build_brightness_controls()
        self._build_apply_controls()
        right_column = ft.Column(
            [self.brightness_card, self.apply_card],
            spacing=18,
        )

        self.main_layout = ft.ResponsiveRow(
            [
                ft.Container(content=self.picker_card, col={"xs": 12, "lg": 7}),
                ft.Container(content=right_column, col={"xs": 12, "lg": 5}),
            ],
            spacing=18,
            run_spacing=18,
        )

        self.recent_row = ft.ResponsiveRow(spacing=10, run_spacing=10)
        self.recent_card = self._card(
            ft.Column(
                [
                    self._section_header(self._t("color_studio.recent_section"), self._t("color_studio.recent_subtitle")),
                    self.recent_row,
                ],
                spacing=12,
            ),
            padding=18,
        )

        self.favorite_row = ft.ResponsiveRow(spacing=10, run_spacing=10)
        favorite_header_controls: list[ft.Control] = [
            ft.Container(
                content=self._section_header(
                    self._t("color_studio.favorites_section"),
                    self._t("color_studio.favorites_subtitle"),
                ),
                col={"xs": 12, "sm": 8} if self._navigate is not None else 12,
            )
        ]
        if self._navigate is not None:
            favorite_header_controls.append(
                ft.Container(
                    content=ft.TextButton(
                        self._t("color_studio.view_all"),
                        icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
                        on_click=lambda e: self._go_favorites(),
                    ),
                    col={"xs": 12, "sm": 4},
                    alignment=ft.Alignment.CENTER_RIGHT,
                )
            )
        self.favorite_header = ft.ResponsiveRow(
            favorite_header_controls,
            spacing=8,
            run_spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.favorite_card = self._card(
            ft.Column(
                [
                    self.favorite_header,
                    self.favorite_row,
                ],
                spacing=12,
            ),
            padding=18,
        )

        self.controls = [
            self.header,
            self.preview,
            self.main_layout,
            self.recent_card,
            self.favorite_card,
        ]
        self._render_recent()
        self._render_favorites()

    def _build_palette_controls(self) -> None:
        geo = self._palette_geometry
        self.palette_image = ft.Image(
            src=palette_png(
                int(geo.image_width),
                int(geo.image_height),
                PALETTE_THUMB,
            ),
            width=geo.image_width,
            height=geo.image_height,
            left=geo.image_left,
            top=geo.image_top,
            fit=ft.BoxFit.FILL,
            border_radius=Theme.R_MD,
            filter_quality=ft.FilterQuality.HIGH,
            gapless_playback=True,
        )
        self.palette_thumb = self._picker_thumb(PALETTE_THUMB)
        self.palette_gesture = ft.GestureDetector(
            width=geo.outer_width,
            height=geo.outer_height,
            drag_interval=PICKER_DRAG_INTERVAL_MS,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap_up=self._on_palette_tap,
            on_pan_start=self._on_palette_start,
            on_pan_update=self._on_palette_update,
            on_pan_end=self._on_palette_end,
            on_pan_cancel=self._on_palette_cancel,
        )
        self.palette_stack = ft.Stack(
            [self.palette_image, self.palette_thumb, self.palette_gesture],
            width=geo.outer_width,
            height=geo.outer_height,
        )
        self.palette_hs_label = ft.Text(color=Theme.MUTED, size=12)
        self.palette_hex_label = ft.Text(color=Theme.TEXT, size=12, weight=ft.FontWeight.BOLD)
        self.palette_meta = ft.ResponsiveRow(
            [
                ft.Container(
                    content=self.palette_hs_label,
                    col={"xs": 12, "sm": 6},
                ),
                ft.Container(
                    content=self.palette_hex_label,
                    col={"xs": 12, "sm": 6},
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
            spacing=10,
            run_spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.quick_color_row = ft.ResponsiveRow(
            [self._quick_color(name, value) for name, value in QUICK_COLORS],
            spacing=9,
            run_spacing=9,
        )
        palette_header = ft.ResponsiveRow(
            [
                ft.Container(
                    content=self._section_header(
                        self._t("color_studio.palette_section"),
                        self._t("color_studio.palette_subtitle"),
                    ),
                    col={"xs": 12, "md": 9},
                ),
                ft.Container(
                    content=self._outline_chip(
                        "HEX",
                        lambda e: self._select_view("precise"),
                    ),
                    col={"xs": 12, "md": 3},
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
            spacing=10,
            run_spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.palette_axis_hint = ft.Text(
            self._t("color_studio.palette_hint"),
            color=Theme.FAINT,
            size=10,
            text_align=ft.TextAlign.CENTER,
        )
        self.color_section = ft.Column(
            [
                palette_header,
                ft.Row([self.palette_stack], alignment=ft.MainAxisAlignment.CENTER),
                self.palette_meta,
                self.palette_axis_hint,
                ft.Divider(height=1, color=Theme.STROKE),
                self._section_header(self._t("color_studio.quick_colors"), self._t("color_studio.quick_subtitle")),
                self.quick_color_row,
            ],
            spacing=13,
        )

    def _build_white_controls(self) -> None:
        geo = self._cct_geometry
        self.cct_image = ft.Image(
            src=kelvin_gradient_png(
                int(geo.length),
                int(geo.thickness),
                self._kelvin_min,
                self._kelvin_max,
                CCT_THUMB,
            ),
            width=geo.length,
            height=geo.thickness,
            left=geo.track_left,
            top=geo.track_top,
            fit=ft.BoxFit.FILL,
            border_radius=18,
            filter_quality=ft.FilterQuality.HIGH,
            gapless_playback=True,
        )
        self.cct_thumb = self._picker_thumb(CCT_THUMB)
        self.cct_thumb.top = geo.thumb_top
        self.cct_gesture = ft.GestureDetector(
            width=geo.outer_width,
            height=geo.outer_height,
            drag_interval=PICKER_DRAG_INTERVAL_MS,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap_up=self._on_cct_tap,
            on_pan_start=self._on_cct_start,
            on_pan_update=self._on_cct_update,
            on_pan_end=self._on_cct_end,
            on_pan_cancel=self._on_cct_cancel,
        )
        self.cct_stack = ft.Stack(
            [self.cct_image, self.cct_thumb, self.cct_gesture],
            width=geo.outer_width,
            height=geo.outer_height,
        )
        self.cct_label = ft.Text(color=Theme.TEXT, weight=ft.FontWeight.BOLD, size=13)
        self.cct_range_label = ft.Text(
            self._t("color_studio.detected_range", minimum=self._kelvin_min, maximum=self._kelvin_max),
            color=Theme.FAINT,
            size=11,
        )
        self.white_preset_row = ft.ResponsiveRow(
            [self._white_preset(k, label, subtitle) for k, label, subtitle in WHITE_PRESETS],
            spacing=9,
            run_spacing=9,
        )
        self.white_section = ft.Column(
            [
                self._section_header(
                    self._t("color_studio.cct_section"),
                    self._t("color_studio.cct_subtitle"),
                ),
                ft.Row([self.cct_stack], alignment=ft.MainAxisAlignment.CENTER),
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            content=self.cct_label,
                            col={"xs": 12, "sm": 5},
                        ),
                        ft.Container(
                            content=self.cct_range_label,
                            col={"xs": 12, "sm": 7},
                            alignment=ft.Alignment.CENTER_RIGHT,
                        ),
                    ],
                    spacing=10,
                    run_spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=1, color=Theme.STROKE),
                self.white_preset_row,
            ],
            spacing=14,
        )

    def _build_precise_controls(self) -> None:
        self.hex_field = self._text_field("HEX", "#FF0000")
        self.r_field = self._text_field("R", "255")
        self.g_field = self._text_field("G", "0")
        self.b_field = self._text_field("B", "0")
        self.h_field = self._text_field("H°", "0")
        self.s_field = self._text_field("S%", "100")
        for field in (self.hex_field, self.r_field, self.g_field, self.b_field, self.h_field, self.s_field):
            field.on_submit = self._on_precise_submit

        self.precise_fields = ft.ResponsiveRow(
            [
                ft.Container(self.hex_field, col={"xs": 12, "sm": 4}),
                ft.Container(self.r_field, col={"xs": 4, "sm": 2}),
                ft.Container(self.g_field, col={"xs": 4, "sm": 2}),
                ft.Container(self.b_field, col={"xs": 4, "sm": 2}),
                ft.Container(self.h_field, col={"xs": 6, "sm": 3}),
                ft.Container(self.s_field, col={"xs": 6, "sm": 3}),
            ],
            spacing=10,
            run_spacing=10,
        )
        self.precise_note = ft.Text(color=Theme.FAINT, size=11)
        self.precise_apply = ft.FilledButton(
            self._t("color_studio.use_values"),
            icon=ft.Icons.CHECK_ROUNDED,
            style=ft.ButtonStyle(bgcolor=Theme.PRIMARY, color="white"),
            on_click=self._on_precise_submit,
        )
        self.precise_section = ft.Column(
            [
                self._section_header(
                    self._t("color_studio.precise_section"),
                    self._t("color_studio.precise_subtitle"),
                ),
                self.precise_fields,
                self.precise_note,
                ft.Row([self.precise_apply], wrap=True),
            ],
            spacing=13,
        )

    def _build_brightness_controls(self) -> None:
        self.brightness_value = ft.Text(
            f"{self.dimming}%",
            color=Theme.TEXT,
            size=18,
            weight=ft.FontWeight.BOLD,
        )
        self.brightness_slider = ft.Slider(
            min=BRIGHTNESS_MIN,
            max=BRIGHTNESS_MAX,
            value=self.dimming,
            divisions=BRIGHTNESS_MAX - BRIGHTNESS_MIN,
            active_color=Theme.ACCENT,
            inactive_color=Theme.STROKE,
            thumb_color="white",
            on_change_start=self._on_brightness_start,
            on_change=self._on_brightness_change,
            on_change_end=self._on_brightness_end,
        )
        self.brightness_card = self._card(
            ft.Column(
                [
                    ft.Row(
                        [
                            self._section_header(self._t("home.brightness_section"), self._t("color_studio.brightness_subtitle")),
                            ft.Container(expand=True),
                            self.brightness_value,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.brightness_slider,
                    ft.Row(
                        [
                            self._mini_value_button("10%", 10),
                            self._mini_value_button("25%", 25),
                            self._mini_value_button("50%", 50),
                            self._mini_value_button("75%", 75),
                            self._mini_value_button("100%", 100),
                        ],
                        spacing=7,
                        wrap=True,
                    ),
                ],
                spacing=10,
            ),
            padding=18,
        )

    def _build_apply_controls(self) -> None:
        live_pref = self._config.get("color_studio", {})
        live_default = True
        if isinstance(live_pref, dict):
            live_default = bool(live_pref.get("apply_live", True))
        self.live_switch = ft.Switch(
            value=live_default,
            active_color=Theme.PRIMARY,
            on_change=self._live_changed,
        )
        self.pending_text = ft.Text(color=Theme.FAINT, size=11)
        self.apply_button = ft.FilledButton(
            self._t("common.apply"),
            icon=ft.Icons.CHECK_ROUNDED,
            style=ft.ButtonStyle(bgcolor=Theme.PRIMARY, color="white"),
            on_click=lambda e: self._apply_current(manual=True),
        )
        self.apply_row = ft.Row(
            [self.apply_button],
            visible=not self._live_enabled(),
            wrap=True,
        )
        apply_copy = ft.Column(
            [
                ft.Text(self._t("color_studio.apply_section"), style=Theme.LABEL),
                ft.Text(
                    self._t("color_studio.apply_subtitle"),
                    color=Theme.FAINT,
                    size=11,
                ),
            ],
            spacing=2,
        )
        apply_toggle = ft.Row(
            [
                ft.Text(self._t("color_studio.live_apply"), color=Theme.TEXT, size=12),
                self.live_switch,
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.apply_header = ft.ResponsiveRow(
            [
                ft.Container(
                    content=apply_copy,
                    col={"xs": 12, "md": 7},
                ),
                ft.Container(
                    content=apply_toggle,
                    col={"xs": 12, "md": 5},
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
            spacing=8,
            run_spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.apply_card = self._card(
            ft.Column(
                [
                    self.apply_header,
                    self.pending_text,
                    self.apply_row,
                ],
                spacing=12,
            ),
            padding=18,
        )

    def _install_compatibility_aliases(self) -> None:
        """Keep harmless aliases used by tests and older UI integrations.

        Color Studio removes the separate Value square and hue
        bar, but these names let a branch upgrade without breaking unrelated
        code that only inspects controls or calls the former refresh hooks.
        """

        self.picker_apply_row = self.apply_row
        self.picker_apply_button = self.apply_button
        self.field_stack = self.palette_stack
        self.field_thumb = self.palette_thumb
        self.hue_stack = self.cct_stack
        self.hue_thumb = self.cct_thumb
        self.picker_meta = self.palette_meta
        self.hsv_label = self.palette_hs_label
        self.color_field_bg = self.palette_image
        self._field_size = self._palette_geometry.image_width
        self._hue_width = self._cct_geometry.length
        self._field_tracker = self._palette_tracker
        self._hue_tracker = GlobalDragTracker(
            self._cct_geometry.outer_width,
            self._cct_geometry.outer_height,
        )

    # ------------------------------------------------------------------
    # Small UI factories
    # ------------------------------------------------------------------
    def _card(self, content: ft.Control, *, padding: int = 20) -> ft.Container:
        return ft.Container(
            content=content,
            padding=padding,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )

    def _section_header(self, title: str, subtitle: str) -> ft.Column:
        return ft.Column(
            [
                ft.Text(title, style=Theme.LABEL),
                ft.Text(subtitle, color=Theme.FAINT, size=11),
            ],
            spacing=2,
        )

    def _status_chip(self, text: str, icon: Any) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.18, "white"),
            content=ft.Row(
                [ft.Icon(icon, size=14), ft.Text(text, size=11, weight=ft.FontWeight.BOLD)],
                spacing=5,
            ),
        )

    def _mode_button(self, key: str, label: str, icon: Any) -> ft.Container:
        return ft.Container(
            data=key,
            padding=ft.Padding.symmetric(horizontal=14, vertical=9),
            border_radius=18,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row([ft.Icon(icon, size=16), ft.Text(label, size=12)], spacing=6),
            ink=True,
            on_click=lambda e, selected=key: self._select_view(selected),
        )

    def _outline_chip(self, label: str, on_click: Callable[[Any], None]) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            border_radius=16,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Text(label, color=Theme.TEXT, size=10, weight=ft.FontWeight.BOLD),
            ink=True,
            on_click=on_click,
        )

    def _picker_thumb(self, diameter: float) -> ft.Container:
        return ft.Container(
            width=diameter,
            height=diameter,
            border_radius=diameter / 2.0,
            bgcolor=ft.Colors.with_opacity(0.04, "white"),
            border=ft.Border.all(3, "white"),
            shadow=ft.BoxShadow(
                blur_radius=8,
                spread_radius=1,
                color=ft.Colors.with_opacity(0.68, "black"),
            ),
        )

    def _quick_color(self, name: str, value: str) -> ft.Container:
        key = {
            "Rojo": "color.name.red",
            "Naranjo": "color.name.orange",
            "Amarillo": "color.name.yellow",
            "Lima": "color.name.lime",
            "Verde": "color.name.green",
            "Cian": "color.name.cyan",
            "Celeste": "color.name.sky",
            "Azul": "color.name.blue",
            "Violeta": "color.name.violet",
            "Magenta": "color.name.magenta",
            "Rosa": "color.name.pink",
        }.get(name)
        display_name = self._t(key) if key else name
        return ft.Container(
            col={"xs": 3, "sm": 2, "md": 1.5},
            height=46,
            border_radius=23,
            bgcolor=value,
            border=ft.Border.all(2, ft.Colors.with_opacity(0.25, "white")),
            tooltip=f"{display_name} · {value.upper()}",
            ink=True,
            on_click=lambda e, color=value: self._select_exact_rgb(parse_hex_color(color), source="preset"),
        )

    def _white_preset(self, kelvin: int, label: str, subtitle: str) -> ft.Container:
        label_key = {
            "Vela": "white.name.candle",
            "Cálido": "white.name.warm",
            "Hogar": "white.name.home",
            "Neutro": "white.name.neutral",
            "Día": "white.name.daylight",
            "Frío": "white.name.cool",
        }.get(label)
        subtitle_key = {
            "muy cálido": "white.note.very_warm",
            "relax": "white.note.relax",
            "suave": "white.note.soft",
            "diario": "white.note.daily",
            "foco": "white.note.focus",
            "energía": "white.note.energy",
        }.get(subtitle)
        display_label = self._t(label_key) if label_key else label
        display_subtitle = self._t(subtitle_key) if subtitle_key else subtitle
        disabled = kelvin < self._kelvin_min or kelvin > self._kelvin_max
        color = rgb_to_hex(kelvin_to_rgb(kelvin))
        return ft.Container(
            col={"xs": 6, "sm": 4, "md": 2},
            height=72,
            padding=10,
            border_radius=Theme.R_SM,
            bgcolor=ft.Colors.with_opacity(0.12, color),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.45, color)),
            opacity=0.42 if disabled else 1.0,
            tooltip=f"{kelvin}K",
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.LIGHT_MODE_ROUNDED, color=color, size=18),
                    ft.Text(display_label, color=Theme.TEXT, size=11, weight=ft.FontWeight.BOLD),
                    ft.Text(display_subtitle, color=Theme.FAINT, size=9),
                ],
                spacing=1,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ink=not disabled,
            on_click=None if disabled else lambda e, k=kelvin: self._select_kelvin(k, source="preset"),
        )

    def _text_field(self, label: str, value: str) -> ft.TextField:
        return ft.TextField(
            label=label,
            value=value,
            dense=True,
            text_size=13,
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            focused_border_color=Theme.PRIMARY,
        )

    def _mini_value_button(self, label: str, value: int) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=15,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Text(label, color=Theme.MUTED, size=10, weight=ft.FontWeight.BOLD),
            ink=True,
            on_click=lambda e, pct=value: self._set_brightness(pct, final=True),
        )

    # ------------------------------------------------------------------
    # State and rendering
    # ------------------------------------------------------------------
    def _current_rgb(self) -> RGB:
        return self._exact_rgb or hue_purity_to_rgb(self.hue, self.purity)

    def _current_display_rgb(self) -> RGB:
        return self._current_rgb() if self.mode == "rgb" else kelvin_to_rgb(self.temp_kelvin)

    def _current_action(self) -> dict[str, Any]:
        if self.mode == "white":
            return {"type": "white_kelvin", "value": int(self.temp_kelvin)}
        return {"type": "rgb", "value": rgb_to_hex(self._current_rgb())}

    def _refresh_all(self, *, update: bool = True) -> None:
        self._refresh_mode_controls()
        self._refresh_preview(interactive=False)
        self._refresh_palette(interactive=False)
        self._refresh_cct()
        self._refresh_precise_fields()
        self._refresh_brightness()
        self._refresh_apply_state()
        if update:
            self._batch_update(
                self.preview,
                self.mode_row,
                self.color_section,
                self.white_section,
                self.precise_section,
                self.brightness_card,
                self.apply_card,
            )

    def _refresh_mode_controls(self) -> None:
        self.color_section.visible = self.view_mode == "color"
        self.white_section.visible = self.view_mode == "white"
        self.precise_section.visible = self.view_mode == "precise"
        for key, button in self.mode_buttons.items():
            active = key == self.view_mode
            button.bgcolor = ft.Colors.with_opacity(0.20, Theme.PRIMARY) if active else "transparent"
            button.border = ft.Border.all(1, Theme.PRIMARY if active else Theme.STROKE)
            row = button.content
            if isinstance(row, ft.Row):
                for child in row.controls:
                    if isinstance(child, ft.Text):
                        child.color = Theme.TEXT if active else Theme.MUTED
                    elif isinstance(child, ft.Icon):
                        child.color = Theme.PRIMARY if active else Theme.MUTED

    def _refresh_preview(self, *, interactive: bool) -> None:
        rgb = self._current_display_rgb()
        background = rgb_to_hex(rgb)
        foreground = contrast_text_color(rgb)
        self.preview.bgcolor = background
        if not interactive:
            self.preview.shadow = Theme.GLOW(background)
        self.preview_icon.bgcolor = ft.Colors.with_opacity(0.18, foreground)
        icon = self.preview_icon.content
        if isinstance(icon, ft.Icon):
            icon.color = foreground
        self.preview_title.color = foreground
        self.preview_subtitle.color = ft.Colors.with_opacity(0.78, foreground)
        for chip in (self.preview_mode, self.preview_pending):
            chip.bgcolor = ft.Colors.with_opacity(0.16, foreground)
            row = chip.content
            if isinstance(row, ft.Row):
                for child in row.controls:
                    if isinstance(child, (ft.Text, ft.Icon)):
                        child.color = foreground

        if self.mode == "white":
            self.preview_title.value = self._t("color_studio.white_value", kelvin=self.temp_kelvin)
            self.preview_subtitle.value = f"{self._white_name(self.temp_kelvin)} · Brillo {self.dimming}%"
            self._set_chip(self.preview_mode, self._t("color_studio.mode_white"), ft.Icons.LIGHT_MODE_ROUNDED)
        else:
            hue, saturation, value = rgb_to_hsv(self._current_rgb())
            self.preview_title.value = f"RGB {rgb_to_hex(self._current_rgb(), upper=True)}"
            if self._exact_rgb is None:
                detail = (
                    f"H {round(self.hue % 360)}° · Pureza {round(self.purity * 100)}% "
                    f"· Brillo {self.dimming}%"
                )
            else:
                detail = (
                    f"H {round(hue)}° · S {round(saturation * 100)}% "
                    f"· Brillo {self.dimming}% · RGB exacto"
                )
                if value < 0.995:
                    detail += f" · V {round(value * 100)}%"
            self.preview_subtitle.value = detail
            self._set_chip(self.preview_mode, "RGB", ft.Icons.PALETTE_ROUNDED)

        if self._live_enabled():
            self._set_chip(self.preview_pending, self._t("color_studio.live"), ft.Icons.BOLT_ROUNDED)
        elif self._pending:
            self._set_chip(self.preview_pending, self._t("color_studio.pending"), ft.Icons.EDIT_ROUNDED)
        else:
            self._set_chip(self.preview_pending, self._t("color_studio.applied"), ft.Icons.CHECK_ROUNDED)

    def _refresh_palette(self, *, interactive: bool) -> None:
        left, top = self._palette_geometry.hue_purity_to_thumb_left_top(
            self.hue,
            self.purity,
        )
        self.palette_thumb.left = left
        self.palette_thumb.top = top
        pure_rgb = hue_purity_to_rgb(self.hue, self.purity)
        self.palette_thumb.bgcolor = rgb_to_hex(pure_rgb)
        self.palette_hs_label.value = (
            f"H {round(self.hue % 360)}° · Pureza {round(self.purity * 100)}%"
        )
        self.palette_hex_label.value = rgb_to_hex(self._current_rgb(), upper=True)
        if not interactive:
            self.palette_hex_label.tooltip = (
                self._t("color_studio.exact_preserved") if self._exact_rgb is not None else self._t("color_studio.direct_rgb")
            )

    def _refresh_cct(self) -> None:
        ratio = kelvin_to_ratio(self.temp_kelvin, self._kelvin_min, self._kelvin_max)
        self.cct_thumb.left = self._cct_geometry.ratio_to_thumb_left(ratio)
        self.cct_thumb.top = self._cct_geometry.thumb_top
        self.cct_thumb.bgcolor = rgb_to_hex(kelvin_to_rgb(self.temp_kelvin))
        self.cct_label.value = f"{self.temp_kelvin}K · {self._white_name(self.temp_kelvin)}"

    def _refresh_precise_fields(self) -> None:
        self._refreshing_fields = True
        try:
            rgb = self._current_rgb()
            hue, saturation, value = rgb_to_hsv(rgb)
            self.hex_field.value = rgb_to_hex(rgb, upper=True)
            self.r_field.value = str(rgb[0])
            self.g_field.value = str(rgb[1])
            self.b_field.value = str(rgb[2])
            self.h_field.value = str(round(hue, 1)).rstrip("0").rstrip(".")
            self.s_field.value = str(round(saturation * 100, 1)).rstrip("0").rstrip(".")
            if self._exact_rgb is not None and value < 0.995:
                self.precise_note.value = (
                    f"RGB exacto conservado (valor {round(value * 100)}%). "
                    "Al tocar la paleta volverá al modelo perceptual con brillo separado."
                )
                self.precise_note.color = Theme.WARNING
            else:
                self.precise_note.value = self._t("color_studio.palette_note")
                self.precise_note.color = Theme.FAINT
        finally:
            self._refreshing_fields = False

    def _refresh_brightness(self) -> None:
        self.brightness_slider.value = self.dimming
        self.brightness_value.value = f"{self.dimming}%"

    def _refresh_apply_state(self) -> None:
        live = self._live_enabled()
        self.apply_row.visible = not live
        self.apply_button.disabled = not self._pending
        if live:
            self.pending_text.value = self._t("color_studio.live_hint")
            self.pending_text.color = Theme.FAINT
        elif self._pending:
            suffix = f": {self._pending_reason}" if self._pending_reason else ""
            self.pending_text.value = f"Cambios pendientes{suffix}."
            self.pending_text.color = Theme.WARNING
        else:
            self.pending_text.value = self._t("color_studio.no_pending_changes")
            self.pending_text.color = Theme.FAINT

    def _set_chip(self, chip: ft.Container, text: str, icon: Any) -> None:
        row = chip.content
        if not isinstance(row, ft.Row) or len(row.controls) < 2:
            return
        icon_control, text_control = row.controls[0], row.controls[1]
        if isinstance(icon_control, ft.Icon):
            icon_control.icon = icon
        if isinstance(text_control, ft.Text):
            text_control.value = text

    def _mark_changed(self, reason: str) -> bool:
        previous = (self._pending, self._pending_reason)
        if self._live_enabled():
            self._pending = False
            self._pending_reason = ""
        else:
            self._pending = True
            self._pending_reason = reason
        return previous != (self._pending, self._pending_reason)

    def _batch_update(self, *controls: Any) -> None:
        targets = [control for control in controls if control is not None]
        if not targets:
            return
        try:
            page = self.page
        except Exception:
            page = None
        if page is not None:
            try:
                page.update(*targets)
                return
            except Exception:
                pass
        for target in targets:
            supdate(target)

    # ------------------------------------------------------------------
    # View and responsive layout
    # ------------------------------------------------------------------
    def _select_view(self, view: str, *, update: bool = True) -> None:
        if view not in {"color", "white", "precise"}:
            return
        previous_mode = self.mode
        self.view_mode = view
        if view == "color":
            self.mode = "rgb"
        elif view == "white":
            self.mode = "white"

        mode_changed = self.mode != previous_mode
        if mode_changed:
            self._mark_changed("modo")
            if self.mode == "rgb":
                self._color_guard.touch(self._current_rgb(), hold_seconds=1.0)
            else:
                self._white_guard.touch(self.temp_kelvin, hold_seconds=1.0)
            if self._live_enabled():
                gate = self._color_gate if self.mode == "rgb" else self._white_gate
                self._send_live(self._current_action(), gate, final=True)
                self._remember_current()

        self._save_preferences()
        self._refresh_mode_controls()
        self._refresh_preview(interactive=False)
        self._refresh_apply_state()
        if update:
            self._batch_update(self.mode_row, self.picker_card, self.preview, self.apply_card)

    def set_viewport(self, width: float, height: float | None = None) -> None:
        """Responsive hook used by the current WizzApp implementation."""

        try:
            width_value = max(280.0, float(width))
        except Exception:
            return
        height_value = self._viewport_height
        if height is not None:
            try:
                height_value = max(400.0, float(height))
            except Exception:
                pass
        self._viewport_width = width_value
        self._viewport_height = height_value
        new_width, new_height = self._palette_size_for_viewport(width_value)
        if (
            int(new_width) == int(self._palette_geometry.image_width)
            and int(new_height) == int(self._palette_geometry.image_height)
        ):
            return
        self._resize_picker(new_width, new_height)

    def _palette_size_for_viewport(self, width: float) -> tuple[int, int]:
        value = float(width)
        if value < 460:
            return 250, 82
        if value < 620:
            return 330, 104
        if value < 820:
            return 420, 130
        if value < 1120:
            return 500, 152
        return 560, 168

    def _resize_picker(self, width: int, height: int) -> None:
        self._palette_geometry = PaletteGeometry(width, height, PALETTE_THUMB)
        pgeo = self._palette_geometry
        self.palette_image.src = palette_png(width, height, PALETTE_THUMB)
        self.palette_image.width = pgeo.image_width
        self.palette_image.height = pgeo.image_height
        self.palette_image.left = pgeo.image_left
        self.palette_image.top = pgeo.image_top
        self.palette_stack.width = pgeo.outer_width
        self.palette_stack.height = pgeo.outer_height
        self.palette_gesture.width = pgeo.outer_width
        self.palette_gesture.height = pgeo.outer_height
        self._palette_tracker.resize(pgeo.outer_width, pgeo.outer_height)

        self._cct_geometry = TrackGeometry(width, CCT_THUMB, CCT_HEIGHT)
        cgeo = self._cct_geometry
        self.cct_image.src = kelvin_gradient_png(
            width,
            int(cgeo.thickness),
            self._kelvin_min,
            self._kelvin_max,
            CCT_THUMB,
        )
        self.cct_image.width = cgeo.length
        self.cct_image.height = cgeo.thickness
        self.cct_image.left = cgeo.track_left
        self.cct_image.top = cgeo.track_top
        self.cct_stack.width = cgeo.outer_width
        self.cct_stack.height = cgeo.outer_height
        self.cct_gesture.width = cgeo.outer_width
        self.cct_gesture.height = cgeo.outer_height
        self._cct_tracker.resize(cgeo.outer_width, cgeo.outer_height)
        self._hue_tracker.resize(cgeo.outer_width, cgeo.outer_height)
        self._field_size = pgeo.image_width
        self._hue_width = cgeo.length

        self._refresh_palette(interactive=False)
        self._refresh_cct()
        self._batch_update(self.palette_stack, self.cct_stack)

    # ------------------------------------------------------------------
    # Palette gestures
    # ------------------------------------------------------------------
    def _on_palette_tap(self, event: Any) -> None:
        self._apply_palette_point(self._palette_tracker.tap(event), emit_live=False, interactive=False)
        self._finish_palette_edit()

    def _on_palette_start(self, event: Any) -> None:
        self._dragging_palette = True
        self._apply_palette_point(
            self._palette_tracker.begin(event),
            emit_live=self._live_enabled(),
            interactive=True,
        )

    def _on_palette_update(self, event: Any) -> None:
        self._apply_palette_point(
            self._palette_tracker.move(event),
            emit_live=self._live_enabled(),
            interactive=True,
        )

    def _on_palette_end(self, event: Any) -> None:
        self._apply_palette_point(
            self._palette_tracker.end(event),
            emit_live=False,
            interactive=False,
            update=False,
        )
        self._dragging_palette = False
        self._finish_palette_edit()

    def _on_palette_cancel(self, event: Any) -> None:
        point = self._palette_tracker.cancel()
        self._dragging_palette = False
        if point is not None:
            self._apply_palette_point(point, emit_live=False, interactive=False, update=False)
            self._finish_palette_edit()

    def _apply_palette_point(
        self,
        point: tuple[float, float] | None,
        *,
        emit_live: bool,
        interactive: bool,
        update: bool = True,
    ) -> None:
        if point is None:
            return
        self.hue, self.purity = self._palette_geometry.pointer_to_hue_purity(*point)
        if self.hue >= 360.0:
            self.hue = 360.0
        self._exact_rgb = None
        self.mode = "rgb"
        self.view_mode = "color"
        rgb = self._current_rgb()
        self._color_guard.touch(rgb, hold_seconds=0.95)
        apply_changed = self._mark_changed("color")
        self._refresh_palette(interactive=interactive)
        preview_changed = self._preview_gate.ready(force=not interactive)
        if preview_changed:
            self._refresh_preview(interactive=interactive)
        if apply_changed or not interactive:
            self._refresh_apply_state()
        if update:
            self._batch_update(
                self.palette_thumb,
                self.palette_meta,
                self.preview if preview_changed else None,
                self.apply_card if apply_changed or not interactive else None,
            )
        if emit_live:
            self._send_live(self._current_action(), self._color_gate)

    def _finish_palette_edit(self) -> None:
        if self._live_enabled():
            self._send_live(self._current_action(), self._color_gate, final=True)
            self._remember_current()
        self._refresh_palette(interactive=False)
        self._refresh_preview(interactive=False)
        self._refresh_precise_fields()
        self._refresh_apply_state()
        self._save_preferences()
        self._batch_update(
            self.palette_thumb,
            self.palette_meta,
            self.preview,
            self.precise_fields,
            self.precise_note,
            self.apply_card,
        )

    # ------------------------------------------------------------------
    # CCT gestures
    # ------------------------------------------------------------------
    def _on_cct_tap(self, event: Any) -> None:
        self._apply_cct_point(self._cct_tracker.tap(event), emit_live=False, interactive=False)
        self._finish_cct_edit()

    def _on_cct_start(self, event: Any) -> None:
        self._dragging_cct = True
        self._apply_cct_point(
            self._cct_tracker.begin(event),
            emit_live=self._live_enabled(),
            interactive=True,
        )

    def _on_cct_update(self, event: Any) -> None:
        self._apply_cct_point(
            self._cct_tracker.move(event),
            emit_live=self._live_enabled(),
            interactive=True,
        )

    def _on_cct_end(self, event: Any) -> None:
        self._apply_cct_point(
            self._cct_tracker.end(event),
            emit_live=False,
            interactive=False,
            update=False,
        )
        self._dragging_cct = False
        self._finish_cct_edit()

    def _on_cct_cancel(self, event: Any) -> None:
        point = self._cct_tracker.cancel()
        self._dragging_cct = False
        if point is not None:
            self._apply_cct_point(point, emit_live=False, interactive=False, update=False)
            self._finish_cct_edit()

    def _apply_cct_point(
        self,
        point: tuple[float, float] | None,
        *,
        emit_live: bool,
        interactive: bool,
        update: bool = True,
    ) -> None:
        if point is None:
            return
        ratio = self._cct_geometry.pointer_to_ratio(point[0])
        self.temp_kelvin = ratio_to_kelvin(ratio, self._kelvin_min, self._kelvin_max)
        self.mode = "white"
        self.view_mode = "white"
        self._white_guard.touch(self.temp_kelvin, hold_seconds=0.95)
        apply_changed = self._mark_changed("blanco")
        self._refresh_cct()
        preview_changed = self._preview_gate.ready(force=not interactive)
        if preview_changed:
            self._refresh_preview(interactive=interactive)
        if apply_changed or not interactive:
            self._refresh_apply_state()
        if update:
            self._batch_update(
                self.cct_thumb,
                self.cct_label,
                self.preview if preview_changed else None,
                self.apply_card if apply_changed or not interactive else None,
            )
        if emit_live:
            self._send_live(self._current_action(), self._white_gate)

    def _finish_cct_edit(self) -> None:
        if self._live_enabled():
            self._send_live(self._current_action(), self._white_gate, final=True)
            self._remember_current()
        self._refresh_preview(interactive=False)
        self._refresh_apply_state()
        self._save_preferences()
        self._batch_update(self.cct_thumb, self.cct_label, self.preview, self.apply_card)

    # ------------------------------------------------------------------
    # Brightness
    # ------------------------------------------------------------------
    def _on_brightness_start(self, event: Any) -> None:
        self._dragging_brightness = True

    def _on_brightness_change(self, event: Any) -> None:
        value = getattr(getattr(event, "control", None), "value", self.brightness_slider.value)
        self._set_brightness(value, final=False)

    def _on_brightness_end(self, event: Any) -> None:
        self._dragging_brightness = False
        value = getattr(getattr(event, "control", None), "value", self.brightness_slider.value)
        self._set_brightness(value, final=True)

    def _set_brightness(self, value: int | float, *, final: bool) -> None:
        self.dimming = clamp_int(value, BRIGHTNESS_MIN, BRIGHTNESS_MAX)
        self._brightness_guard.touch(self.dimming, hold_seconds=0.95)
        apply_changed = self._mark_changed("brillo")
        self._refresh_brightness()
        preview_changed = self._preview_gate.ready(force=final)
        if preview_changed:
            self._refresh_preview(interactive=not final)
        if apply_changed or final:
            self._refresh_apply_state()
        self._batch_update(
            self.brightness_value,
            self.preview if preview_changed else None,
            self.apply_card if apply_changed or final else None,
        )
        if self._live_enabled():
            self._send_live(
                {"type": "brightness", "value": self.dimming},
                self._brightness_gate,
                final=final,
            )
        if final:
            self._save_preferences()

    # ------------------------------------------------------------------
    # Presets and precise input
    # ------------------------------------------------------------------
    def _select_exact_rgb(self, rgb: RGB, *, source: str) -> None:
        self._exact_rgb = rgb
        self.hue, self.purity = rgb_to_hue_purity(rgb)
        self.mode = "rgb"
        if self.view_mode == "white":
            self.view_mode = "color"
        self._color_guard.touch(rgb, hold_seconds=1.0)
        self._mark_changed(source)
        self._refresh_all(update=True)
        if self._live_enabled():
            self._send_live(self._current_action(), self._color_gate, final=True)
            self._remember_current()

    def _select_kelvin(self, kelvin: int, *, source: str) -> None:
        self.temp_kelvin = clamp_int(kelvin, self._kelvin_min, self._kelvin_max)
        self.mode = "white"
        self.view_mode = "white"
        self._white_guard.touch(self.temp_kelvin, hold_seconds=1.0)
        self._mark_changed(source)
        self._refresh_all(update=True)
        if self._live_enabled():
            self._send_live(self._current_action(), self._white_gate, final=True)
            self._remember_current()

    def _on_precise_submit(self, event: Any = None) -> None:
        if self._refreshing_fields:
            return
        try:
            hex_value = str(self.hex_field.value or "").strip()
            rgb_fields = (self.r_field.value, self.g_field.value, self.b_field.value)
            current_hex = rgb_to_hex(self._current_rgb(), upper=True)
            if hex_value and hex_value.upper() != current_hex.upper():
                rgb = parse_hex_color(hex_value)
                self._exact_rgb = rgb
                self.hue, self.purity = rgb_to_hue_purity(rgb)
            else:
                rgb = (
                    clamp_int(float(rgb_fields[0]), 0, 255),
                    clamp_int(float(rgb_fields[1]), 0, 255),
                    clamp_int(float(rgb_fields[2]), 0, 255),
                )
                # H/S in Preciso means standard HSV saturation. Preserve the
                # resulting RGB exactly instead of silently reinterpreting S as
                # the palette's perceptual purity axis.
                if rgb == self._current_rgb():
                    hue = float(self.h_field.value or self.hue) % 360.0
                    saturation = clamp(
                        float(self.s_field.value or 100.0) / 100.0,
                        0.0,
                        1.0,
                    )
                    rgb = hue_saturation_to_rgb(hue, saturation)
                    self._exact_rgb = rgb
                    self.hue, self.purity = rgb_to_hue_purity(rgb)
                else:
                    self._exact_rgb = rgb
                    self.hue, self.purity = rgb_to_hue_purity(rgb)
            self.mode = "rgb"
            self.view_mode = "precise"
            self._last_error = ""
            self._color_guard.touch(rgb, hold_seconds=1.0)
            self._mark_changed("RGB preciso")
            self._refresh_all(update=True)
            if self._live_enabled():
                self._send_live(self._current_action(), self._color_gate, final=True)
                self._remember_current()
        except Exception as exc:
            self._last_error = str(exc)
            self.precise_note.value = self._t("color_studio.apply_error", error=exc)
            self.precise_note.color = Theme.ERROR
            self._batch_update(self.precise_note)

    # ------------------------------------------------------------------
    # Apply / executor
    # ------------------------------------------------------------------
    def _live_enabled(self) -> bool:
        switch = getattr(self, "live_switch", None)
        return bool(getattr(switch, "value", True))

    def _live_changed(self, event: Any = None) -> None:
        live = self._live_enabled()
        self._save_preferences()
        if live and self._pending:
            self._apply_current(manual=False)
        else:
            self._refresh_apply_state()
            self._refresh_preview(interactive=False)
            self._batch_update(self.apply_card, self.preview)

    def _send_live(self, action: dict[str, Any], gate: _RateGate, *, final: bool = False) -> None:
        if not self._live_enabled() or not gate.ready(force=final):
            return
        try:
            # execute_action keeps every source on the unified action engine and
            # avoids spawning one thread per 6 ms pointer event.
            self.executor.execute_action(action)
            self._pending = False
            self._pending_reason = ""
        except Exception as exc:  # pragma: no cover - hardware/runtime failure
            self._last_error = str(exc)
            _LOG.warning("Color Studio live action failed: %s", exc, exc_info=True)

    def _apply_current(self, *, manual: bool) -> None:
        actions = [
            self._current_action(),
            {"type": "brightness", "value": int(self.dimming)},
        ]
        try:
            self.executor.execute(actions, threaded=True)
            self._pending = False
            self._pending_reason = ""
            self._color_guard.touch(self._current_rgb(), hold_seconds=1.1)
            self._white_guard.touch(self.temp_kelvin, hold_seconds=1.1)
            self._brightness_guard.touch(self.dimming, hold_seconds=1.0)
            self._remember_current()
            self._save_preferences()
            self._refresh_apply_state()
            self._refresh_preview(interactive=False)
            self._batch_update(self.apply_card, self.preview, self.recent_card)
        except Exception as exc:  # pragma: no cover - hardware/runtime failure
            self._last_error = str(exc)
            self.pending_text.value = self._t("color_studio.apply_error", error=exc)
            self.pending_text.color = Theme.ERROR
            self._batch_update(self.pending_text)

    # ------------------------------------------------------------------
    # History and favourites
    # ------------------------------------------------------------------
    def _make_history_manager(self) -> Any | None:
        if ColorHistoryManager is None:
            return None
        try:
            return ColorHistoryManager()
        except Exception:
            return None

    def _remember_current(self) -> None:
        if self.mode == "white":
            value = int(self.temp_kelvin)
            if self._history is not None and hasattr(self._history, "remember_white"):
                try:
                    self._history.remember_white(value)
                except Exception:
                    pass
            else:
                self._fallback_recent_whites = [value] + [
                    item for item in self._fallback_recent_whites if item != value
                ]
                self._fallback_recent_whites = self._fallback_recent_whites[:6]
        else:
            value = rgb_to_hex(self._current_rgb())
            if self._history is not None and hasattr(self._history, "remember_color"):
                try:
                    self._history.remember_color(value)
                except Exception:
                    pass
            else:
                self._fallback_recent_colors = [value] + [
                    item for item in self._fallback_recent_colors if item.lower() != value.lower()
                ]
                self._fallback_recent_colors = self._fallback_recent_colors[:10]
        self._render_recent()

    def _recent_values(self) -> tuple[list[str], list[int]]:
        colors = list(self._fallback_recent_colors)
        whites = list(self._fallback_recent_whites)
        if self._history is not None:
            try:
                colors = list(self._history.get_colors())
            except Exception:
                pass
            try:
                whites = list(self._history.get_whites())
            except Exception:
                pass
        return colors[:10], whites[:6]

    def _render_recent(self) -> None:
        colors, whites = self._recent_values()
        controls: list[ft.Control] = []
        for value in colors:
            try:
                rgb = parse_hex_color(value)
            except Exception:
                continue
            controls.append(
                ft.Container(
                    col={"xs": 3, "sm": 2, "md": 1},
                    height=42,
                    border_radius=21,
                    bgcolor=rgb_to_hex(rgb),
                    border=ft.Border.all(2, ft.Colors.with_opacity(0.25, "white")),
                    tooltip=rgb_to_hex(rgb, upper=True),
                    ink=True,
                    on_click=lambda e, selected=rgb: self._select_exact_rgb(selected, source="reciente"),
                )
            )
        for kelvin in whites:
            color = rgb_to_hex(kelvin_to_rgb(kelvin))
            controls.append(
                ft.Container(
                    col={"xs": 4, "sm": 3, "md": 2},
                    height=42,
                    padding=ft.Padding.symmetric(horizontal=10),
                    border_radius=21,
                    bgcolor=ft.Colors.with_opacity(0.14, color),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.5, color)),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(f"{kelvin}K", color=Theme.TEXT, size=10, weight=ft.FontWeight.BOLD),
                    ink=True,
                    on_click=lambda e, selected=kelvin: self._select_kelvin(selected, source="reciente"),
                )
            )
        if not controls:
            controls = [
                ft.Container(
                    col=12,
                    content=ft.Text(
                        self._t("color_studio.recents_empty"),
                        color=Theme.FAINT,
                        size=11,
                    ),
                )
            ]
        self.recent_row.controls = controls
        supdate(self.recent_row)

    def _save_current_favorite(self) -> None:
        try:
            if self.mode == "white":
                self.favorites.add_favorite(
                    self._t("color_studio.white_value", kelvin=self.temp_kelvin),
                    "white",
                    int(self.temp_kelvin),
                    "LIGHT_MODE",
                )
            else:
                value = rgb_to_hex(self._current_rgb())
                self.favorites.add_favorite(value.upper(), "rgb", value, "CIRCLE")
            self._render_favorites()
            self._batch_update(self.favorite_card)
        except Exception as exc:
            _LOG.warning("Could not save Color Studio favorite: %s", exc, exc_info=True)

    def _render_favorites(self) -> None:
        try:
            favorites = list(self.favorites.get_favorites())
        except Exception:
            favorites = []
        controls: list[ft.Control] = []
        for favorite in favorites:
            kind = str(favorite.get("type") or "")
            value = favorite.get("value")
            name = str(favorite.get("name") or self._t("color_studio.favorite_default"))
            if kind == "rgb":
                try:
                    rgb = parse_hex_color(str(value))
                except Exception:
                    continue
                controls.append(
                    self._favorite_chip(
                        name,
                        rgb_to_hex(rgb),
                        lambda e, selected=rgb: self._select_exact_rgb(selected, source="favorito"),
                    )
                )
            elif kind in {"white", "white_kelvin"}:
                try:
                    kelvin = int(value)
                except Exception:
                    continue
                controls.append(
                    self._favorite_chip(
                        name,
                        rgb_to_hex(kelvin_to_rgb(kelvin)),
                        lambda e, selected=kelvin: self._select_kelvin(selected, source="favorito"),
                    )
                )
            if len(controls) >= 8:
                break
        if not controls:
            controls = [
                ft.Container(
                    col=12,
                    content=ft.Text(
                        self._t("color_studio.favorites_empty"),
                        color=Theme.FAINT,
                        size=11,
                    ),
                )
            ]
        self.favorite_row.controls = controls
        supdate(self.favorite_row)

    def _favorite_chip(self, name: str, color: str, on_click: Callable[[Any], None]) -> ft.Container:
        return ft.Container(
            col={"xs": 6, "sm": 4, "md": 3},
            height=52,
            padding=ft.Padding.symmetric(horizontal=12),
            border_radius=Theme.R_SM,
            bgcolor=ft.Colors.with_opacity(0.11, color),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.48, color)),
            content=ft.Row(
                [
                    ft.Container(width=20, height=20, border_radius=10, bgcolor=color),
                    ft.Text(name, color=Theme.TEXT, size=11, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                ],
                spacing=8,
            ),
            ink=True,
            on_click=on_click,
        )

    # ------------------------------------------------------------------
    # Compatibility helpers for the previous Color Studio implementation
    # ------------------------------------------------------------------
    @property
    def sat(self) -> float:
        return self.purity * 100.0

    @sat.setter
    def sat(self, value: float) -> None:
        self.purity = clamp(float(value) / 100.0, 0.0, 1.0)

    @property
    def val(self) -> float:
        # Value is deliberately fixed. Dimming owns physical intensity.
        return 100.0

    @val.setter
    def val(self, value: float) -> None:
        # Accepted only so old state-restoration code cannot crash.
        return

    def _rgb(self) -> RGB:
        return self._current_rgb()

    def _hex(self) -> str:
        return rgb_to_hex(self._current_rgb())

    def _display_hex(self) -> str:
        return rgb_to_hex(self._current_display_rgb())

    def _hue_hex(self) -> str:
        return rgb_to_hex(hue_saturation_to_rgb(self.hue, 1.0))

    def _white_label(self) -> str:
        return f"{self.temp_kelvin}K · {self._white_name(self.temp_kelvin)}"

    def _kelvin_to_pct(self, kelvin: int) -> float:
        return kelvin_to_ratio(kelvin, self._kelvin_min, self._kelvin_max) * 100.0

    def _pct_to_kelvin(self, percent: float) -> int:
        return ratio_to_kelvin(float(percent) / 100.0, self._kelvin_min, self._kelvin_max)

    def _place_thumbs(self, update: bool = True) -> None:
        self._refresh_palette(interactive=False)
        self._refresh_cct()
        if update:
            self._batch_update(self.palette_thumb, self.cct_thumb)

    def _refresh_color_controls(
        self,
        update: bool = True,
        render_dynamic: bool = False,
        *,
        interactive: bool = False,
    ) -> None:
        self._refresh_palette(interactive=interactive)
        self._refresh_preview(interactive=interactive)
        if not interactive:
            self._refresh_precise_fields()
        if update:
            self._batch_update(
                self.palette_thumb,
                self.palette_meta,
                self.preview,
                None if interactive else self.precise_fields,
            )

    def _apply_field_point(
        self,
        point: tuple[float, float] | None,
        *,
        emit_live: bool,
        refresh: bool = True,
    ) -> None:
        self._apply_palette_point(
            point,
            emit_live=emit_live,
            interactive=True,
            update=refresh,
        )

    def _finish_color_edit(self) -> None:
        self._finish_palette_edit()

    def _on_field_tap(self, event: Any) -> None:
        self._on_palette_tap(event)

    def _on_field_start(self, event: Any) -> None:
        self._on_palette_start(event)

    def _on_field_update(self, event: Any) -> None:
        self._on_palette_update(event)

    def _on_field_end(self, event: Any) -> None:
        self._on_palette_end(event)

    def _on_field_cancel(self, event: Any) -> None:
        self._on_palette_cancel(event)

    def _apply_hue_point(
        self,
        point: tuple[float, float] | None,
        *,
        emit_live: bool,
        refresh: bool = True,
    ) -> None:
        if point is None:
            return
        ratio = self._cct_geometry.pointer_to_ratio(point[0])
        self.hue = ratio * 360.0
        self._exact_rgb = None
        self.mode = "rgb"
        self.view_mode = "color"
        self._color_guard.touch(self._current_rgb(), hold_seconds=0.95)
        self._mark_changed("color")
        self._refresh_palette(interactive=True)
        self._refresh_preview(interactive=True)
        self._refresh_apply_state()
        if refresh:
            self._batch_update(self.palette_thumb, self.palette_meta, self.preview, self.apply_card)
        if emit_live:
            self._send_live(self._current_action(), self._color_gate)

    def _on_hue_tap(self, event: Any) -> None:
        self._apply_hue_point(self._hue_tracker.tap(event), emit_live=False)
        self._finish_palette_edit()

    def _on_hue_start(self, event: Any) -> None:
        self._apply_hue_point(
            self._hue_tracker.begin(event),
            emit_live=self._live_enabled(),
        )

    def _on_hue_update(self, event: Any) -> None:
        self._apply_hue_point(
            self._hue_tracker.move(event),
            emit_live=self._live_enabled(),
        )

    def _on_hue_end(self, event: Any) -> None:
        self._apply_hue_point(self._hue_tracker.end(event), emit_live=False, refresh=False)
        self._finish_palette_edit()

    def _on_hue_cancel(self, event: Any) -> None:
        point = self._hue_tracker.cancel()
        if point is not None:
            self._apply_hue_point(point, emit_live=False, refresh=False)
            self._finish_palette_edit()

    def _render_harmony(self) -> None:
        # Harmonies remain outside the core picker to keep interaction lightweight.
        return

    def _apply_current_color(self) -> None:
        self._apply_current(manual=True)

    def refresh_favorites(self) -> None:
        self._render_favorites()
        self._batch_update(self.favorite_card)

    # ------------------------------------------------------------------
    # External state sync
    # ------------------------------------------------------------------
    def sync_state(self, state: dict[str, Any]) -> None:
        if not isinstance(state, dict):
            return
        changed = False
        dimming = state.get("dimming")
        if dimming is not None and not self._brightness_guard.blocks(dimming, tolerance=1):
            try:
                self.dimming = clamp_int(dimming, BRIGHTNESS_MIN, BRIGHTNESS_MAX)
                changed = True
            except Exception:
                pass

        temp = state.get("temp", state.get("temperature"))
        rgb_available = all(key in state for key in ("r", "g", "b"))
        if temp is not None and not self._white_guard.blocks(temp, tolerance=20):
            try:
                self.temp_kelvin = clamp_int(temp, self._kelvin_min, self._kelvin_max)
                self.mode = "white"
                if not self._dragging_cct:
                    self.view_mode = "white"
                changed = True
            except Exception:
                pass
        elif rgb_available:
            try:
                rgb = (
                    clamp_int(state["r"], 0, 255),
                    clamp_int(state["g"], 0, 255),
                    clamp_int(state["b"], 0, 255),
                )
                if not self._color_guard.blocks(rgb, tolerance=3):
                    self._exact_rgb = rgb
                    self.hue, self.purity = rgb_to_hue_purity(rgb)
                    self.mode = "rgb"
                    if not self._dragging_palette and self.view_mode != "precise":
                        self.view_mode = "color"
                    changed = True
            except Exception:
                pass

        if not changed:
            return
        self._pending = False
        self._pending_reason = ""
        self._refresh_all(update=mounted(self))

    def _go_favorites(self) -> None:
        if self._navigate is None:
            return
        for target in (3, "favorites", "favs"):
            try:
                self._navigate(target)
                return
            except (TypeError, ValueError, KeyError):
                continue
            except Exception:
                return

    # ------------------------------------------------------------------
    # Persistence and helpers
    # ------------------------------------------------------------------
    def _read_kelvin_range(self) -> tuple[int, int]:
        try:
            low, high = self.wiz.get_kelvin_range()
            low, high = int(low), int(high)
            if low > high:
                low, high = high, low
            return max(1000, low), min(10000, high)
        except Exception:
            return 2200, 6500

    def _save_preferences(self) -> None:
        try:
            data = {
                "apply_live": self._live_enabled(),
                "view_mode": self.view_mode,
                "hue": round(self.hue % 360.0, 3),
                "purity": round(self.purity, 4),
                "kelvin": int(self.temp_kelvin),
                "dimming": int(self.dimming),
            }
            self._config.set("color_studio", data)
        except Exception:
            pass


__all__ = [
    "CCT_THUMB",
    "ColorPanel",
    "FIELD_THUMB",
    "HUE_THUMB",
    "PALETTE_THUMB",
    "PICKER_DRAG_INTERVAL_MS",
]
