import flet as ft
import colorsys
from ui.theme import Theme, supdate

PAD = 240
EO = ft.AnimationCurve.EASE_OUT

SWATCHES = [
    "#ff0000", "#ff7f00", "#ffd000", "#7fff00", "#00ff66",
    "#00ffd0", "#00b3ff", "#0040ff", "#7f00ff", "#ff00d4",
    "#ff0066", "#ff99cc", "#ffffff", "#ffd9a8", "#a8e0ff",
]

WHITES = [
    (2200, "Vela",   "#ff9a3c"),
    (2700, "Cálido", "#ffc187"),
    (4000, "Neutro", "#ffe9d6"),
    (5000, "Día",    "#fbf7ff"),
    (6500, "Frío",   "#cfe8ff"),
]


class ColorPanel(ft.Column):
    """Pad 2D arrastrable: X = matiz, Y = saturación. Brillo en slider aparte."""

    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.hue = 210.0
        self.sat = 90.0
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        header = ft.Column(
            [ft.Text("Color", style=Theme.H1),
             ft.Text("Arrastra en el pad para elegir color", color=Theme.MUTED, size=13)],
            spacing=2,
        )

        self.preview = ft.Container(
            height=120, border_radius=Theme.R_LG,
            bgcolor=self._hex(), shadow=Theme.GLOW(self._hex()),
            animate=ft.Animation(140, EO),
            content=ft.Row(
                [ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color="white", size=30),
                 ft.Text("Color actual", color="white", weight=ft.FontWeight.W_600)],
                alignment=ft.MainAxisAlignment.CENTER, spacing=10,
            ),
        )

        # --- Pad HS ---
        self.thumb = ft.Container(
            width=22, height=22, border_radius=11,
            bgcolor=ft.Colors.with_opacity(0.0, "white"),
            border=ft.Border.all(3, "white"),
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.6, "black")),
        )
        pad = ft.Stack(
            width=PAD, height=PAD,
            controls=[
                ft.Container(
                    width=PAD, height=PAD, border_radius=Theme.R_MD,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1, 0), end=ft.Alignment(1, 0),
                        colors=["#ff0000", "#ffff00", "#00ff00", "#00ffff",
                                "#0000ff", "#ff00ff", "#ff0000"]),
                ),
                ft.Container(
                    width=PAD, height=PAD, border_radius=Theme.R_MD,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(0, -1), end=ft.Alignment(0, 1),
                        colors=[ft.Colors.with_opacity(1.0, "white"),
                                ft.Colors.with_opacity(0.0, "white")]),
                ),
                self.thumb,
                ft.GestureDetector(
                    width=PAD, height=PAD, drag_interval=16,
                    on_pan_start=self._on_pad, on_pan_update=self._on_pad,
                    on_tap_down=self._on_pad,
                ),
            ],
        )
        pad_card = self._card(ft.Column(
            [ft.Text("MATIZ / SATURACIÓN", style=Theme.LABEL),
             ft.Row([pad], alignment=ft.MainAxisAlignment.CENTER)],
            spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ))

        # --- Brillo ---
        self.bri_value = ft.Text("100%", size=13, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
        self.bri_slider = ft.Slider(min=10, max=100, value=100, divisions=18,
                                    active_color=Theme.ACCENT, thumb_color="white",
                                    on_change=self._on_brightness, expand=True)
        bri_card = self._card(ft.Column([
            ft.Row([ft.Text("BRILLO", style=Theme.LABEL), self.bri_value],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.bri_slider,
        ], spacing=4))

        # --- Hex (v1: TextField sin prefix_text) ---
        self.hex_field = ft.TextField(
            label="Hexadecimal", value=self._hex(), text_size=14,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
            on_submit=self._on_hex, dense=True,
        )
        hex_card = self._card(ft.Column([
            ft.Text("CÓDIGO HEX", style=Theme.LABEL), self.hex_field,
        ], spacing=8))

        # --- Swatches ---
        swatch_grid = ft.Row(wrap=True, spacing=10, run_spacing=10, controls=[
            ft.Container(
                width=38, height=38, border_radius=19, bgcolor=c,
                border=ft.Border.all(2, ft.Colors.with_opacity(0.25, "white")),
                on_click=lambda e, col=c: self._pick_hex(col), ink=True,
            ) for c in SWATCHES
        ])
        swatches = self._card(ft.Column([
            ft.Text("COLORES RÁPIDOS", style=Theme.LABEL), swatch_grid,
        ], spacing=12))

        # --- Blancos ---
        white_btns = ft.Row(spacing=10, controls=[
            ft.Container(
                expand=True, height=64, border_radius=Theme.R_SM,
                bgcolor=ft.Colors.with_opacity(0.10, col),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.4, col)),
                content=ft.Column(
                    [ft.Icon(ft.Icons.LIGHT_MODE_ROUNDED, color=col, size=18),
                     ft.Text(label, size=11, color=Theme.TEXT)],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                on_click=lambda e, kk=k: self.wiz.set_white(kk), ink=True,
            ) for k, label, col in WHITES
        ])
        whites = self._card(ft.Column([
            ft.Text("TEMPERATURA DE BLANCOS", style=Theme.LABEL), white_btns,
        ], spacing=12))

        self.controls = [header, self.preview, pad_card, bri_card,
                         hex_card, swatches, whites]
        self._place_thumb()

    # ------------------------------------------------------------------ #
    def _card(self, content):
        return ft.Container(content=content, padding=20, border_radius=Theme.R_MD,
                            bgcolor=Theme.CARD, border=ft.Border.all(1, Theme.STROKE),
                            shadow=Theme.SHADOW)

    def _rgb(self):
        r, g, b = colorsys.hsv_to_rgb(self.hue / 360, self.sat / 100, 1.0)
        return int(r * 255), int(g * 255), int(b * 255)

    def _hex(self):
        return "#{:02x}{:02x}{:02x}".format(*self._rgb())

    def _place_thumb(self):
        self.thumb.left = max(0, min(PAD - 22, self.hue / 360 * PAD - 11))
        self.thumb.top = max(0, min(PAD - 22, self.sat / 100 * PAD - 11))
        supdate(self.thumb)

    def _refresh(self, send=True):
        h = self._hex()
        self.preview.bgcolor = h
        self.preview.shadow = Theme.GLOW(h)
        self.hex_field.value = h
        supdate(self.preview)
        supdate(self.hex_field)
        self._place_thumb()
        if send:
            self.wiz.set_rgb(*self._rgb())

    # ------------------------------------------------------------------ #
    def _on_pad(self, e):
        # Flet v1: el evento trae local_position (Offset con .x / .y)
        pos = getattr(e, "local_position", None)
        if pos is None:
            return
        x = max(0.0, min(float(PAD), float(pos.x)))
        y = max(0.0, min(float(PAD), float(pos.y)))
        self.hue = x / PAD * 360
        self.sat = y / PAD * 100
        self._refresh()

    def _on_brightness(self, e):
        v = int(self.bri_slider.value)
        self.bri_value.value = f"{v}%"
        supdate(self.bri_value)
        self.wiz.set_brightness(v)

    def _on_hex(self, e):
        try:
            self._pick_hex(self.hex_field.value)
        except Exception:
            pass

    def _pick_hex(self, hex_color):
        h = str(hex_color).lstrip("#").strip()
        if len(h) != 6:
            return
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        hh, ss, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        self.hue = hh * 360
        self.sat = ss * 100
        self._refresh()
