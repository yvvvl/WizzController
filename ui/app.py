from __future__ import annotations

import asyncio

import flet as ft

from config.app_runtime_manager import AppRuntimeManager
from localization import RuntimeLanguagePreference, get_manager, translated_navigation

from ui.components.color_panel import ColorPanel
from ui.components.favorites_panel import FavoritesPanel
from ui.components.home_panel import HomePanel
from ui.components.hotkeys_panel import HotkeysPanel
from ui.components.routines_panel import RoutinesPanel
from ui.components.scenes_panel import ScenesPanel
from ui.components.settings_panel import SettingsPanel
from ui.responsive import Viewport, safe_number
from ui.theme import Theme, supdate


class WizzApp(ft.Container):
    """Navegación lateral + área de contenido con layout desktop responsivo.

    El resize se resuelve por breakpoints y medidas cuantizadas dentro de cada
    panel. No se reconstruye toda la app en cada píxel ni se toca el ciclo de
    vida de ventana/tray.
    """

    def __init__(
        self,
        page: ft.Page,
        wiz_controller,
        hotkeys_manager=None,
        platform_services=None,
    ):
        # Each panel owns its vertical scroll area.  Do not clip the complete
        # application shell here: on Windows that clips the first row while a
        # panel is in motion and produces a visible horizontal seam.
        super().__init__()
        self.page_ref = page
        self.wiz = wiz_controller
        self.hotkeys_manager = hotkeys_manager
        self.platform_services = platform_services
        self.runtime = AppRuntimeManager()
        self.i18n = get_manager()
        self.language_preference = RuntimeLanguagePreference(self.runtime)
        self.i18n.set_preference(self.language_preference.load())
        self.expand = True
        self.bgcolor = Theme.BG
        self.gradient = Theme.GRADIENT
        self.selected_index = 0
        self._last_state: dict = {}
        self._viewport = Viewport(1080, 720)
        self._shell_mode = ""
        self._transition_id = 0
        self._rail_width = 92.0
        self.hotkeys_available = bool(
            self.hotkeys_manager is not None and self.hotkeys_manager.available
        )

        self.panels = [
            HomePanel(self.wiz, i18n=self.i18n),
            ColorPanel(
                self.wiz,
                i18n=self.i18n,
                on_favorites_changed=self.refresh_favorites_panel,
            ),
            ScenesPanel(self.wiz, i18n=self.i18n),
            FavoritesPanel(self.wiz, i18n=self.i18n),
            RoutinesPanel(self.wiz, i18n=self.i18n),
            SettingsPanel(
                self.wiz,
                i18n=self.i18n,
                on_language_change=self.set_language_preference,
                runtime=self.runtime,
                platform_services=self.platform_services,
                on_theme_change=self.set_theme_preference,
            ),
            HotkeysPanel(self.wiz, manager=self.hotkeys_manager, i18n=self.i18n),
        ]
        self._hotkeys_index = len(self.panels) - 1
        for panel in self.panels:
            self._add_panel_header_breathing_room(panel)

        self.content_area = ft.Container(
            content=self.panels[0],
            expand=True,
            bgcolor=Theme.BG,
            # The content viewport begins directly below the title strip. This
            # avoids a second empty band above every panel when it scrolls.
            padding=ft.Padding.only(left=8, right=18, top=0, bottom=0),
            # Clip *only* this viewport: panels cannot paint under the window
            # chrome, while the root page and its title strip stay fixed.
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            # The client interpolates these two properties at native frame
            # rate. Navigation only sends start/swap/end updates from Python.
            animate_opacity=Theme.animation(210),
            animate_offset=Theme.animation(210),
        )

        self.logo_label = ft.Text("WizZ", size=12, weight=ft.FontWeight.BOLD, color=Theme.TEXT)
        self.logo_box = ft.Container(
            content=ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color="white", size=22),
            width=42,
            height=42,
            border_radius=12,
            bgcolor=Theme.PRIMARY,
            alignment=ft.Alignment.CENTER,
            shadow=Theme.GLOW(Theme.PRIMARY),
        )
        self.leading = ft.Container(
            content=ft.Column(
                [self.logo_box, self.logo_label],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
            padding=ft.Padding.only(top=14, bottom=12),
        )

        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=72,
            bgcolor="transparent",
            indicator_color=ft.Colors.with_opacity(0.18, Theme.PRIMARY),
            group_alignment=-0.88,
            leading=self.leading,
            scrollable=True,
            destinations=[
                ft.NavigationRailDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME_ROUNDED, label=self._t("nav.home")),
                ft.NavigationRailDestination(icon=ft.Icons.PALETTE_OUTLINED, selected_icon=ft.Icons.PALETTE, label=self._t("nav.color")),
                ft.NavigationRailDestination(icon=ft.Icons.AUTO_AWESOME_OUTLINED, selected_icon=ft.Icons.AUTO_AWESOME, label=self._t("nav.scenes")),
                ft.NavigationRailDestination(icon=ft.Icons.STAR_BORDER_ROUNDED, selected_icon=ft.Icons.STAR_ROUNDED, label=self._t("nav.favorites")),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ROCKET_LAUNCH_OUTLINED,
                    selected_icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
                    label=self._t("nav.routines"),
                ),
                ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS_ROUNDED, label=self._t("nav.settings")),
                *([self._hotkeys_destination()] if self.hotkeys_available else []),
            ],
            trailing=self._disabled_hotkeys_indicator() if not self.hotkeys_available else None,
            on_change=self._on_nav,
        )

        self.rail_wrap = ft.Container(
            width=92,
            content=self.rail,
            gradient=Theme.RAIL_GRADIENT,
            border_radius=ft.BorderRadius.only(top_right=Theme.R_LG, bottom_right=Theme.R_LG),
        )

        self.shell_body = ft.Row(
            [self.rail_wrap, self.content_area],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.shell_viewport = ft.Container(
            content=self.shell_body,
            expand=True,
            bgcolor=Theme.BG,
            # Seal the panel canvas at the lower edge too: otherwise Flutter
            # can briefly expose the root page behind a scrolled panel.
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        self.window_chrome = self._build_window_chrome()
        self.content = ft.Column(
            [self.window_chrome, self.shell_viewport],
            expand=True,
            spacing=0,
        )

        initial_w = safe_number(getattr(page, "width", None), safe_number(getattr(page.window, "width", None), 1080))
        initial_h = safe_number(getattr(page, "height", None), safe_number(getattr(page.window, "height", None), 720))
        # ``expand`` alone is not enough when the root Page has more than one
        # layout pass. Keeping a concrete canvas height prevents Page from
        # becoming a second scroll parent above the panel currently shown.
        self.height = initial_h
        self.set_viewport(initial_w, initial_h, update=False)
        self._language_unsubscribe = self.i18n.subscribe(self._on_language_changed)

    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    @staticmethod
    def _add_panel_header_breathing_room(panel) -> None:
        """Separate the first heading from chrome without adding a scroll gap.

        The margin belongs to the panel's first child, so it scrolls away with
        the content. A parent padding would create a permanent black band at
        the top of every scrolled screen.
        """
        controls = getattr(panel, "controls", None)
        if not controls:
            return
        try:
            controls[0].margin = ft.Margin.only(top=10)
        except Exception:
            pass

    def _build_window_chrome(self) -> ft.Container:
        """A small themed title strip that preserves native move/minimize/close."""
        mark = ft.Container(
            content=ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, size=15, color="white"),
            width=24,
            height=24,
            border_radius=8,
            bgcolor=Theme.PRIMARY,
            alignment=ft.Alignment.CENTER,
        )
        drag_content = ft.Container(
            content=ft.Row(
                [mark, ft.Text("WizZ Desktop", color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600)],
                spacing=8,
            ),
            padding=ft.Padding.only(left=14, right=10),
            expand=True,
            alignment=ft.Alignment.CENTER_LEFT,
        )
        drag = ft.WindowDragArea(drag_content, maximizable=False, expand=True)
        minimize = ft.IconButton(
            icon=ft.Icons.REMOVE_ROUNDED,
            icon_color=Theme.MUTED,
            icon_size=18,
            tooltip=self._t("window.minimize"),
            on_click=self._minimize_window,
        )
        close = ft.IconButton(
            icon=ft.Icons.CLOSE_ROUNDED,
            icon_color=Theme.MUTED,
            icon_size=17,
            tooltip=self._t("window.close"),
            on_click=self._request_close_window,
        )
        return ft.Container(
            height=38,
            gradient=Theme.RAIL_GRADIENT,
            border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.42, Theme.STROKE))),
            content=ft.Row([drag, minimize, close], spacing=0),
        )

    def _minimize_window(self, _event=None) -> None:
        try:
            self.page_ref.window.minimized = True
            self.page_ref.update()
        except Exception:
            pass

    def _request_close_window(self, _event=None) -> None:
        async def close_native_window() -> None:
            try:
                await self.page_ref.window.close()
            except Exception:
                # The normal native titlebar is unavailable here, but the tray
                # remains the safe fallback when the platform refuses close().
                tray = getattr(self.page_ref, "_wizz_tray", None)
                hide = getattr(tray, "hide_window", None)
                if callable(hide):
                    hide()

        try:
            self.page_ref.run_task(close_native_window)
        except Exception:
            pass

    def _hotkeys_destination(self):
        return ft.NavigationRailDestination(
            icon=ft.Icons.KEYBOARD_OUTLINED,
            selected_icon=ft.Icons.KEYBOARD_ROUNDED,
            label=self._t("nav.hotkeys"),
        )

    def _disabled_hotkeys_indicator(self):
        """A non-interactive, explanatory Linux beta capability indicator."""
        self.hotkeys_trailing_label = ft.Text(
            self._t("nav.hotkeys"), color=Theme.MUTED, size=11, text_align=ft.TextAlign.CENTER
        )
        self.hotkeys_trailing_status = ft.Text(
            self._t("hotkeys.linux_disabled_short"), color=Theme.FAINT, size=9, text_align=ft.TextAlign.CENTER
        )
        return ft.Container(
            tooltip=self._t("hotkeys.linux_disabled_tooltip"),
            padding=ft.Padding.only(top=10, bottom=14),
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.KEYBOARD_OUTLINED, color=Theme.MUTED, size=22),
                    self.hotkeys_trailing_label,
                    self.hotkeys_trailing_status,
                ],
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def set_language_preference(self, preference: str) -> str:
        normalized = self.language_preference.save(preference)
        changed = self.i18n.set_preference(normalized)
        if not changed:
            self._on_language_changed(self.i18n.language)
        return self.i18n.language

    def set_theme_preference(self, theme: str, reduced_motion: bool) -> None:
        """Persist and apply the visual system without interrupting WiZ I/O."""
        self.runtime.update(ui_theme=str(theme), reduced_motion=bool(reduced_motion))
        Theme.configure(theme, reduced_motion=bool(reduced_motion))

        try:
            self.page_ref.bgcolor = Theme.BG
            self.page_ref.window.bgcolor = Theme.BG
            self.page_ref.theme_mode = ft.ThemeMode.LIGHT if Theme.NAME == "light" else ft.ThemeMode.DARK
            self.page_ref.theme = Theme.flet_theme()
        except Exception:
            pass

        self.gradient = Theme.GRADIENT
        self.bgcolor = Theme.BG
        self.content_area.bgcolor = Theme.BG
        self.shell_viewport.bgcolor = Theme.BG
        self.rail_wrap.gradient = Theme.RAIL_GRADIENT
        self.rail.indicator_color = ft.Colors.with_opacity(0.18, Theme.PRIMARY)
        self.window_chrome = self._build_window_chrome()
        self.content.controls[0] = self.window_chrome

        # Panels build controls from Theme tokens. Rebuilding them in place
        # changes their colors immediately while preserving controller state.
        for panel in self.panels:
            rebuild = getattr(panel, "set_language", None)
            if callable(rebuild):
                try:
                    rebuild(self.i18n.language)
                    self._add_panel_header_breathing_room(panel)
                except Exception:
                    pass
        supdate(self)

    def refresh_favorites_panel(self) -> None:
        """Propagate a saved Color Studio favorite without an app restart."""
        if len(self.panels) <= 3:
            return
        refresh = getattr(self.panels[3], "refresh_favorites", None)
        if callable(refresh):
            refresh()

    def _on_language_changed(self, language: str) -> None:
        labels = list(translated_navigation(self.i18n))
        visible_labels = labels if self.hotkeys_available else labels[:-1]
        for destination, label in zip(self.rail.destinations, visible_labels):
            destination.label = label
        if not self.hotkeys_available:
            self.hotkeys_trailing_label.value = self._t("nav.hotkeys")
            self.hotkeys_trailing_status.value = self._t("hotkeys.linux_disabled_short")

        try:
            self.page_ref.title = self._t("app.name")
        except Exception:
            pass

        for panel in self.panels:
            handler = getattr(panel, "set_language", None)
            if callable(handler):
                try:
                    handler(language)
                    self._add_panel_header_breathing_room(panel)
                except Exception:
                    pass

        supdate(self.rail)
        supdate(self.content_area)

    # ------------------------------------------------------------------ #
    # Responsive shell
    # ------------------------------------------------------------------ #
    def handle_page_resize(self, e) -> None:
        width = safe_number(getattr(e, "width", None), self._viewport.width)
        height = safe_number(getattr(e, "height", None), self._viewport.height)
        self.set_viewport(width, height, update=True)

    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        viewport = Viewport(max(320.0, float(width)), max(420.0, float(height)))
        self._viewport = viewport
        self.height = viewport.height

        # El shell usa umbrales de página; los paneles reciben el ancho útil.
        if viewport.width < 760:
            shell_mode = "compact"
            rail_width = 62.0
            rail_min = 56.0
            label_type = ft.NavigationRailLabelType.NONE
            padding = ft.Padding.only(left=6, right=10, top=0, bottom=0)
            self.logo_label.visible = False
            self.leading.padding = ft.Padding.only(top=10, bottom=8)
        elif viewport.width < 1040:
            shell_mode = "medium"
            rail_width = 78.0
            rail_min = 64.0
            label_type = ft.NavigationRailLabelType.SELECTED
            padding = ft.Padding.only(left=8, right=14, top=0, bottom=0)
            self.logo_label.visible = True
            self.leading.padding = ft.Padding.only(top=12, bottom=10)
        else:
            shell_mode = "wide"
            rail_width = 96.0
            rail_min = 72.0
            label_type = ft.NavigationRailLabelType.ALL
            padding = ft.Padding.only(left=8, right=18, top=0, bottom=0)
            self.logo_label.visible = True
            self.leading.padding = ft.Padding.only(top=14, bottom=12)

        shell_changed = shell_mode != self._shell_mode
        self._shell_mode = shell_mode
        self._rail_width = rail_width
        self.rail_wrap.width = rail_width
        self.rail.min_width = rail_min
        self.rail.label_type = label_type
        self.content_area.padding = padding

        horizontal_padding = float(padding.left or 0) + float(padding.right or 0)
        vertical_padding = float(padding.top or 0) + float(padding.bottom or 0)
        panel_width = max(280.0, viewport.width - rail_width - horizontal_padding)
        panel_height = max(320.0, viewport.height - 38.0 - vertical_padding)
        self._apply_viewport_to_panel(self.selected_index, panel_width, panel_height, update=update)

        if update and shell_changed:
            supdate(self.rail_wrap)
            supdate(self.rail)
            supdate(self.content_area)

    def _apply_viewport_to_panel(self, idx: int, width: float, height: float, *, update: bool) -> None:
        if idx < 0 or idx >= len(self.panels):
            return
        fn = getattr(self.panels[idx], "set_viewport", None)
        if callable(fn):
            try:
                fn(width, height, update=update)
            except TypeError:
                try:
                    fn(width, height)
                except Exception:
                    pass
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Navegación / estado
    # ------------------------------------------------------------------ #
    def _sync_panel(self, idx: int, state: dict):
        if idx < 0 or idx >= len(self.panels):
            return
        fn = getattr(self.panels[idx], "sync_state", None)
        if callable(fn):
            try:
                fn(state)
            except Exception:
                pass

    def _on_nav(self, e):
        index = int(e.control.selected_index or 0)
        if index == self._hotkeys_index and not self.hotkeys_available:
            e.control.selected_index = self.selected_index
            supdate(e.control)
            return
        self.navigate_to(index)

    def navigate_to(self, idx: int) -> None:
        """Cambia de panel conservando el viewport y el estado sincronizado.

        Los accesos internos (por ejemplo, "Ver todos" en Color) deben usar
        este método en lugar de manipular ``content_area`` directamente. Así
        el panel de destino recibe su ancho útil antes de dibujarse y no queda
        con el layout calculado para otro tamaño de ventana.
        """

        idx = max(0, min(len(self.panels) - 1, int(idx)))
        if idx == self._hotkeys_index and not self.hotkeys_available:
            return
        self.rail.selected_index = idx
        self.selected_index = idx
        supdate(self.rail)
        self._transition_id += 1
        transition_id = self._transition_id
        if Theme.REDUCED_MOTION:
            self._commit_navigation(idx)
            return
        try:
            self.page_ref.run_task(self._animate_navigation, idx, transition_id)
        except Exception:
            self._commit_navigation(idx)

    def _commit_navigation(self, idx: int) -> None:
        self.content_area.content = self.panels[idx]
        padding = self.content_area.padding
        horizontal_padding = float(padding.left or 0) + float(padding.right or 0)
        vertical_padding = float(padding.top or 0) + float(padding.bottom or 0)
        panel_width = max(280.0, self._viewport.width - self._rail_width - horizontal_padding)
        panel_height = max(320.0, self._viewport.height - 38.0 - vertical_padding)
        self._apply_viewport_to_panel(idx, panel_width, panel_height, update=False)
        self._sync_panel(idx, self._last_state)
        supdate(self.content_area)

    async def _animate_navigation(self, idx: int, transition_id: int) -> None:
        """Native-rate crossfade: fade old panel, swap, reveal new panel."""
        self.content_area.opacity = 0.08
        self.content_area.offset = (-0.018, 0)
        supdate(self.content_area)
        await asyncio.sleep(0.225)

        if transition_id != self._transition_id:
            return
        self._commit_navigation(idx)
        await asyncio.sleep(0.028)
        if transition_id != self._transition_id:
            return
        self.content_area.opacity = 1.0
        self.content_area.offset = (0, 0)
        supdate(self.content_area)

    def update_ui(self, state: dict):
        next_state = dict(state or {})

        # Live colour changes may acknowledge 20-30 times per second. While
        # Color Studio owns an active drag, refreshing Home's light cards for
        # every acknowledgement starves the pointer/thumbnail update. Keep the
        # latest snapshot and render it after the gesture releases.
        active_panel = self.panels[self.selected_index] if 0 <= self.selected_index < len(self.panels) else None
        if bool(getattr(active_panel, "is_picker_dragging", False)):
            self._last_state = next_state
            return

        # Los callbacks de discovery pueden cambiar la lista de dispositivos sin
        # cambiar el estado luminoso (state/dimming/RGB). Antes se descartaban por
        # igualdad y Ajustes quedaba con el spinner activo aunque discovery ya
        # hubiera terminado. Los paneles que dependan de metadata pueden optar a
        # refrescarse aun cuando el estado de luz sea idéntico.
        if next_state == self._last_state:
            idx = int(self.selected_index)
            if 0 <= idx < len(self.panels):
                panel = self.panels[idx]
                if bool(getattr(panel, "refresh_on_equal_state", False)):
                    self._sync_panel(idx, next_state)
            return

        self._last_state = next_state
        indices = {0, self.selected_index}
        for idx in indices:
            self._sync_panel(idx, self._last_state)
