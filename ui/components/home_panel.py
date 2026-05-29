import flet as ft
from ui.theme import Theme, mounted, supdate

EO = ft.AnimationCurve.EASE_OUT


class HomePanel(ft.Column):
    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.is_on = True
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        self.status_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=Theme.MUTED)
        self.status_text = ft.Text("Buscando…", size=12, color=Theme.MUTED)
        self.status_chip = ft.Container(
            content=ft.Row([self.status_dot, self.status_text], spacing=8),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            bgcolor=Theme.CARD, border_radius=20, border=ft.Border.all(1, Theme.STROKE),
        )
        self.btn_refresh = ft.IconButton(
            ft.Icons.REFRESH_ROUNDED, icon_color=Theme.MUTED, icon_size=20,
            tooltip="Releer estado real", on_click=lambda e: self.wiz.refresh(),
        )

        header = ft.Row(
            [
                ft.Column([ft.Text("Inicio", style=Theme.H1),
                           ft.Text("Control principal de iluminación", color=Theme.MUTED, size=13)],
                          spacing=2),
                ft.Container(expand=True),
                self.status_chip, self.btn_refresh,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- Control maestro ---
        self.master_icon = ft.Icon(ft.Icons.POWER_SETTINGS_NEW_ROUNDED, size=34, color="white")
        self.master_label = ft.Text("ENCENDIDO", size=18, weight=ft.FontWeight.BOLD, color="white")
        self.master_card = ft.Container(
            content=ft.Row(
                [
                    ft.Container(content=self.master_icon, width=64, height=64, border_radius=20,
                                 bgcolor=ft.Colors.with_opacity(0.22, "white"),
                                 alignment=ft.Alignment.CENTER),
                    ft.Column([ft.Text("Control maestro", color="white", size=12, opacity=0.85),
                               self.master_label,
                               ft.Text("Toca para alternar todas las luces", color="white", size=11, opacity=0.7)],
                              spacing=2),
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.TOUCH_APP_ROUNDED, color="white", opacity=0.6),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=18,
            ),
            padding=24, border_radius=Theme.R_LG,
            gradient=ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
                                       colors=[Theme.PRIMARY, Theme.PRIMARY_D]),
            shadow=Theme.GLOW(Theme.PRIMARY),
            on_click=self._toggle_master, ink=True, animate=ft.Animation(220, EO),
        )

        # --- Brillo ---
        self.bri_value = ft.Text("100%", size=14, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
        self.bri_slider = ft.Slider(min=10, max=100, value=100, divisions=18,
                                    active_color=Theme.ACCENT, thumb_color="white",
                                    on_change=self._on_brightness, expand=True)
        bri_card = self._card(ft.Column([
            ft.Row([ft.Row([ft.Icon(ft.Icons.BRIGHTNESS_6_ROUNDED, color=Theme.ACCENT, size=18),
                            ft.Text("BRILLO", style=Theme.LABEL)], spacing=8),
                    self.bri_value], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.bri_slider,
        ], spacing=4))

        # --- Accesos rápidos ---
        quick = ft.Row(wrap=True, spacing=12, run_spacing=12, controls=[
            self._quick("TV / Cine", ft.Icons.MOVIE_ROUNDED, "#8b5cf6", lambda e: self.wiz.set_scene(18)),
            self._quick("Lectura",   ft.Icons.MENU_BOOK_ROUNDED, "#f59e0b", lambda e: self.wiz.set_white(4000)),
            self._quick("Relax",     ft.Icons.SPA_ROUNDED, "#10b981", lambda e: self.wiz.set_scene(16)),
            self._quick("Fiesta",    ft.Icons.CELEBRATION_ROUNDED, "#ec4899", lambda e: self.wiz.set_scene(4, speed=180)),
            self._quick("Cálido",    ft.Icons.WB_TWILIGHT_ROUNDED, "#fb923c", lambda e: self.wiz.set_white(2700)),
            self._quick("Frío",      ft.Icons.AC_UNIT_ROUNDED, "#38bdf8", lambda e: self.wiz.set_white(6500)),
        ])

        self.controls = [header, self.master_card, bri_card,
                         ft.Text("ACCESOS RÁPIDOS", style=Theme.LABEL), quick]

    # ------------------------------------------------------------------ #
    def _card(self, content):
        return ft.Container(content=content, padding=20, border_radius=Theme.R_MD,
                            bgcolor=Theme.CARD, border=ft.Border.all(1, Theme.STROKE),
                            shadow=Theme.SHADOW)

    def _quick(self, title, icon, color, action):
        return ft.Container(
            width=150, height=92, padding=16, border_radius=Theme.R_MD,
            bgcolor=Theme.CARD, border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column([
                ft.Container(content=ft.Icon(icon, color=color, size=20), width=36, height=36,
                             border_radius=10, bgcolor=ft.Colors.with_opacity(0.15, color),
                             alignment=ft.Alignment.CENTER),
                ft.Text(title, color=Theme.TEXT, weight=ft.FontWeight.W_600, size=14),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            on_click=action, ink=True, animate=ft.Animation(150, EO),
        )

    # ------------------------------------------------------------------ #
    def _toggle_master(self, e):
        self.is_on = not self.is_on
        if self.is_on:
            self.wiz.turn_on()
            self.master_label.value = "ENCENDIDO"
            self.master_icon.icon = ft.Icons.POWER_SETTINGS_NEW_ROUNDED
            self.master_card.gradient = ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
                                                          colors=[Theme.PRIMARY, Theme.PRIMARY_D])
            self.master_card.shadow = Theme.GLOW(Theme.PRIMARY)
        else:
            self.wiz.turn_off()
            self.master_label.value = "APAGADO"
            self.master_icon.icon = ft.Icons.POWER_OFF_ROUNDED
            self.master_card.gradient = ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
                                                          colors=[Theme.CARD_HI, Theme.CARD])
            self.master_card.shadow = None
        self._safe(self.master_card)

    def _on_brightness(self, e):
        v = int(self.bri_slider.value)
        self.bri_value.value = f"{v}%"
        self._safe(self.bri_value)
        self.wiz.set_brightness(v)

    # ------------------------------------------------------------------ #
    def sync_state(self, state: dict):
        if not mounted(self):
            return
        if "dimming" in state:
            self.bri_slider.value = state["dimming"]
            self.bri_value.value = f"{int(state['dimming'])}%"
        if "state" in state:
            self.is_on = bool(state["state"])
            self.master_label.value = "ENCENDIDO" if self.is_on else "APAGADO"

        s = self.wiz.summary()
        online = s["count"] > 0
        self.status_dot.bgcolor = Theme.SUCCESS if online else Theme.ERROR
        n = s["count"]
        extra = f" · {s['label']}" if s["label"] else ""
        self.status_text.value = (f"{n} bombilla{'s' if n != 1 else ''}{extra}"
                                  if online else "Sin bombillas")
        supdate(self)

    def _safe(self, control):
        supdate(control)
