import flet as ft
from ui.styles import Theme

# Importamos los paneles
from ui.components.home_panel import HomePanel
from ui.components.color_panel import ColorPanel

class WizzApp(ft.Container):
    def __init__(self, page, wiz_controller):
        super().__init__()
        self.page_ref = page
        self.wiz = wiz_controller
        
        # Configuración del Contenedor Principal
        self.expand = True
        self.gradient = Theme.MAIN_GRADIENT
        self.padding = 10
        
        self._init_components()

        self.content = self.tabs

    def _init_components(self):
        # 1. Crear paneles
        self.home_panel = HomePanel(self.wiz)
        self.color_panel = ColorPanel(self.wiz)
        
        # 2. Configurar Tabs
        # CORRECCIÓN: Usamos 'label' en vez de 'text'
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(label="Inicio", icon=ft.Icons.HOME, content=self.home_panel),
                ft.Tab(label="Colores", icon=ft.Icons.COLOR_LENS, content=self.color_panel),
            ],
            expand=True,
            divider_color="transparent",
            indicator_color=Theme.PRIMARY,
            label_color=Theme.PRIMARY,
            unselected_label_color=Theme.TEXT_MUTED
        )

    def update_ui(self, state):
        pass