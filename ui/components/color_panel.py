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
    ("Rojo", "#ff0000"), ("Naranjo", "#ff7f00"), ("Amarillo", "#ffd000"),
    ("Verde", "#00ff40"), ("Cian", "#00d5ff"), ("Azul", "#0055ff"),
    ("Violeta", "#7f00ff"), ("Magenta", "#ff00cc"), ("Rosa", "#ff4fa3"),
    ("Blanco", "#ffffff"), ("Cálido", "#ffd9a8"), ("Frío", "#cfe8ff"),
]
WHITE_SWATCH_KELVIN = {"Blanco": 4000, "Cálido": 2700, "Frío": 6500}

WHITES = [
    (2200, "Vela", "#ff9a3c"),
    (2700, "Cálido", "#ffc187"),
    (4000, "Neutro", "#fff1df"),
    (5000, "Día", "#fffdf7"),
    (6500, "Frío", "#d6ecff"),
]


class _Throttle:
    def __init__(self, interval: float = 0.065):
        self.interval = interval
        self.last = 0.0

    def ready(self, final: bool = False) -> bool:
        now = time.monotonic()
        if final or now - self.last >= self.interval:
            self.last = now
            return True
        return False


class ColorPanel(ft.Column):
    """Color/Blancos sin assets externos: no más bloques grises por imágenes no cargadas."""

    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.favorites = FavoritesManager()
        self.hue = 0.0
        self.sat = 100.0
        self.temp_kelvin = 4000
        self._color_throttle = _Throttle(0.065)
        self._bri_throttle = _Throttle(0.065)
        self._white_throttle = _Throttle(0.075)
        self._build()

    def _build(self):
        header = ft.Row(
            [
                ft.Column([
                    ft.Text("Color", style=Theme.H1),
                    ft.Text("Color RGB preciso + blancos reales por Kelvin", color=Theme.MUTED, size=13),
                ], spacing=2),
                ft.Container(expand=True),
                ft.OutlinedButton("Guardar actual", icon=ft.Icons.STAR_BORDER_ROUNDED,
                                  style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
                                  on_click=lambda e: self._save_current_favorite()),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.preview = ft.Container(
            height=104,
            border_radius=Theme.R_LG,
            bgcolor=self._hex(),
            shadow=Theme.GLOW(self._hex()),
            animate=ft.Animation(90, EO),
            content=ft.Row([
                ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color="white", size=26),
                ft.Text("Color actual", color="white", weight=ft.FontWeight.W_600),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        )

        self.thumb = ft.Container(
            width=THUMB, height=THUMB, border_radius=THUMB / 2,
            bgcolor=ft.Colors.with_opacity(0.0, "white"),
            border=ft.Border.all(3, "white"),
            shadow=ft.BoxShadow(blur_radius=7, color=ft.Colors.with_opacity(0.65, "black")),
        )
        pad = ft.Stack(
            width=PAD, height=PAD,
            controls=[
                ft.Container(
                    width=PAD, height=PAD, border_radius=Theme.R_MD,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1, 0), end=ft.Alignment(1, 0),
                        colors=["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff", "#ff0000"],
                    ),
                ),
                ft.Container(
                    width=PAD, height=PAD, border_radius=Theme.R_MD,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(0, -1), end=ft.Alignment(0, 1),
                        colors=[ft.Colors.with_opacity(1.0, "white"), ft.Colors.with_opacity(0.0, "white")],
                    ),
                ),
                self.thumb,
                ft.GestureDetector(
                    width=PAD, height=PAD, drag_interval=32,
                    on_pan_start=self._on_pad, on_pan_update=self._on_pad,
                    on_pan_end=self._on_pad_end, on_tap_down=self._on_pad,
                ),
            ],
        )
        self.hex_field = ft.TextField(
            label="Hex", value=self._hex(), text_size=13,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
            on_submit=self._on_hex, dense=True,
        )
        picker_card = self._card(ft.Column([
            ft.Row([
                ft.Text("MATIZ / SATURACIÓN", style=Theme.LABEL),
                ft.Text("rojo exacto: esquina inferior izquierda", color=Theme.FAINT, size=11),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([pad], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                self.hex_field,
                ft.IconButton(ft.Icons.CHECK_ROUNDED, tooltip="Aplicar HEX", icon_color=Theme.PRIMARY, on_click=self._on_hex),
                ft.IconButton(ft.Icons.RESTART_ALT_ROUNDED, tooltip="Rojo puro", icon_color=Theme.MUTED, on_click=lambda e: self._pick_hex("#ff0000")),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=12))

        self.bri_value = ft.Text("100%", size=13, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
        self.bri_slider = ft.Slider(min=10, max=100, value=100, divisions=18,
                                    active_color=Theme.ACCENT, thumb_color="white",
                                    on_change=self._on_brightness, on_change_end=self._on_brightness_end,
                                    expand=True)
        bri_card = self._card(ft.Column([
            ft.Row([
                ft.Text("BRILLO", style=Theme.LABEL),
                ft.Row([self.bri_value, ft.IconButton(ft.Icons.RESTART_ALT_ROUNDED, icon_color=Theme.MUTED, tooltip="100%", on_click=self._reset_brightness)], spacing=4),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.bri_slider,
        ], spacing=4))

        lo, hi = self._kelvin_range()
        self.temp_kelvin = 4000 if lo <= 4000 <= hi else round((lo + hi) / 2)
        self.white_value = ft.Text(self._white_label(), size=13, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
        self.white_slider = ft.Slider(min=0, max=100, value=self._kelvin_to_pct(self.temp_kelvin), divisions=100,
                                      active_color="#fbbf24", thumb_color="white",
                                      on_change=self._on_white_slider, on_change_end=self._on_white_slider_end,
                                      expand=True)
        whites = self._card(ft.Column([
            ft.Row([
                ft.Text("TEMPERATURA DE BLANCOS", style=Theme.LABEL),
                ft.Row([self.white_value, ft.IconButton(ft.Icons.RESTART_ALT_ROUNDED, icon_color=Theme.MUTED, tooltip="Neutro", on_click=self._reset_white)], spacing=4),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.white_slider,
            ft.Text(f"Rango detectado: {lo}K – {hi}K", color=Theme.FAINT, size=11),
            ft.ResponsiveRow(spacing=10, run_spacing=10, controls=[self._white_preset(k, label, col) for k, label, col in WHITES]),
        ], spacing=8))

        swatches = self._card(ft.Column([
            ft.Text("COLORES RÁPIDOS", style=Theme.LABEL),
            ft.ResponsiveRow(spacing=10, run_spacing=10, controls=[self._swatch(name, color) for name, color in SWATCHES]),
        ], spacing=12))

        self.fav_row = ft.ResponsiveRow(spacing=10, run_spacing=10)
        favs_card = self._card(ft.Column([
            ft.Row([
                ft.Text("FAVORITOS RÁPIDOS", style=Theme.LABEL),
                ft.TextButton("Ver todos", icon=ft.Icons.OPEN_IN_NEW_ROUNDED, on_click=lambda e: self._go_favorites()),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.fav_row,
        ], spacing=10))

        layout = ft.ResponsiveRow(spacing=18, run_spacing=18, controls=[
            ft.Container(content=picker_card, col={"xs": 12, "lg": 5}),
            ft.Container(content=ft.Column([bri_card, whites, swatches, favs_card], spacing=18), col={"xs": 12, "lg": 7}),
        ])

        self.controls = [header, self.preview, layout]
        self._render_favorites()
        self._place_thumb()

    def _card(self, content):
        return ft.Container(content=content, padding=20, border_radius=Theme.R_MD,
                            bgcolor=Theme.CARD, border=ft.Border.all(1, Theme.STROKE), shadow=Theme.SHADOW)

    def _swatch(self, name: str, color: str):
        action = (lambda e, k=WHITE_SWATCH_KELVIN[name]: self._set_white_kelvin(k)) if name in WHITE_SWATCH_KELVIN else (lambda e, col=color: self._pick_hex(col))
        return ft.Container(col={"xs": 3, "sm": 2, "md": 1.5}, height=40, border_radius=20,
                            bgcolor=color, tooltip=name, border=ft.Border.all(2, ft.Colors.with_opacity(0.25, "white")),
                            on_click=action, ink=True)

    def _white_preset(self, kelvin: int, label: str, col: str):
        lo, hi = self._kelvin_range()
        disabled = kelvin < lo or kelvin > hi
        return ft.Container(col={"xs": 6, "sm": 4, "md": 2.4}, height=64, border_radius=Theme.R_SM,
                            bgcolor=ft.Colors.with_opacity(0.10, col), border=ft.Border.all(1, ft.Colors.with_opacity(0.4, col)),
                            opacity=0.45 if disabled else 1,
                            content=ft.Column([ft.Icon(ft.Icons.LIGHT_MODE_ROUNDED, color=col, size=18), ft.Text(label, size=11, color=Theme.TEXT)],
                                              alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                            on_click=(None if disabled else lambda e, kk=kelvin: self._set_white_kelvin(kk)), ink=not disabled)

    def _render_favorites(self):
        self.favorites = FavoritesManager()
        favs = self.favorites.get_favorites()[:8]
        self.fav_row.controls.clear()
        if not favs:
            self.fav_row.controls.append(ft.Text("Sin favoritos todavía. Guarda un color o blanco actual.", color=Theme.MUTED, size=12))
        else:
            for fav in favs:
                self.fav_row.controls.append(self._fav_chip(fav))
        supdate(self.fav_row)

    def _fav_chip(self, fav: dict):
        ftype = fav.get("type")
        value = fav.get("value")
        color = str(value) if ftype == "rgb" else "#fbbf24" if ftype == "white" else "#8b5cf6"
        return ft.Container(
            col={"xs": 6, "sm": 4, "md": 3}, height=42, padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=14, bgcolor=Theme.CARD_HI, border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row([ft.Container(width=16, height=16, border_radius=8, bgcolor=color), ft.Text(fav.get("name", "Favorito"), color=Theme.TEXT, size=12, overflow=ft.TextOverflow.ELLIPSIS)], spacing=8),
            on_click=lambda e, f=fav: self.wiz.apply_favorite(f), ink=True,
        )

    def _go_favorites(self):
        try:
            app = self.page.controls[0]
            app.rail.selected_index = 3
            app.selected_index = 3
            app.content_area.content = app.panels[3]
            app.update()
        except Exception:
            pass

    def _rgb(self):
        r, g, b = colorsys.hsv_to_rgb((self.hue % 360.0) / 360.0, max(0, min(100, self.sat)) / 100.0, 1.0)
        return round(r * 255), round(g * 255), round(b * 255)

    def _hex(self):
        return "#{:02x}{:02x}{:02x}".format(*self._rgb())

    def _kelvin_range(self) -> tuple[int, int]:
        try:
            lo, hi = self.wiz.get_kelvin_range()
            return int(lo), int(hi)
        except Exception:
            return 2200, 6500

    def _kelvin_to_pct(self, kelvin: int) -> int:
        lo, hi = self._kelvin_range()
        if hi <= lo:
            return 50
        return round((max(lo, min(hi, kelvin)) - lo) * 100 / (hi - lo))

    def _pct_to_kelvin(self, pct: int) -> int:
        lo, hi = self._kelvin_range()
        return round(lo + (hi - lo) * max(0, min(100, int(pct))) / 100)

    def _white_label(self):
        return f"{self._kelvin_to_pct(self.temp_kelvin)}% · {self.temp_kelvin}K"

    def _place_thumb(self):
        self.thumb.left = max(0, min(PAD - THUMB, self.hue / 359.999 * (PAD - 1) - THUMB / 2))
        self.thumb.top = max(0, min(PAD - THUMB, self.sat / 100 * (PAD - 1) - THUMB / 2))
        supdate(self.thumb)

    def _refresh_preview(self):
        h = self._hex()
        self.preview.bgcolor = h
        self.preview.shadow = Theme.GLOW(h)
        self.hex_field.value = h
        supdate(self.preview)
        supdate(self.hex_field)
        self._place_thumb()

    def _emit_color(self, final=False):
        if not self._color_throttle.ready(final):
            return
        if self.sat <= 5:
            self.wiz.set_white(self.temp_kelvin)
        else:
            self.wiz.set_rgb(*self._rgb())

    def _on_pad(self, e):
        pos = getattr(e, "local_position", None)
        if pos is None:
            return
        x = max(0.0, min(float(PAD - 1), float(pos.x)))
        y = max(0.0, min(float(PAD - 1), float(pos.y)))
        self.hue = 0.0 if x <= 5 or x >= PAD - 6 else x / (PAD - 1) * 359.999
        self.sat = 0.0 if y <= 5 else 100.0 if y >= PAD - 6 else y / (PAD - 1) * 100.0
        self._refresh_preview()
        self._emit_color(final=False)

    def _on_pad_end(self, e):
        self._emit_color(final=True)

    def _on_brightness(self, e):
        v = int(self.bri_slider.value)
        self.bri_value.value = f"{v}%"
        supdate(self.bri_value)
        if self._bri_throttle.ready(False):
            self.wiz.set_brightness(v)

    def _on_brightness_end(self, e):
        self.wiz.set_brightness(int(self.bri_slider.value))

    def _reset_brightness(self, e=None):
        self.bri_slider.value = 100
        self.bri_value.value = "100%"
        self.wiz.set_brightness(100)
        supdate(self.bri_slider)
        supdate(self.bri_value)

    def _on_white_slider(self, e):
        self.temp_kelvin = self._pct_to_kelvin(int(self.white_slider.value))
        self.white_value.value = self._white_label()
        supdate(self.white_value)
        if self._white_throttle.ready(False):
            self.wiz.set_white(self.temp_kelvin)

    def _on_white_slider_end(self, e):
        self.wiz.set_white(self.temp_kelvin)

    def _set_white_kelvin(self, kelvin: int):
        lo, hi = self._kelvin_range()
        self.temp_kelvin = max(lo, min(hi, int(kelvin)))
        self.white_slider.value = self._kelvin_to_pct(self.temp_kelvin)
        self.white_value.value = self._white_label()
        self.wiz.set_white(self.temp_kelvin)
        supdate(self.white_slider)
        supdate(self.white_value)

    def _reset_white(self, e=None):
        lo, hi = self._kelvin_range()
        self._set_white_kelvin(4000 if lo <= 4000 <= hi else round((lo + hi) / 2))

    def _on_hex(self, e=None):
        self._pick_hex(self.hex_field.value, final=True)

    def _pick_hex(self, hex_color, final=True):
        h = str(hex_color).lstrip("#").strip()
        if len(h) != 6:
            return
        try:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            return
        hh, ss, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        self.hue = min(359.999, hh * 360)
        self.sat = ss * 100
        self._refresh_preview()
        if final:
            self.wiz.set_white(self.temp_kelvin) if self.sat <= 5 else self.wiz.set_rgb(r, g, b)

    def _save_current_favorite(self):
        h = self._hex()
        if self.sat <= 2:
            self.favorites.add_favorite(f"Blanco {self.temp_kelvin}K", "white", self.temp_kelvin, "LIGHT_MODE")
        else:
            self.favorites.add_favorite(h.upper(), "rgb", h, "CIRCLE")
        self._render_favorites()

    def sync_state(self, state: dict):
        if not mounted(self):
            return
        if "dimming" in state:
            self.bri_slider.value = state["dimming"]
            self.bri_value.value = f"{int(state['dimming'])}%"
        if "temp" in state:
            self.temp_kelvin = int(state["temp"])
            self.white_slider.value = self._kelvin_to_pct(self.temp_kelvin)
            self.white_value.value = self._white_label()
        if all(k in state for k in ("r", "g", "b")):
            r, g, b = int(state["r"]), int(state["g"]), int(state["b"])
            hh, ss, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            self.hue = min(359.999, hh * 360)
            self.sat = ss * 100
            self._refresh_preview()
        self._render_favorites()
        supdate(self)
