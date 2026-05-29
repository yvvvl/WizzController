import flet as ft
from ui.theme import Theme
from ui.components.home_panel import HomePanel
from ui.components.color_panel import ColorPanel
from ui.components.scenes_panel import ScenesPanel
from ui.components.settings_panel import SettingsPanel


class WizzApp(ft.Container):
    """Navegación lateral + área de contenido (Flet v1)."""

    def __init__(self, page: ft.Page, wiz_controller):
        super().__init__()
        self.page_ref = page
        self.wiz = wiz_controller
        self.expand = True
        self.gradient = Theme.GRADIENT

        self.panels = [
            HomePanel(self.wiz),
            ColorPanel(self.wiz),
            ScenesPanel(self.wiz),
            SettingsPanel(self.wiz),
        ]

        self.content_area = ft.Container(
            content=self.panels[0],
            expand=True,
            padding=ft.Padding.only(left=8, right=18, top=18, bottom=18),
        )

        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=92,
            bgcolor="transparent",
            indicator_color=ft.Colors.with_opacity(0.18, Theme.PRIMARY),
            group_alignment=-0.9,
            leading=ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color="white", size=22),
                            width=42, height=42, border_radius=12,
                            bgcolor=Theme.PRIMARY, alignment=ft.Alignment.CENTER,
                            shadow=Theme.GLOW(Theme.PRIMARY),
                        ),
                        ft.Text("WizZ", size=12, weight=ft.FontWeight.BOLD, color=Theme.TEXT),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6,
                ),
                padding=ft.Padding.only(top=18, bottom=24),
            ),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME_ROUNDED, label="Inicio"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PALETTE_OUTLINED, selected_icon=ft.Icons.PALETTE, label="Color"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.AUTO_AWESOME_OUTLINED, selected_icon=ft.Icons.AUTO_AWESOME, label="Escenas"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS_ROUNDED, label="Ajustes"),
            ],
            on_change=self._on_nav,
        )

        rail_wrap = ft.Container(
            content=self.rail,
            bgcolor=ft.Colors.with_opacity(0.6, Theme.SURFACE),
            border_radius=ft.BorderRadius.only(top_right=Theme.R_LG, bottom_right=Theme.R_LG),
        )

        self.content = ft.Row(
            [rail_wrap, self.content_area],
            expand=True, spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _on_nav(self, e):
        idx = e.control.selected_index
        self.content_area.content = self.panels[idx]
        self.content_area.update()

    def update_ui(self, state: dict):
        for panel in self.panels:
            fn = getattr(panel, "sync_state", None)
            if callable(fn):
                try:
                    fn(state)
                except Exception:
                    pass
