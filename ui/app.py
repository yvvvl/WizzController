import flet as ft
from ui.theme import Theme
from ui.components.home_panel import HomePanel
from ui.components.color_panel import ColorPanel
from ui.components.scenes_panel import ScenesPanel


class WizzApp(ft.Container):
    """
    Layout principal: barra lateral de navegación + área de contenido.
    Los paneles se crean UNA vez y se conmutan (mantiene estado, cero rebuild).
    """

    def __init__(self, page: ft.Page, wiz_controller):
        super().__init__()
        self.page_ref = page
        self.wiz = wiz_controller
        self.expand = True
        self.gradient = Theme.GRADIENT

        # Paneles (instanciados una sola vez)
        self.panels = [
            HomePanel(self.wiz),
            ColorPanel(self.wiz),
            ScenesPanel(self.wiz),
        ]

        self.content_area = ft.Container(
            content=self.panels[0],
            expand=True,
            padding=ft.padding.only(left=8, right=18, top=18, bottom=18),
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
                            bgcolor=Theme.PRIMARY, alignment=ft.alignment.center,
                            shadow=Theme.GLOW(Theme.PRIMARY),
                        ),
                        ft.Text("WizZ", size=12, weight="bold", color=Theme.TEXT),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6,
                ),
                padding=ft.padding.only(top=18, bottom=24),
            ),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME_ROUNDED, label="Inicio"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PALETTE_OUTLINED, selected_icon=ft.Icons.PALETTE, label="Color"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.AUTO_AWESOME_OUTLINED, selected_icon=ft.Icons.AUTO_AWESOME, label="Escenas"),
            ],
            on_change=self._on_nav,
        )

        rail_wrap = ft.Container(
            content=self.rail,
            bgcolor=ft.Colors.with_opacity(0.6, Theme.SURFACE),
            border_radius=ft.border_radius.only(top_right=Theme.R_LG, bottom_right=Theme.R_LG),
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

    # Callback desde el controlador tras cada envío (refresco de estado)
    def update_ui(self, state: dict):
        try:
            self.panels[0].sync_state(state)
        except Exception:
            pass
