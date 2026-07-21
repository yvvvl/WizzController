from __future__ import annotations

import flet as ft

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

    def __init__(self, page: ft.Page, wiz_controller, hotkeys_manager=None):
        super().__init__()
        self.page_ref = page
        self.wiz = wiz_controller
        self.hotkeys_manager = hotkeys_manager
        self.expand = True
        self.gradient = Theme.GRADIENT
        self.selected_index = 0
        self._last_state: dict = {}
        self._viewport = Viewport(1080, 720)
        self._shell_mode = ""
        self._rail_width = 92.0

        self.panels = [
            HomePanel(self.wiz),
            ColorPanel(self.wiz),
            ScenesPanel(self.wiz),
            FavoritesPanel(self.wiz),
            RoutinesPanel(self.wiz),
            SettingsPanel(self.wiz),
            HotkeysPanel(self.wiz, manager=self.hotkeys_manager),
        ]

        self.content_area = ft.Container(
            content=self.panels[0],
            expand=True,
            bgcolor=Theme.BG,
            padding=ft.Padding.only(left=8, right=18, top=18, bottom=18),
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
                ft.NavigationRailDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME_ROUNDED, label="Inicio"),
                ft.NavigationRailDestination(icon=ft.Icons.PALETTE_OUTLINED, selected_icon=ft.Icons.PALETTE, label="Color"),
                ft.NavigationRailDestination(icon=ft.Icons.AUTO_AWESOME_OUTLINED, selected_icon=ft.Icons.AUTO_AWESOME, label="Escenas"),
                ft.NavigationRailDestination(icon=ft.Icons.STAR_BORDER_ROUNDED, selected_icon=ft.Icons.STAR_ROUNDED, label="Favs"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ROCKET_LAUNCH_OUTLINED,
                    selected_icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
                    label="Rutinas",
                ),
                ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS_ROUNDED, label="Ajustes"),
                ft.NavigationRailDestination(icon=ft.Icons.KEYBOARD_OUTLINED, selected_icon=ft.Icons.KEYBOARD_ROUNDED, label="Hotkeys"),
            ],
            on_change=self._on_nav,
        )

        self.rail_wrap = ft.Container(
            width=92,
            content=self.rail,
            bgcolor=ft.Colors.with_opacity(0.6, Theme.SURFACE),
            border_radius=ft.BorderRadius.only(top_right=Theme.R_LG, bottom_right=Theme.R_LG),
        )

        self.content = ft.Row(
            [self.rail_wrap, self.content_area],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        initial_w = safe_number(getattr(page, "width", None), safe_number(getattr(page.window, "width", None), 1080))
        initial_h = safe_number(getattr(page, "height", None), safe_number(getattr(page.window, "height", None), 720))
        self.set_viewport(initial_w, initial_h, update=False)

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

        # El shell usa umbrales de página; los paneles reciben el ancho útil.
        if viewport.width < 760:
            shell_mode = "compact"
            rail_width = 62.0
            rail_min = 56.0
            label_type = ft.NavigationRailLabelType.NONE
            padding = ft.Padding.only(left=6, right=10, top=12, bottom=12)
            self.logo_label.visible = False
            self.leading.padding = ft.Padding.only(top=10, bottom=8)
        elif viewport.width < 1040:
            shell_mode = "medium"
            rail_width = 78.0
            rail_min = 64.0
            label_type = ft.NavigationRailLabelType.SELECTED
            padding = ft.Padding.only(left=8, right=14, top=15, bottom=15)
            self.logo_label.visible = True
            self.leading.padding = ft.Padding.only(top=12, bottom=10)
        else:
            shell_mode = "wide"
            rail_width = 96.0
            rail_min = 72.0
            label_type = ft.NavigationRailLabelType.ALL
            padding = ft.Padding.only(left=8, right=18, top=18, bottom=18)
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
        panel_height = max(320.0, viewport.height - vertical_padding)
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
        self.navigate_to(int(e.control.selected_index or 0))

    def navigate_to(self, idx: int) -> None:
        """Cambia de panel conservando el viewport y el estado sincronizado.

        Los accesos internos (por ejemplo, "Ver todos" en Color) deben usar
        este método en lugar de manipular ``content_area`` directamente. Así
        el panel de destino recibe su ancho útil antes de dibujarse y no queda
        con el layout calculado para otro tamaño de ventana.
        """

        idx = max(0, min(len(self.panels) - 1, int(idx)))
        self.rail.selected_index = idx
        self.selected_index = idx
        self.content_area.content = self.panels[idx]

        padding = self.content_area.padding
        horizontal_padding = float(padding.left or 0) + float(padding.right or 0)
        vertical_padding = float(padding.top or 0) + float(padding.bottom or 0)
        panel_width = max(280.0, self._viewport.width - self._rail_width - horizontal_padding)
        panel_height = max(320.0, self._viewport.height - vertical_padding)
        self._apply_viewport_to_panel(idx, panel_width, panel_height, update=False)

        supdate(self.rail)
        supdate(self.content_area)
        self._sync_panel(idx, self._last_state)

    def update_ui(self, state: dict):
        next_state = dict(state or {})
        if next_state == self._last_state:
            return
        self._last_state = next_state
        indices = {0, self.selected_index}
        for idx in indices:
            self._sync_panel(idx, self._last_state)
