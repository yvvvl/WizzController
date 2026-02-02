import flet as ft
import logging
from ui.styles import Theme
from ui.components.home_panel import HomePanel
from ui.components.color_panel_v3 import ColorPanelV3
from ui.components.hotkeys_panel import HotkeysPanel
from ui.components.devices_panel import DevicesPanel
from config.hotkeys_manager import HotkeysManager

class WizzApp:
    def __init__(self, page: ft.Page, wiz_manager):
        self.logger = logging.getLogger(__name__)
        self.page = page
        self.wiz = wiz_manager
        self.hk_manager = HotkeysManager(self.wiz)
        
        self.current_index = 0
        self._background_mode = False
        self._last_state = None
        
        self._setup_page()
        self._init_components()
        self._build_layout()
        
    def _setup_page(self):
        self.page.title = "Wizz AI"
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = Theme.BG_DARK

        # No forzar geometrÃ­a aquÃ­: main.py restaura tamaÃ±o/posiciÃ³n desde config.
        # Mantener sÃ³lo mÃ­nimos razonables.
        self.page.window.min_width = 800
        self.page.window.min_height = 600

        # Evitar descargar fuentes remotas en startup (mÃ¡s liviano y funciona offline).
        # Usar la tipografÃ­a por defecto del sistema.

    def _init_components(self):
        self.home_panel = HomePanel(self.wiz)
        self.color_panel = ColorPanelV3(self.wiz, on_bg_change=self._update_bg_accent)
        self.hotkeys_panel = HotkeysPanel(self.page, self.hk_manager)
        self.devices_panel = DevicesPanel(self.wiz)

        self.destinations = [
            ft.NavigationRailDestination(icon=ft.icons.DASHBOARD_ROUNDED, selected_icon=ft.icons.DASHBOARD, label="Control"),
            ft.NavigationRailDestination(icon=ft.icons.COLOR_LENS_OUTLINED, selected_icon=ft.icons.COLOR_LENS, label="Estudio"),
            ft.NavigationRailDestination(icon=ft.icons.KEYBOARD_OUTLINED, selected_icon=ft.icons.KEYBOARD, label="Atajos"),
            ft.NavigationRailDestination(icon=ft.icons.LIGHTBULB_OUTLINE, selected_icon=ft.icons.LIGHTBULB, label="Dispositivos"),
        ]

        self.views = [self.home_panel, self.color_panel, self.hotkeys_panel, self.devices_panel]

        # Barra Lateral (Desktop)
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=180,
            bgcolor=ft.Colors.TRANSPARENT,
            indicator_color=Theme.PRIMARY_GLOW,
            indicator_shape=ft.RoundedRectangleBorder(radius=10),
            group_alignment=-0.9,
            destinations=self.destinations,
            on_change=self._on_nav_change
        )

        # Barra Inferior (Mobile/Compact)
        self.nav_bar = ft.NavigationBar(
            selected_index=0,
            destinations=[
                ft.NavigationBarDestination(
                    icon=d.icon, 
                    selected_icon=getattr(d, "selected_icon", d.icon), 
                    label=d.label
                ) 
                for d in self.destinations
            ],
            on_change=self._on_nav_change,
            bgcolor="#111827",
            height=70,
            visible=False 
        )

    def _build_layout(self):
        self.content_area = ft.Container(
            content=self.home_panel,
            expand=True,
            padding=ft.padding.all(0),
            gradient=Theme.MAIN_GRADIENT,
            alignment=Theme.ALIGN_TOP_LEFT
        )

        self.sidebar_container = ft.Container(
            content=self.nav_rail,
            visible=True,
            width=90,
            gradient=Theme.SIDEBAR_GRADIENT,
            border=ft.border.only(right=ft.border.BorderSide(1, ft.Colors.with_opacity(0.1, "white"))),
        )

        self.layout = ft.Row(
            controls=[self.sidebar_container, self.content_area],
            expand=True,
            spacing=0
        )
        
        self.page.add(self.layout)
        self.page.on_resized = self.handle_resize
        self.handle_resize(None)

    def _on_nav_change(self, e):
        idx = e.control.selected_index
        self.current_index = idx
        
        self.nav_rail.selected_index = idx
        self.nav_bar.selected_index = idx
        
        # Pausar refrescos de vistas pesadas cuando no estÃ¡n activas
        try:
            if hasattr(self.devices_panel, "set_auto_refresh"):
                self.devices_panel.set_auto_refresh(bool(idx == 3 and not self._background_mode))
        except Exception:
            pass

        self.content_area.content = self._get_view_for_index(idx)
        self.page.update()

        # Si volvemos a foreground y habÃ­a estado pendiente, aplicarlo una vez.
        if not self._background_mode and self._last_state is not None:
            try:
                self._apply_state_now(self._last_state)
            except Exception:
                pass

    def _get_view_for_index(self, index):
        if 0 <= index < len(self.views):
            return self.views[index]
        return ft.Container(content=ft.Text("En construcciÃ³n", color="white"))

    def _update_bg_accent(self, color):
        if not color: return
        try:
            accent_color = ft.Colors.with_opacity(0.1, color)
        except Exception:
            self.logger.exception("No se pudo aplicar opacidad al color")
            accent_color = "#1A" + color.lstrip("#")
            
        self.content_area.gradient = ft.LinearGradient(
            begin=Theme.ALIGN_TOP_LEFT,
            end=Theme.ALIGN_BOTTOM_RIGHT,
            colors=[Theme.BG_DARK, accent_color, Theme.BG_DARK],
        )
        self.content_area.update()

    def handle_resize(self, e):
        width = self.page.window.width
        if width < 800:
            self.sidebar_container.visible = False
            self.nav_bar.visible = True
            self.page.navigation_bar = self.nav_bar
            self.page.padding = 0
        else:
            self.sidebar_container.visible = True
            self.nav_bar.visible = False
            self.page.navigation_bar = None
            self.page.padding = 0
        self.page.update()
        
    def update_ui(self, state):
        # Puede venir desde hilos de fondo (LightController). Siempre saltar al hilo UI.
        try:
            p = self.page
        except Exception:
            return

        # En segundo plano, evita gastar CPU en updates de UI; cachea el Ãºltimo estado.
        if self._background_mode:
            self._last_state = state
            return

        try:
            p.run_task(self._ui_apply_state, state)
        except Exception:
            # fallback: si run_task no estÃ¡ disponible o la sesiÃ³n estÃ¡ cerrando
            try:
                self._apply_state_now(state)
            except Exception:
                pass

    async def _ui_apply_state(self, state, *args):
        self._apply_state_now(state)

    def _apply_state_now(self, state):
        self._last_state = state
        if isinstance(self.content_area.content, HomePanel):
            self.content_area.content.sync_state(state)

    def set_background_mode(self, enabled: bool) -> None:
        """Activa modo segundo plano: pausa refrescos y evita updates de UI."""
        self._background_mode = bool(enabled)
        # DevicesPanel es el mÃ¡s costoso (thread + updates).
        try:
            if hasattr(self.devices_panel, "set_auto_refresh"):
                self.devices_panel.set_auto_refresh(bool((self.current_index == 3) and not self._background_mode))
        except Exception:
            pass

        # Al volver, aplicar el Ãºltimo estado cacheado.
        if not self._background_mode and self._last_state is not None:
            try:
                self._apply_state_now(self._last_state)
            except Exception:
                pass
