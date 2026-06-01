from __future__ import annotations

import time

import flet as ft
from config.favorites_manager import FavoritesManager
from ui.theme import Theme, mounted, supdate

EO = ft.AnimationCurve.EASE_OUT


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


class HomePanel(ft.Column):
    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.is_on = False
        self._bri_throttle = _Throttle(0.065)
        self.favorites = FavoritesManager()
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        self.status_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=Theme.MUTED)
        self.status_text = ft.Text("Buscando…", size=12, color=Theme.MUTED)
        self.target_text = ft.Text("", size=11, color=Theme.FAINT)
        self.status_chip = ft.Container(
            content=ft.Row([self.status_dot, ft.Column([self.status_text, self.target_text], spacing=0)], spacing=8),
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

        # --- Control maestro ---
        self.master_icon = ft.Icon(ft.Icons.POWER_OFF_ROUNDED, size=34, color="white")
        self.master_label = ft.Text("APAGADO", size=18, weight=ft.FontWeight.BOLD, color="white")
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
                            ft.Text("Toca para alternar el target activo", color="white", size=11, opacity=0.7),
                        ],
                        spacing=2,
                    ),
                    ft.Container(expand=True),
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
                colors=[Theme.CARD_HI, Theme.CARD],
            ),
            shadow=None,
            on_click=self._toggle_master,
            ink=True,
            animate=ft.Animation(180, EO),
        )

        # --- Brillo ---
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
        self.btn_reset_bri = ft.IconButton(
            ft.Icons.RESTART_ALT_ROUNDED,
            icon_color=Theme.MUTED,
            tooltip="Restaurar brillo a 100%",
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
                            ft.Row([self.bri_value, self.btn_reset_bri], spacing=4),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.bri_slider,
                ],
                spacing=4,
            )
        )

        quick = ft.Row(
            wrap=True,
            spacing=12,
            run_spacing=12,
            controls=[
                self._quick("TV / Cine", ft.Icons.MOVIE_ROUNDED, "#8b5cf6", lambda e: self.wiz.set_scene(18)),
                self._quick("Lectura", ft.Icons.MENU_BOOK_ROUNDED, "#f59e0b", lambda e: self.wiz.set_white(4000)),
                self._quick("Relax", ft.Icons.SPA_ROUNDED, "#10b981", lambda e: self.wiz.set_scene(16)),
                self._quick("Fiesta", ft.Icons.CELEBRATION_ROUNDED, "#ec4899", lambda e: self.wiz.set_scene(4, speed=180)),
                self._quick("Cálido", ft.Icons.WB_TWILIGHT_ROUNDED, "#fb923c", lambda e: self.wiz.set_white(2700)),
                self._quick("Frío", ft.Icons.AC_UNIT_ROUNDED, "#38bdf8", lambda e: self.wiz.set_white(6500)),
                self._quick("Reset", ft.Icons.RESTART_ALT_ROUNDED, "#94a3b8", lambda e: self._reset_all()),
            ],
        )

        self.fav_row = ft.Row(wrap=True, spacing=10, run_spacing=10)
        favs_card = self._card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("FAVORITOS", style=Theme.LABEL),
                            ft.TextButton("Administrar", icon=ft.Icons.STAR_ROUNDED, on_click=lambda e: self._go_favorites()),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.fav_row,
                ],
                spacing=10,
            )
        )

        self.controls = [header, self.master_card, bri_card, ft.Text("ACCESOS RÁPIDOS", style=Theme.LABEL), quick, favs_card]
        self._render_favorites()

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

    def _quick(self, title, icon, color, action):
        return ft.Container(
            width=150,
            height=92,
            padding=12,
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
                    ft.Text(
                        title,
                        color=Theme.TEXT,
                        weight=ft.FontWeight.W_600,
                        size=13,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            on_click=action,
            ink=True,
            animate=ft.Animation(120, EO),
        )

    # ------------------------------------------------------------------ #
    def _apply_power_visual(self, is_on: bool):
        self.is_on = bool(is_on)
        if self.is_on:
            self.master_label.value = "ENCENDIDO"
            self.master_icon.icon = ft.Icons.POWER_SETTINGS_NEW_ROUNDED
            self.master_card.gradient = ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[Theme.PRIMARY, Theme.PRIMARY_D],
            )
            self.master_card.shadow = Theme.GLOW(Theme.PRIMARY)
        else:
            self.master_label.value = "APAGADO"
            self.master_icon.icon = ft.Icons.POWER_OFF_ROUNDED
            self.master_card.gradient = ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[Theme.CARD_HI, Theme.CARD],
            )
            self.master_card.shadow = None

    def _toggle_master(self, e):
        new_state = not self.is_on
        self.wiz.turn_on() if new_state else self.wiz.turn_off()
        self._apply_power_visual(new_state)
        self._safe(self.master_card)

    def _emit_brightness(self, final=False):
        v = int(self.bri_slider.value)
        if self._bri_throttle.ready(final):
            self.wiz.set_brightness(v)

    def _on_brightness(self, e):
        v = int(self.bri_slider.value)
        self.bri_value.value = f"{v}%"
        self._safe(self.bri_value)
        self._emit_brightness(final=False)

    def _on_brightness_end(self, e):
        self._emit_brightness(final=True)

    def _reset_brightness(self, e=None):
        self.bri_slider.value = 100
        self.bri_value.value = "100%"
        self.wiz.set_brightness(100)
        supdate(self.bri_slider)
        supdate(self.bri_value)

    def _reset_all(self):
        self.wiz.reset_light()
        self.bri_slider.value = 100
        self.bri_value.value = "100%"
        self._apply_power_visual(True)
        supdate(self)

    def _render_favorites(self):
        self.favorites = FavoritesManager()
        favs = self.favorites.get_favorites()[:6]
        self.fav_row.controls.clear()
        if not favs:
            self.fav_row.controls.append(ft.Text("Guarda colores/blancos desde Color o Favoritos.", color=Theme.MUTED, size=12))
        else:
            for fav in favs:
                self.fav_row.controls.append(self._fav_chip(fav))
        supdate(self.fav_row)

    def _fav_chip(self, fav: dict):
        ftype = fav.get("type")
        value = fav.get("value")
        color = str(value) if ftype == "rgb" else "#fbbf24" if ftype == "white" else "#8b5cf6"
        return ft.Container(
            width=168,
            height=46,
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=14,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [
                    ft.Container(width=16, height=16, border_radius=8, bgcolor=color),
                    ft.Text(fav.get("name", "Favorito"), color=Theme.TEXT, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=lambda e, f=fav: self.wiz.apply_favorite(f),
            ink=True,
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

    # ------------------------------------------------------------------ #
    def sync_state(self, state: dict):
        if not mounted(self):
            return
        if "dimming" in state:
            self.bri_slider.value = state["dimming"]
            self.bri_value.value = f"{int(state['dimming'])}%"
        if "state" in state:
            self._apply_power_visual(bool(state["state"]))

        s = self.wiz.summary()
        count = int(s.get("count", 0) or 0)
        active = int(s.get("active", 0) or 0)
        extra = f" · {s['label']}" if s.get("label") else ""
        mode = "1 luz" if s.get("target_mode") == "single" else "todas"
        active_ip = s.get("active_ip") or "—"

        if active > 0:
            self.status_dot.bgcolor = Theme.SUCCESS
            self.status_text.value = f"{active}/{count} online{extra}"
        elif count > 0:
            self.status_dot.bgcolor = Theme.MUTED
            self.status_text.value = f"{count} guardada{'s' if count != 1 else ''} · sin respuesta"
        else:
            self.status_dot.bgcolor = Theme.ERROR
            self.status_text.value = "Sin bombillas"
        self.target_text.value = f"target: {mode} · {active_ip}"
        self._render_favorites()

        supdate(self)

    def _safe(self, control):
        supdate(control)
