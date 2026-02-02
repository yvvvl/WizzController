"""
Nueva Interfaz de Usuario para WizzController.
DiseÃ±o profesional, minimalista, adaptable y de bajo consumo.
"""

import flet as ft
import logging
from ui.styles import Theme

# Paneles de la aplicaciÃ³n
from ui.components.home_panel import HomePanel
from ui.components.edit_panel import EditPanel
from ui.components.hotkeys_panel import HotkeysPanel
from ui.components.devices_panel import DevicesPanel

# Gestores de datos y lÃ³gica
from config.hotkeys_manager import HotkeysManager

class WizzApp(ft.Container):
    def __init__(self, page: ft.Page, wiz_manager):
        super().__init__(expand=True, bgcolor=Theme.BG_DARK)
        self._page = page
        self.wiz = wiz_manager
        self.logger = logging.getLogger(__name__)
        self.hk_manager = HotkeysManager(self.wiz)
        
        self.current_view_index = 0
        self._is_compact = False

        self._build_components()
        self._build_layout()
        
        self._page.on_resize = self._on_resize
        self._on_resize(None)

    def _build_components(self):
        """Inicializa todos los componentes y vistas de la UI."""
        
        # --- Vistas Principales ---
        self.home_view = HomePanel(self.wiz)
        self.edit_view = EditPanel(self.wiz, on_bg_change=self._update_background_gradient)
        self.hotkeys_view = HotkeysPanel(self._page, self.hk_manager)
        self.devices_view = DevicesPanel(self.wiz)
        
        self.views = [
            self.home_view,
            self.edit_view,
            self.hotkeys_view,
            self.devices_view,
        ]

        # --- Elementos de NavegaciÃ³n ---
        self.nav_destinations = [
            ft.NavigationRailDestination(icon=ft.icons.DASHBOARD_OUTLINED, selected_icon=ft.icons.DASHBOARD_ROUNDED, label="Control"),
            ft.NavigationRailDestination(icon=ft.icons.PALETTE_OUTLINED, selected_icon=ft.icons.PALETTE, label="Estudio"),
            ft.NavigationRailDestination(icon=ft.icons.KEYBOARD_COMMAND_KEY_OUTLINED, selected_icon=ft.icons.KEYBOARD_COMMAND_KEY, label="Atajos"),
            ft.NavigationRailDestination(icon=ft.icons.LIGHTBULB_OUTLINE, selected_icon=ft.icons.LIGHTBULB, label="Dispositivos"),
        ]

        # Barra lateral para escritorio
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=180,
            bgcolor=ft.Colors.with_opacity(0.03, "white"),
            group_alignment=-0.9,
            destinations=self.nav_destinations,
            on_change=self._on_nav_change,
            leading=ft.Container(
                content=ft.Icon(ft.icons.LIGHTBULB_CIRCLE, color=Theme.PRIMARY, size=32),
                padding=ft.padding.only(top=12, bottom=20),
            )
        )

        # Barra inferior para mÃ³vil/compacto
        self.nav_bar = ft.NavigationBar(
            selected_index=0,
            destinations=[
                ft.NavigationBarDestination(icon=d.icon, selected_icon=d.selected_icon, label=d.label)
                for d in self.nav_destinations
            ],
            on_change=self._on_nav_change,
            bgcolor="#111827",
            height=70,
        )

    def _build_layout(self):
        """Construye el layout principal de la aplicaciÃ³n."""
        
        self.sidebar = ft.Container(
            content=self.nav_rail,
            border=ft.border.only(right=ft.border.BorderSide(1, "#262626")),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
        
        self.content_area = ft.Container(
            content=self.views[0],
            expand=True,
            padding=ft.padding.all(20),
            gradient=Theme.MAIN_GRADIENT,
            alignment=Theme.ALIGN_TOP_LEFT,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_IN),
        )
        
        self.content = ft.Row(
            controls=[self.sidebar, self.content_area],
            spacing=0,
            expand=True,
        )

    def _on_nav_change(self, e):
        """Maneja el cambio de vista desde la navegaciÃ³n."""
        self.current_view_index = e.control.selected_index
        
        # Sincronizar ambas barras de navegaciÃ³n
        self.nav_rail.selected_index = self.current_view_index
        self.nav_bar.selected_index = self.current_view_index
        
        # Cambiar el contenido
        self.content_area.content = self.views[self.current_view_index]
        
        # Pausar/reanudar refrescos de vistas pesadas
        is_devices_view = self.current_view_index == 3
        if hasattr(self.devices_view, "set_auto_refresh"):
            self.devices_view.set_auto_refresh(is_devices_view)

        self.update()

    def _on_resize(self, e):
        """Ajusta el layout en funciÃ³n del tamaÃ±o de la ventana."""
        page_width = getattr(self._page, "width", 0) or 0
        is_now_compact = page_width < 800
        
        if is_now_compact != self._is_compact:
            self._is_compact = is_now_compact
            
            if self._is_compact:
                # Modo Compacto
                self.sidebar.visible = False
                self._page.navigation_bar = self.nav_bar
            else:
                # Modo Escritorio
                self.sidebar.visible = True
                self._page.navigation_bar = None
            
            self._page.update()

    def _update_background_gradient(self, color: str):
        """Actualiza el gradiente de fondo con un color de acento."""
        if not color: return
        
        accent_color = ft.Colors.with_opacity(0.15, color)
        
        self.content_area.gradient = ft.LinearGradient(
            begin=Theme.ALIGN_TOP_LEFT,
            end=Theme.ALIGN_BOTTOM_RIGHT,
            colors=[Theme.BG_DARK, accent_color, Theme.BG_DARK],
            stops=[0.1, 0.5, 0.9],
        )
        self.content_area.update()

    def sync_state(self, state: dict):
        """Sincroniza el estado de las bombillas con la UI."""
        if self.current_view_index == 0 and hasattr(self.home_view, "sync_state"):
            self.home_view.sync_state(state)

    def set_background_mode(self, enabled: bool):
        """Pone la UI en modo de bajo consumo cuando estÃ¡ en segundo plano."""
        if hasattr(self.devices_view, "set_auto_refresh"):
            # Solo refrescar si la vista estÃ¡ activa y la app no estÃ¡ en segundo plano
            is_devices_view = self.current_view_index == 3
            self.devices_view.set_auto_refresh(is_devices_view and not enabled)
