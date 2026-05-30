from __future__ import annotations

import time

import flet as ft

from ui.theme import Theme, mounted, supdate

EO = ft.AnimationCurve.EASE_OUT


class HomePanel(ft.Column):
    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.is_on = True
        self._last_bri_ui = 0.0
        self._last_bri_send = 0.0
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        self.status_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=Theme.MUTED)
        self.status_text = ft.Text("Buscando…", size=12, color=Theme.MUTED)
        self.status_chip = ft.Container(
            content=ft.Row([self.status_dot, self.status_text], spacing=8),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            bgcolor=Theme.CARD,
            border_radius=20,
            border=ft.Border.all(1, Theme.STROKE),
        )
        self.btn_refresh = ft.IconButton(
            ft.Icons.REFRESH_ROUNDED,
            icon_color=Theme.MUTED,
            icon_size=20,
            tooltip="Releer estado real",
            on_click=lambda e: self.wiz.refresh(),
        )

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Inicio", style=Theme.H1),
                        ft.Text("Control principal de iluminación", color=Theme.MUTED, size=13),
                    ],
                    spacing=2,
                ),
                ft.Container(expand=True),
                self.status_chip,
                self.btn_refresh,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.target_text = ft.Text("Destino: —", color=Theme.MUTED, size=12)
        self.btn_single = ft.OutlinedButton("Una", icon=ft.Icons.LIGHTBULB_ROUNDED, on_click=lambda e: self._set_mode("single"))
        self.btn_all = ft.OutlinedButton("Todas", icon=ft.Icons.HUB_ROUNDED, on_click=lambda e: self._set_mode("all"))
        target_card = self._card(
            ft.Row(
                [
                    ft.Row([ft.Icon(ft.Icons.NEAR_ME_ROUNDED, color=Theme.ACCENT, size=18), ft.Text("DESTINO", style=Theme.LABEL)], spacing=8),
                    self.target_text,
                    ft.Container(expand=True),
                    self.btn_single,
                    self.btn_all,
                ],
                wrap=True,
                spacing=10,
                run_spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=14,
        )

        self.master_icon = ft.Icon(ft.Icons.POWER_SETTINGS_NEW_ROUNDED, size=34, color="white")
        self.master_label = ft.Text("ENCENDIDO", size=18, weight=ft.FontWeight.BOLD, color="white")
        self.master_subtitle = ft.Text("Toca para alternar la luz activa", color="white", size=11, opacity=0.7)
        self.master_card = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=self.master_icon,
                        width=64,
                        height=64,
                        border_radius=20,
                        bgcolor=ft.Colors.with_opacity(0.22, "white"),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text("Control maestro", color="white", size=12, opacity=0.85),
                            self.master_label,
                            self.master_subtitle,
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.TOUCH_APP_ROUNDED, color="white", opacity=0.6),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=18,
            ),
            padding=24,
            border_radius=Theme.R_LG,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[Theme.PRIMARY, Theme.PRIMARY_D],
            ),
            shadow=Theme.GLOW(Theme.PRIMARY),
            on_click=self._toggle_master,
            ink=True,
            animate=ft.Animation(180, EO),
        )

        self.bri_value = ft.Text("100%", size=14, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
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
        self.btn_bri_reset = ft.TextButton(
            "Restaurar",
            icon=ft.Icons.RESTART_ALT_ROUNDED,
            style=ft.ButtonStyle(color=Theme.MUTED),
            on_click=self._reset_brightness,
        )
        bri_card = self._card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.BRIGHTNESS_6_ROUNDED, color=Theme.ACCENT, size=18),
                                    ft.Text("BRILLO", style=Theme.LABEL),
                                ],
                                spacing=8,
                            ),
                            ft.Row([self.btn_bri_reset, self.bri_value], spacing=12),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.bri_slider,
                ],
                spacing=4,
            )
        )

        quick = ft.ResponsiveRow(
            spacing=12,
            run_spacing=12,
            controls=[
                self._quick("TV / Cine", ft.Icons.MOVIE_ROUNDED, "#8b5cf6", lambda e: self.wiz.set_scene(18)),
                self._quick("Lectura", ft.Icons.MENU_BOOK_ROUNDED, "#f59e0b", lambda e: self.wiz.set_white(4000)),
                self._quick("Relax", ft.Icons.SPA_ROUNDED, "#10b981", lambda e: self.wiz.set_scene(16)),
                self._quick("Fiesta", ft.Icons.CELEBRATION_ROUNDED, "#ec4899", lambda e: self.wiz.set_scene(4, speed=180)),
                self._quick("Cálido", ft.Icons.WB_TWILIGHT_ROUNDED, "#fb923c", lambda e: self.wiz.set_white_percent(0)),
                self._quick("Frío", ft.Icons.AC_UNIT_ROUNDED, "#38bdf8", lambda e: self.wiz.set_white_percent(100)),
                self._quick("Reset", ft.Icons.RESTART_ALT_ROUNDED, Theme.MUTED, lambda e: self._reset_all()),
            ],
        )

        self.controls = [header, target_card, self.master_card, bri_card, ft.Text("ACCESOS RÁPIDOS", style=Theme.LABEL), quick]
        self._sync_target_controls()

    # ------------------------------------------------------------------ #
    def _card(self, content, *, padding=20):
        return ft.Container(
            content=content,
            padding=padding,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )

    def _quick(self, title, icon, color, action):
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
            height=96,
            padding=16,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Icon(icon, color=color, size=20),
                        width=36,
                        height=36,
                        border_radius=10,
                        bgcolor=ft.Colors.with_opacity(0.15, color),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(title, color=Theme.TEXT, weight=ft.FontWeight.W_600, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            on_click=action,
            ink=True,
            animate=ft.Animation(120, EO),
        )

    # ------------------------------------------------------------------ #
    def _slider_interval(self) -> float:
        try:
            return self.wiz.get_target_config().get("slider_interval_ms", 65) / 1000.0
        except Exception:
            return 0.065

    def _set_mode(self, mode: str) -> None:
        self.wiz.set_target_mode(mode)
        self._sync_target_controls()
        supdate(self)

    def _sync_target_controls(self):
        cfg = self.wiz.get_target_config()
        mode = cfg.get("mode", "single")
        name = cfg.get("active_name") or cfg.get("active_ip") or "—"
        count = cfg.get("target_count", 0)
        self.target_text.value = f"Una: {name}" if mode == "single" else f"Todas: {count} destino(s)"
        self.master_subtitle.value = "Toca para alternar la luz activa" if mode == "single" else "Toca para alternar todas las luces online"
        self.btn_single.style = ft.ButtonStyle(color=Theme.PRIMARY if mode == "single" else Theme.MUTED, side=ft.BorderSide(1, Theme.PRIMARY if mode == "single" else Theme.STROKE))
        self.btn_all.style = ft.ButtonStyle(color=Theme.PRIMARY if mode == "all" else Theme.MUTED, side=ft.BorderSide(1, Theme.PRIMARY if mode == "all" else Theme.STROKE))

    def _toggle_master(self, e):
        self.is_on = not self.is_on
        if self.is_on:
            self.wiz.turn_on()
        else:
            self.wiz.turn_off()
        self._paint_master()

    def _paint_master(self):
        if self.is_on:
            self.master_label.value = "ENCENDIDO"
            self.master_icon.icon = ft.Icons.POWER_SETTINGS_NEW_ROUNDED
            self.master_card.gradient = ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1), colors=[Theme.PRIMARY, Theme.PRIMARY_D])
            self.master_card.shadow = Theme.GLOW(Theme.PRIMARY)
        else:
            self.master_label.value = "APAGADO"
            self.master_icon.icon = ft.Icons.POWER_OFF_ROUNDED
            self.master_card.gradient = ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1), colors=[Theme.CARD_HI, Theme.CARD])
            self.master_card.shadow = None
        supdate(self.master_card)

    def _on_brightness(self, e):
        self._set_brightness_from_ui(force=False)

    def _on_brightness_end(self, e):
        self._set_brightness_from_ui(force=True)

    def _set_brightness_from_ui(self, *, force: bool) -> None:
        v = int(self.bri_slider.value)
        now = time.monotonic()
        self.bri_value.value = f"{v}%"
        if force or now - self._last_bri_ui >= 0.08:
            supdate(self.bri_value)
            self._last_bri_ui = now
        if force or now - self._last_bri_send >= self._slider_interval():
            self.wiz.set_brightness(v)
            self._last_bri_send = now

    def _reset_brightness(self, e=None):
        self.bri_slider.value = 100
        self.bri_value.value = "100%"
        self.wiz.reset_brightness()
        supdate(self.bri_slider)
        supdate(self.bri_value)

    def _reset_all(self):
        self.wiz.reset_light()
        self.bri_slider.value = 100
        self.bri_value.value = "100%"
        supdate(self.bri_slider)
        supdate(self.bri_value)

    # ------------------------------------------------------------------ #
    def sync_state(self, state: dict):
        if not mounted(self):
            return
        if "dimming" in state:
            self.bri_slider.value = state["dimming"]
            self.bri_value.value = f"{int(state['dimming'])}%"
        if "state" in state:
            self.is_on = bool(state["state"])
            self._paint_master()

        s = self.wiz.summary()
        count = int(s.get("count", 0) or 0)
        active = int(s.get("active", 0) or 0)
        extra = f" · {s['label']}" if s.get("label") else ""

        if active > 0:
            self.status_dot.bgcolor = Theme.SUCCESS
            self.status_text.value = f"{active}/{count} online{extra}"
        elif count > 0:
            self.status_dot.bgcolor = Theme.MUTED
            self.status_text.value = f"{count} guardada{'s' if count != 1 else ''} · sin respuesta"
        else:
            self.status_dot.bgcolor = Theme.ERROR
            self.status_text.value = "Sin bombillas"

        self._sync_target_controls()
        supdate(self)
