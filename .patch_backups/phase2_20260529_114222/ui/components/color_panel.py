from __future__ import annotations

import colorsys
import time

import flet as ft

from config.favorites_manager import FavoritesManager
from ui.theme import Theme, mounted, supdate

PAD = 260
THUMB = 22
EO = ft.AnimationCurve.EASE_OUT

SWATCHES = [
    "#ff0000", "#ff7f00", "#ffd000", "#7fff00", "#00ff66",
    "#00ffd0", "#00b3ff", "#0040ff", "#7f00ff", "#ff00d4",
    "#ff0066", "#ffffff", "#ffcf9e", "#dfeeff", "#cfe8ff",
]

WHITE_PRESETS = [
    (0, "Mín", "#ff9a3c"),
    (18, "Cálido", "#ffc187"),
    (58, "Neutro", "#fff2df"),
    (76, "Día", "#f7fbff"),
    (100, "Frío", "#cfe8ff"),
]


class ColorPanel(ft.Column):
    """Color + blancos con throttling.

    X = matiz, Y = saturación. Si saturación es casi cero se usa set_white(),
    no RGB blanco, porque muchas WiZ muestran RGB blanco con tinte morado/rosado.
    """

    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.favs = FavoritesManager()
        self.hue = 0.0
        self.sat = 100.0
        self.white_pct = 58
        self._last_preview = 0.0
        self._last_send = 0.0
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        header = ft.Row(
            [
                ft.Column(
                    [ft.Text("Color", style=Theme.H1), ft.Text("RGB exacto + blancos por temperatura real", color=Theme.MUTED, size=13)],
                    spacing=2,
                ),
                ft.Container(expand=True),
                ft.TextButton("Guardar color", icon=ft.Icons.STAR_BORDER_ROUNDED, style=ft.ButtonStyle(color=Theme.MUTED), on_click=self._save_current_color),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.preview_label = ft.Text("Color actual", color="white", weight=ft.FontWeight.W_600)
        self.preview = ft.Container(
            height=112,
            border_radius=Theme.R_LG,
            bgcolor=self._hex(),
            shadow=Theme.GLOW(self._hex()),
            animate=ft.Animation(110, EO),
            content=ft.Row(
                [ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color="white", size=28), self.preview_label],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
            ),
        )

        self.thumb = ft.Container(
            width=THUMB,
            height=THUMB,
            border_radius=THUMB // 2,
            bgcolor=ft.Colors.with_opacity(0.0, "white"),
            border=ft.Border.all(3, "white"),
            shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.7, "black")),
        )
        pad = ft.Stack(
            width=PAD,
            height=PAD,
            controls=[
                ft.Container(
                    width=PAD,
                    height=PAD,
                    border_radius=Theme.R_MD,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1, 0),
                        end=ft.Alignment(1, 0),
                        colors=["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff", "#ff0000"],
                    ),
                ),
                ft.Container(
                    width=PAD,
                    height=PAD,
                    border_radius=Theme.R_MD,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(0, -1),
                        end=ft.Alignment(0, 1),
                        colors=[ft.Colors.with_opacity(1.0, "white"), ft.Colors.with_opacity(0.0, "white")],
                    ),
                ),
                self.thumb,
                ft.GestureDetector(
                    width=PAD,
                    height=PAD,
                    drag_interval=22,
                    on_pan_start=self._on_pad,
                    on_pan_update=self._on_pad,
                    on_pan_end=self._on_pad_end,
                    on_tap_down=self._on_pad,
                ),
            ],
        )
        pad_card = self._card(
            ft.Column(
                [
                    ft.Text("MATIZ / SATURACIÓN", style=Theme.LABEL),
                    ft.Text("Borde inferior = color saturado. Borde superior = blanco limpio por temperatura.", color=Theme.FAINT, size=11),
                    ft.Row([pad], alignment=ft.MainAxisAlignment.CENTER),
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

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
        bri_card = self._card(
            ft.Column(
                [
                    ft.Row(
                        [ft.Text("BRILLO", style=Theme.LABEL), ft.Row([ft.TextButton("Restaurar", icon=ft.Icons.RESTART_ALT_ROUNDED, style=ft.ButtonStyle(color=Theme.MUTED), on_click=self._reset_brightness), self.bri_value], spacing=10)],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.bri_slider,
                ],
                spacing=4,
            )
        )

        self.hex_field = ft.TextField(
            label="Hexadecimal",
            value=self._hex(),
            text_size=14,
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            on_submit=self._on_hex,
            dense=True,
            expand=True,
        )
        hex_card = self._card(
            ft.Row(
                [ft.Text("CÓDIGO HEX", style=Theme.LABEL), self.hex_field, ft.OutlinedButton("Aplicar", icon=ft.Icons.CHECK_ROUNDED, on_click=self._on_hex)],
                wrap=True,
                spacing=12,
                run_spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        swatch_grid = ft.Row(
            wrap=True,
            spacing=10,
            run_spacing=10,
            controls=[self._swatch(c) for c in SWATCHES],
        )
        swatches = self._card(ft.Column([ft.Text("COLORES RÁPIDOS", style=Theme.LABEL), swatch_grid], spacing=12))

        self.white_label = ft.Text("— K", size=13, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
        self.white_slider = ft.Slider(
            min=0,
            max=100,
            value=self.white_pct,
            divisions=100,
            active_color="#fbbf24",
            thumb_color="white",
            on_change=self._on_white_slider,
            on_change_end=self._on_white_slider_end,
            expand=True,
        )
        white_btns = ft.ResponsiveRow(
            spacing=10,
            run_spacing=10,
            controls=[self._white_preset(pct, label, col) for pct, label, col in WHITE_PRESETS],
        )
        whites = self._card(
            ft.Column(
                [
                    ft.Row(
                        [ft.Text("TEMPERATURA DE BLANCOS", style=Theme.LABEL), ft.Row([ft.TextButton("Restaurar", icon=ft.Icons.RESTART_ALT_ROUNDED, style=ft.ButtonStyle(color=Theme.MUTED), on_click=self._reset_white), self.white_label], spacing=10)],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    white_btns,
                    self.white_slider,
                ],
                spacing=10,
            )
        )

        self.controls = [header, self.preview, pad_card, bri_card, hex_card, swatches, whites]
        self._place_thumb()
        self._update_white_label()

    # ------------------------------------------------------------------ #
    def _card(self, content):
        return ft.Container(
            content=content,
            padding=20,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )

    def _swatch(self, color: str):
        return ft.Container(
            width=38,
            height=38,
            border_radius=19,
            bgcolor=color,
            border=ft.Border.all(2, ft.Colors.with_opacity(0.35, "white")),
            on_click=lambda e, col=color: self._pick_hex(col),
            ink=True,
        )

    def _white_preset(self, pct: int, label: str, col: str):
        return ft.Container(
            col={"xs": 6, "sm": 4, "md": 2},
            height=62,
            border_radius=Theme.R_SM,
            bgcolor=ft.Colors.with_opacity(0.10, col),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.4, col)),
            content=ft.Column(
                [ft.Icon(ft.Icons.LIGHT_MODE_ROUNDED, color=col, size=18), ft.Text(label, size=11, color=Theme.TEXT)],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            on_click=lambda e, p=pct: self._set_white_pct(p, force=True),
            ink=True,
        )

    def _rgb(self):
        r, g, b = colorsys.hsv_to_rgb((self.hue % 360) / 360.0, max(0, min(100, self.sat)) / 100.0, 1.0)
        return round(r * 255), round(g * 255), round(b * 255)

    def _hex(self):
        return "#{:02x}{:02x}{:02x}".format(*self._rgb())

    def _kelvin_from_pct(self, pct: int | None = None) -> int:
        info = self.wiz.color_info() if hasattr(self.wiz, "color_info") else {"kelvin_min": 2200, "kelvin_max": 6500}
        lo = int(info.get("kelvin_min", 2200))
        hi = int(info.get("kelvin_max", 6500))
        p = max(0, min(100, int(self.white_pct if pct is None else pct))) / 100.0
        return round(lo + (hi - lo) * p)

    def _pct_from_kelvin(self, kelvin: int) -> int:
        info = self.wiz.color_info() if hasattr(self.wiz, "color_info") else {"kelvin_min": 2200, "kelvin_max": 6500}
        lo = int(info.get("kelvin_min", 2200))
        hi = int(info.get("kelvin_max", 6500))
        if hi <= lo:
            return 50
        return max(0, min(100, round((int(kelvin) - lo) * 100 / (hi - lo))))

    def _place_thumb(self):
        x = ((self.hue % 360) / 360.0) * PAD
        y = (max(0, min(100, self.sat)) / 100.0) * PAD
        self.thumb.left = max(0, min(PAD - THUMB, x - THUMB / 2))
        self.thumb.top = max(0, min(PAD - THUMB, y - THUMB / 2))
        supdate(self.thumb)

    def _update_white_label(self):
        self.white_label.value = f"{self._kelvin_from_pct()} K · {int(self.white_pct)}%"
        supdate(self.white_label)

    def _refresh_visual(self, *, force=False):
        now = time.monotonic()
        h = self._hex()
        self.preview.bgcolor = h
        self.preview.shadow = Theme.GLOW(h)
        self.hex_field.value = h
        self.preview_label.value = "Blanco limpio" if self.sat <= 3 else "Color actual"
        self._place_thumb()
        if force or now - self._last_preview >= 0.055:
            self._last_preview = now
            supdate(self.preview)
            supdate(self.hex_field)

    def _send_current(self, *, force=False):
        now = time.monotonic()
        interval = self._slider_interval()
        if not force and now - self._last_send < interval:
            return
        self._last_send = now
        if self.sat <= 3:
            self.wiz.set_white_percent(int(self.white_pct))
        else:
            self.wiz.set_rgb(*self._rgb())

    def _slider_interval(self) -> float:
        try:
            return self.wiz.get_target_config().get("slider_interval_ms", 65) / 1000.0
        except Exception:
            return 0.065

    # ------------------------------------------------------------------ #
    def _on_pad(self, e):
        pos = getattr(e, "local_position", None)
        if pos is None:
            return
        x = max(0.0, min(float(PAD), float(pos.x)))
        y = max(0.0, min(float(PAD), float(pos.y)))
        self.hue = (x / PAD) * 360.0
        self.sat = (y / PAD) * 100.0
        self._refresh_visual(force=False)
        self._send_current(force=False)

    def _on_pad_end(self, e):
        self._refresh_visual(force=True)
        self._send_current(force=True)

    def _on_brightness(self, e):
        self._set_brightness_from_ui(force=False)

    def _on_brightness_end(self, e):
        self._set_brightness_from_ui(force=True)

    def _set_brightness_from_ui(self, *, force: bool):
        v = int(self.bri_slider.value)
        self.bri_value.value = f"{v}%"
        if force or time.monotonic() - getattr(self, "_last_bri_ui", 0.0) >= 0.08:
            self._last_bri_ui = time.monotonic()
            supdate(self.bri_value)
        if force or time.monotonic() - getattr(self, "_last_bri_send", 0.0) >= self._slider_interval():
            self._last_bri_send = time.monotonic()
            self.wiz.set_brightness(v)

    def _reset_brightness(self, e=None):
        self.bri_slider.value = 100
        self.bri_value.value = "100%"
        self.wiz.reset_brightness()
        supdate(self.bri_slider)
        supdate(self.bri_value)

    def _on_hex(self, e):
        self._pick_hex(self.hex_field.value)

    def _pick_hex(self, hex_color):
        h = str(hex_color).lstrip("#").strip()
        if len(h) != 6:
            return
        try:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            return
        hh, ss, _ = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        self.hue = hh * 360.0
        self.sat = ss * 100.0
        self._refresh_visual(force=True)
        self._send_current(force=True)

    def _set_white_pct(self, pct: int, *, force: bool):
        self.white_pct = max(0, min(100, int(pct)))
        self.white_slider.value = self.white_pct
        self.sat = 0
        self._refresh_visual(force=True)
        self._update_white_label()
        self.wiz.set_white_percent(self.white_pct)
        supdate(self.white_slider)

    def _on_white_slider(self, e):
        self.white_pct = int(self.white_slider.value)
        self.sat = 0
        self._refresh_visual(force=False)
        self._update_white_label()
        self._send_current(force=False)

    def _on_white_slider_end(self, e):
        self.white_pct = int(self.white_slider.value)
        self.sat = 0
        self._refresh_visual(force=True)
        self._update_white_label()
        self._send_current(force=True)

    def _reset_white(self, e=None):
        self._set_white_pct(58, force=True)

    def _save_current_color(self, e=None):
        if self.sat <= 3:
            k = self._kelvin_from_pct()
            self.favs.add_favorite(f"Blanco {k}K", "white", k, "LIGHT_MODE")
        else:
            self.favs.add_favorite(f"Color {self._hex()}", "rgb", self._hex(), "PALETTE")

    # ------------------------------------------------------------------ #
    def sync_state(self, state: dict):
        if not mounted(self):
            return
        if "dimming" in state:
            self.bri_slider.value = state["dimming"]
            self.bri_value.value = f"{int(state['dimming'])}%"
        if "temp" in state:
            try:
                self.white_pct = self._pct_from_kelvin(int(state["temp"]))
                self.white_slider.value = self.white_pct
                self._update_white_label()
            except Exception:
                pass
        supdate(self)
