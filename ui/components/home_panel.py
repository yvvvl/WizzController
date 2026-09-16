from __future__ import annotations

import time

import flet as ft
from localization import LocalizationManager, translated_favorite_name
from config.favorites_manager import FavoritesManager
from ui.responsive import PANEL_BREAKPOINTS, Viewport
from ui.theme import Theme, mounted, supdate
from ui.interaction import LocalEditGuard
from ui.components.target_selector import TargetSelector
from ui.color_studio import kelvin_to_rgb, rgb_to_hex

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


class _LinkedLights(ft.Container):
    """The operational Home light rail, backed by the shared selector state."""

    def __init__(self, wiz, selector: TargetSelector, *, i18n):
        super().__init__(
            padding=ft.Padding.only(top=4, bottom=2),
        )
        self.wiz = wiz
        self.selector = selector
        self.i18n = i18n
        self.count = ft.Text("", color=Theme.ACCENT, size=12, weight=ft.FontWeight.W_600)
        self.grid = ft.ResponsiveRow(breakpoints=PANEL_BREAKPOINTS, spacing=10, run_spacing=10)
        self.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(self._t("home.linked_lights"), style=Theme.H2),
                        ft.Container(expand=True),
                        self.count,
                        ft.TextButton(self._t("home.select_all"), on_click=self._select_all, style=ft.ButtonStyle(color=Theme.ACCENT)),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.grid,
            ],
            spacing=10,
        )
        self.refresh()

    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def _select_all(self, _event=None) -> None:
        self.selector.select_all()
        self.refresh()

    def refresh(self) -> None:
        bulbs = self.wiz.get_bulbs_detailed() if hasattr(self.wiz, "get_bulbs_detailed") else []
        selected = set(self.selector.selected_targets)
        total = len(bulbs)
        self.count.value = self._t("home.selected_lights", selected=len(selected), total=total)
        self.grid.controls = [self._light_row(bulb, str(bulb.get("ip") or "") in selected) for bulb in bulbs]
        if not self.grid.controls:
            self.grid.controls = [ft.Text(self._t("home.status.no_bulbs"), color=Theme.MUTED, size=12)]
        supdate(self.grid)
        supdate(self.count)

    @staticmethod
    def _state_from_bulb(bulb: dict) -> dict:
        """Normalize the compact device snapshot used by LightController.

        ``get_bulbs_detailed()`` intentionally exposes ``state`` as a boolean
        while the development preview exposes it as the raw dictionary.  Home
        accepts both shapes so the production and virtual-device paths render
        exactly the same selector.
        """
        raw_state = bulb.get("state")
        state = dict(raw_state) if isinstance(raw_state, dict) else {
            "state": bool(raw_state),
            "temp": bulb.get("temp"),
            "dimming": bulb.get("dimming"),
            "sceneId": bulb.get("sceneId"),
        }
        color = bulb.get("color_rgb")
        if isinstance(color, (tuple, list)) and len(color) == 3:
            state.update({"r": color[0], "g": color[1], "b": color[2]})
        return state

    def _light_color(self, state: dict) -> str:
        if not bool(state.get("state", False)):
            return Theme.FAINT
        if all(name in state for name in ("r", "g", "b")):
            return rgb_to_hex((int(state["r"]), int(state["g"]), int(state["b"])))
        return rgb_to_hex(kelvin_to_rgb(int(state.get("temp", 4000) or 4000)))

    def _light_row(self, bulb: dict, selected: bool) -> ft.Container:
        ip = str(bulb.get("ip") or "")
        state = self._state_from_bulb(bulb)
        on = bool(state.get("state", False))
        color = self._light_color(state)
        name = str(bulb.get("name") or ip or "—")
        brightness = max(0, min(100, int(state.get("dimming", 100) or 100)))
        bulb_icon = ft.Container(
            width=76,
            height=76,
            border_radius=38,
            bgcolor=color if on else Theme.FAINT,
            shadow=Theme.GLOW(color, 0.26) if on else None,
            alignment=ft.Alignment.CENTER,
            animate=Theme.animation(220),
            content=ft.Icon(
                ft.Icons.LIGHTBULB_ROUNDED,
                color="#ffffff" if on else Theme.MUTED,
                size=34,
            ),
        )
        content = ft.Container(
            padding=16,
            expand=True,
            alignment=ft.Alignment.CENTER_LEFT,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=5,
                                height=24,
                                border_radius=3,
                                bgcolor=Theme.PRIMARY if selected else "transparent",
                                animate=Theme.animation(160),
                            ),
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE_ROUNDED if selected else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED,
                                color=Theme.PRIMARY if selected else Theme.MUTED,
                                size=22,
                            ),
                            ft.Container(expand=True),
                            ft.Icon(
                                ft.Icons.POWER_SETTINGS_NEW_ROUNDED if on else ft.Icons.POWER_OFF_ROUNDED,
                                color=color if on else Theme.MUTED,
                                size=20,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            bulb_icon,
                            ft.Column(
                                [
                                    ft.Text(name, color=Theme.TEXT, size=15, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(ip, color=Theme.MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ],
                                spacing=3,
                                expand=True,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.LIGHT_MODE_ROUNDED, color=Theme.MUTED, size=17),
                            ft.ProgressBar(value=brightness / 100, color=color if on else Theme.FAINT, bgcolor=Theme.STROKE, bar_height=5, expand=True),
                            ft.Text(self._t("common.percent_value", value=brightness), color=Theme.MUTED, size=11, width=32, text_align=ft.TextAlign.RIGHT),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=10,
                tight=True,
            ),
        )
        return ft.Container(
            col={"xs": 12, "sm": 6, "lg": 4},
            padding=0,
            height=176,
            border_radius=Theme.R_MD,
            # Selection deliberately lives *inside* the card.  A blue outline
            # around every edge reads as a focus/debug ring, especially in the
            # light theme; a broad rail and a quiet surface tint are clearer.
            bgcolor=ft.Colors.with_opacity(0.08, Theme.PRIMARY) if selected else Theme.SURFACE,
            border=ft.Border.all(1, Theme.STROKE),
            animate=Theme.animation(180),
            # A dark, accent-tinted wave gives immediate physical feedback
            # without bringing back the pale hover/pre-selection surface.
            ink=True,
            ink_color=Theme.press_ink(0.20),
            on_click=lambda _event, target=ip: self._select(target),
            content=content,
        )

    def _select(self, ip: str) -> None:
        self.selector.toggle_selection(ip)
        self.refresh()


class HomePanel(ft.Column):
    def __init__(self, wiz, *, i18n=None):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.i18n = i18n or LocalizationManager(preference="es")
        self._last_state: dict = {}
        self.is_on = False
        self._bri_throttle = _Throttle(0.065)
        self._bri_guard = LocalEditGuard(1.05)
        self.favorites = FavoritesManager()
        self._viewport = Viewport(900, 720)
        self._build()

    # ------------------------------------------------------------------ #
    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def set_language(self, language: str | None = None) -> None:
        current_state = dict(getattr(self, "_last_state", {}) or {})
        self._build()
        if current_state:
            self.sync_state(current_state)
        elif mounted(self):
            supdate(self)

    def _build(self):
        self.status_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=Theme.MUTED)
        self.status_text = ft.Text(self._t("home.searching"), size=12, color=Theme.MUTED)
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
            tooltip=self._t("home.refresh_state"),
            on_click=lambda e: self.wiz.refresh(),
        )

        # Selector de destino (modo + ampolleta activa) en la parte principal.
        self.target_selector = TargetSelector(self.wiz, i18n=self.i18n)
        self.linked_lights = _LinkedLights(self.wiz, self.target_selector, i18n=self.i18n)
        self.target_selector.on_selection_changed = self._selection_changed

        self.header = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=10,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(self._t("home.header.title"), style=Theme.H1),
                            ft.Text(self._t("home.header.subtitle"), color=Theme.MUTED, size=13),
                        ],
                        spacing=2,
                    ),
                    col={"xs": 12, "md": 7},
                ),
                ft.Container(
                    content=ft.Row([self.status_chip, self.btn_refresh], spacing=6, alignment=ft.MainAxisAlignment.END),
                    col={"xs": 12, "md": 5},
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
        )

        # --- Control maestro ---
        self.master_icon = ft.Icon(ft.Icons.POWER_OFF_ROUNDED, size=26, color=Theme.TEXT)
        self.master_label = ft.Text(self._t("home.off"), size=17, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
        self.master_text = ft.Column(
            [
                ft.Text(self._t("home.master"), color=Theme.MUTED, size=12),
                self.master_label,
                ft.Text(self._t("home.master_hint"), color=Theme.FAINT, size=11),
            ],
            spacing=2,
        )
        self.master_icon_box = ft.Container(
            content=self.master_icon,
            width=54,
            height=54,
            border_radius=27,
            bgcolor=Theme.CARD_HI,
            alignment=ft.Alignment.CENTER,
            animate=Theme.animation(180),
        )
        self.master_touch = ft.Icon(ft.Icons.POWER_SETTINGS_NEW_ROUNDED, color=Theme.FAINT, size=20)
        self.master_body = ft.Row(
            [
                self.master_icon_box,
                self.master_text,
                ft.Container(content=self.master_touch, expand=True, alignment=ft.Alignment.CENTER_RIGHT),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        # Keep layout padding in a child, not in the interactive container.
        # Flet clips its ink wave to the padded content box otherwise, leaving
        # the thin outer "gray gutter" visible around a pressed master button.
        self.master_inner = ft.Container(
            content=self.master_body,
            padding=ft.Padding.symmetric(horizontal=18, vertical=14),
            expand=True,
            alignment=ft.Alignment.CENTER_LEFT,
        )
        self.master_card = ft.Container(
            content=self.master_inner,
            height=94,
            padding=0,
            border_radius=Theme.R_LG,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
            on_click=self._toggle_master,
            ink=True,
            ink_color=Theme.press_ink(0.30),
            animate=Theme.animation(180, EO),
        )

        # --- Brillo ---
        self.bri_value = ft.Text(self._t("common.percent_value", value=100), size=14, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
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
            tooltip=self._t("home.reset_brightness"),
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
                                    ft.Text(self._t("home.brightness_section"), style=Theme.LABEL),
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

        quick = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=12,
            controls=[
                self._quick(self._t("home.quick.cinema"), ft.Icons.MOVIE_ROUNDED, "#8b5cf6", lambda e: self.wiz.set_scene(18)),
                self._quick(self._t("home.quick.reading"), ft.Icons.MENU_BOOK_ROUNDED, "#f59e0b", lambda e: self.wiz.set_white(4000)),
                self._quick(self._t("home.quick.relax"), ft.Icons.SPA_ROUNDED, "#10b981", lambda e: self.wiz.set_scene(16)),
                self._quick(self._t("home.quick.party"), ft.Icons.CELEBRATION_ROUNDED, "#ec4899", lambda e: self.wiz.set_scene(4, speed=180)),
                self._quick(self._t("home.quick.warm"), ft.Icons.WB_TWILIGHT_ROUNDED, "#fb923c", lambda e: self.wiz.set_white(2700)),
                self._quick(self._t("home.quick.cool"), ft.Icons.AC_UNIT_ROUNDED, "#38bdf8", lambda e: self.wiz.set_white(6500)),
                self._quick(self._t("home.quick.reset"), ft.Icons.RESTART_ALT_ROUNDED, "#94a3b8", lambda e: self._reset_all()),
                self._quick(self._t("home.off"), ft.Icons.POWER_SETTINGS_NEW_ROUNDED, "#64748b", lambda e: self.wiz.turn_off()),
            ],
        )

        self.fav_row = ft.ResponsiveRow(breakpoints=PANEL_BREAKPOINTS, spacing=10, run_spacing=10)
        favs_card = self._card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(self._t("home.favorites_section"), style=Theme.LABEL),
                            ft.TextButton(self._t("home.manage"), icon=ft.Icons.STAR_ROUNDED, on_click=lambda e: self._go_favorites()),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.fav_row,
                ],
                spacing=10,
            )
        )

        self.controls = [self.header, self.linked_lights]
        self.controls.extend([self.master_card, bri_card, ft.Text(self._t("home.quick_section"), style=Theme.LABEL), quick, favs_card])
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
        inner = ft.Container(
            padding=12,
            expand=True,
            alignment=ft.Alignment.CENTER,
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
                        width=120,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=7,
            ),
        )
        return ft.Container(
            col={"xs": 6, "sm": 4, "md": 3, "lg": 2},
            height=88,
            padding=0,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=inner,
            on_click=action,
            ink=True,
            ink_color=Theme.press_ink(0.26),
            animate=Theme.animation(240, EO),
        )

    # ------------------------------------------------------------------ #
    def _apply_power_visual(self, is_on: bool):
        self.is_on = bool(is_on)
        if self.is_on:
            self.master_label.value = self._t("home.on")
            self.master_label.color = Theme.TEXT
            self.master_icon.icon = ft.Icons.POWER_SETTINGS_NEW_ROUNDED
            self.master_icon.color = "white"
            self.master_icon_box.bgcolor = None
            self.master_icon_box.gradient = ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=Theme.MASTER_ON_GRADIENT.colors,
            )
            self.master_icon_box.shadow = Theme.GLOW(Theme.PRIMARY, 0.24)
            self.master_touch.color = Theme.ACCENT
        else:
            self.master_label.value = self._t("home.off")
            self.master_label.color = Theme.TEXT
            self.master_icon.icon = ft.Icons.POWER_OFF_ROUNDED
            self.master_icon.color = Theme.TEXT
            self.master_icon_box.gradient = None
            self.master_icon_box.bgcolor = Theme.CARD_HI
            self.master_icon_box.shadow = None
            self.master_touch.color = Theme.FAINT

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
        self._bri_guard.touch(v, hold_seconds=0.85)
        self.bri_value.value = f"{v}%"
        self._safe(self.bri_value)
        self._emit_brightness(final=False)

    def _on_brightness_end(self, e):
        v = int(self.bri_slider.value)
        self._bri_guard.touch(v, hold_seconds=1.15)
        self._emit_brightness(final=True)

    def _reset_brightness(self, e=None):
        self._bri_guard.touch(100, hold_seconds=1.15)
        self.bri_slider.value = 100
        self.bri_value.value = "100%"
        self.wiz.set_brightness(100)
        supdate(self.bri_slider)
        supdate(self.bri_value)

    def _reset_all(self):
        self.wiz.reset_light()
        self.bri_slider.value = 100
        self.bri_value.value = self._t("common.percent_value", value=100)
        self._apply_power_visual(True)
        supdate(self)

    def _render_favorites(self):
        self.favorites = FavoritesManager()
        favs = self.favorites.get_favorites()[:6]
        self.fav_row.controls.clear()
        if not favs:
            self.fav_row.controls.append(ft.Text(self._t("home.favorites_empty"), color=Theme.MUTED, size=12))
        else:
            for fav in favs:
                self.fav_row.controls.append(self._fav_chip(fav))
        supdate(self.fav_row)

    def _fav_chip(self, fav: dict):
        ftype = fav.get("type")
        value = fav.get("value")
        color = str(value) if ftype == "rgb" else "#fbbf24" if ftype == "white" else "#8b5cf6"
        inner = ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            expand=True,
            alignment=ft.Alignment.CENTER_LEFT,
            content=ft.Row(
                [
                    ft.Container(width=16, height=16, border_radius=8, bgcolor=color),
                    ft.Text(translated_favorite_name(self.i18n, fav) or self._t("color_studio.favorite_default"), color=Theme.TEXT, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4},
            height=46,
            padding=0,
            border_radius=14,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=inner,
            on_click=lambda e, f=fav: self.wiz.apply_favorite(f),
            ink=True,
            ink_color=Theme.press_ink(0.24),
        )

    def _go_favorites(self):
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

    def _selection_changed(self) -> None:
        self.linked_lights.refresh()

    # ------------------------------------------------------------------ #
    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        viewport = Viewport(max(280.0, float(width)), max(320.0, float(height)))
        if viewport.mode == self._viewport.mode:
            self._viewport = viewport
            return
        self._viewport = viewport
        self.target_selector.set_viewport(width, height, update=False)
        self.master_inner.padding = ft.Padding.symmetric(
            horizontal=16 if viewport.compact else 20 if viewport.medium else 24,
            vertical=14,
        )
        self.master_touch.visible = not viewport.compact
        self.master_icon_box.width = 54 if viewport.compact else 64
        self.master_icon_box.height = 54 if viewport.compact else 64
        self.master_icon_box.border_radius = 17 if viewport.compact else 20
        if update:
            supdate(self.master_card)

    # ------------------------------------------------------------------ #
    def sync_state(self, state: dict):
        self._last_state = dict(state or {})
        if not mounted(self):
            return
        self.target_selector.refresh()
        self.linked_lights.refresh()
        if "dimming" in state and not self._bri_guard.blocks(state["dimming"], tolerance=1):
            self.bri_slider.value = state["dimming"]
            self.bri_value.value = self._t("common.percent_value", value=int(state["dimming"]))
        if "state" in state:
            self._apply_power_visual(bool(state["state"]))

        s = self.wiz.summary()
        count = int(s.get("count", 0) or 0)
        active = int(s.get("active", 0) or 0)
        extra = f" · {s['label']}" if s.get("label") else ""
        target_mode = s.get("target_mode", "single")
        if target_mode == "selected":
            mode = self._t("target.mode.selected")
        elif target_mode == "all":
            mode = self._t("routines.target.all")
        else:
            mode = self._t("routines.target.single")
        active_ip = s.get("active_ip") or "—"

        if active > 0:
            self.status_dot.bgcolor = Theme.SUCCESS
            self.status_text.value = self._t("home.status.active", active=active, count=count, extra=extra)
        elif count > 0:
            self.status_dot.bgcolor = Theme.MUTED
            self.status_text.value = self.i18n.translate_count("home.status.saved", count)
        else:
            self.status_dot.bgcolor = Theme.ERROR
            self.status_text.value = self._t("home.status.no_bulbs")
        self.target_text.value = self._t("home.target_summary", mode=mode, ip=active_ip)
        # No re-renderizar favoritos en cada tick de sync: evita repintados caros
        # mientras se arrastran sliders. El panel Favoritos refresca su propia vista.

        supdate(self)

    def _safe(self, control):
        supdate(control)
