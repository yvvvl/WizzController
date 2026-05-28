import flet as ft
import colorsys
from ui.theme import Theme

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
    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.hue = 210.0
        self.sat = 100.0
        self._build()

    def _build(self):
        header = ft.Column(
            [ft.Text("Color", style=Theme.H1),
             ft.Text("Mezclador y temperatura de blancos", color=Theme.MUTED, size=13)],
            spacing=2,
        )

        # Preview grande
        self.preview = ft.Container(
            height=140, border_radius=Theme.R_LG,
            bgcolor=self._hex(), shadow=Theme.GLOW(self._hex()),
            animate=ft.Animation(160, "easeOut"),
            content=ft.Column(
                [ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color="white", size=34),
                 ft.Text("Color actual", color="white", weight="w600")],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6,
            ),
        )

        # Slider de matiz con fondo arcoíris
        self.hue_slider = ft.Slider(
            min=0, max=360, value=self.hue, on_change=self._on_change,
            active_color="transparent", inactive_color="transparent", thumb_color="white",
        )
        hue_track = ft.Container(
            content=self.hue_slider, height=34, border_radius=18,
            gradient=ft.LinearGradient(
                colors=["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff", "#ff0000"],
                begin=ft.Alignment(-1, 0), end=ft.Alignment(1, 0),
            ),
        )

        self.sat_slider = ft.Slider(
            min=0, max=100, value=self.sat, on_change=self._on_change,
            active_color=Theme.ACCENT, thumb_color="white",
        )

        mixer = self._card(ft.Column([
            ft.Text("MEZCLADOR", style=Theme.LABEL),
            ft.Text("Matiz", size=12, color=Theme.MUTED),
            hue_track,
            ft.Container(height=4),
            ft.Text("Saturación", size=12, color=Theme.MUTED),
            self.sat_slider,
        ], spacing=8))

        # Swatches
        swatch_grid = ft.Row(wrap=True, spacing=10, run_spacing=10, controls=[
            ft.Container(
                width=40, height=40, border_radius=20, bgcolor=c,
                border=ft.border.all(2, ft.Colors.with_opacity(0.25, "white")),
                on_click=lambda e, col=c: self._pick_hex(col), ink=True,
                animate=ft.Animation(120, "easeOut"),
            ) for c in SWATCHES
        ])
        swatches = self._card(ft.Column([
            ft.Text("COLORES RÁPIDOS", style=Theme.LABEL), swatch_grid,
        ], spacing=12))

        # Blancos
        white_btns = ft.Row(spacing=10, controls=[
            ft.Container(
                expand=True, height=66, border_radius=Theme.R_SM,
                bgcolor=ft.Colors.with_opacity(0.10, col),
                border=ft.border.all(1, ft.Colors.with_opacity(0.4, col)),
                content=ft.Column(
                    [ft.Icon(ft.Icons.LIGHT_MODE_ROUNDED, color=col, size=18),
                     ft.Text(label, size=11, color=Theme.TEXT)],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4,
                ),
                on_click=lambda e, kk=k: self.wiz.set_white(kk), ink=True,
            ) for k, label, col in WHITES
        ])
        whites = self._card(ft.Column([
            ft.Text("TEMPERATURA DE BLANCOS", style=Theme.LABEL), white_btns,
        ], spacing=12))

        self.controls = [header, self.preview, mixer, swatches, whites]

    # ------------------------------------------------------------------ #
    def _card(self, content):
        return ft.Container(content=content, padding=20, border_radius=Theme.R_MD,
                            bgcolor=Theme.CARD, border=ft.border.all(1, Theme.STROKE),
                            shadow=Theme.SHADOW)

    def _rgb(self):
        r, g, b = colorsys.hsv_to_rgb(self.hue / 360, self.sat / 100, 1.0)
        return int(r * 255), int(g * 255), int(b * 255)

    def _hex(self):
        r, g, b = self._rgb()
        return f"#{r:02x}{g:02x}{b:02x}"

    def _refresh_preview(self):
        h = self._hex()
        self.preview.bgcolor = h
        self.preview.shadow = Theme.GLOW(h)
        if self.preview.page:
            self.preview.update()

    def _on_change(self, e):
        self.hue = self.hue_slider.value
        self.sat = self.sat_slider.value
        self._refresh_preview()
        self.wiz.set_rgb(*self._rgb())

    def _pick_hex(self, hex_color):
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        # actualizar sliders en consistencia
        hh, ss, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        self.hue = hh * 360
        self.sat = ss * 100
        self.hue_slider.value = self.hue
        self.sat_slider.value = self.sat
        if self.hue_slider.page:
            self.hue_slider.update()
            self.sat_slider.update()
        self._refresh_preview()
        self.wiz.set_rgb(r, g, b)
