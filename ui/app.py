import flet as ft
from ui.components.header import Header
from ui.components.color_panel import ColorPanel

class WizzApp:
    def __init__(self, page: ft.Page, wiz_manager):
        self.page = page
        self.wiz = wiz_manager

        self.header = Header(self.wiz) 
        
        # Conectamos la señal de resize aquí
        self.color_panel = ColorPanel(
            self.wiz, 
            on_bg_change=self._update_bg,
            on_resize_request=self._apply_window_resize
        )
        
        self.root_container = ft.Container(
            expand=True,
            bgcolor="#111827", 
            animate=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
            content=ft.Column(
                controls=[
                    self.header,
                    ft.Container(
                        content=self.color_panel,
                        expand=True,
                        padding=8,
                    ), 
                ],
                expand=True,
                spacing=0
            )
        )
        
        self._build_layout()

    def _build_layout(self):
        self.page.add(self.root_container)

    def _update_bg(self, color):
        self.root_container.bgcolor = color
        self.root_container.update()

    # --- FUNCIÓN DE AJUSTE AUTOMÁTICO ---
    def _apply_window_resize(self, height):
        # Solo aplicamos si hay cambio real para evitar saltos
        current = self.page.window_height
        if abs(current - height) > 5:
            print(f"Ajustando altura ventana: {height}")
            self.page.window_height = height
            self.page.update()

    def update_ui(self, state):
        self.header.update_state(state)
        self.color_panel.sync_state(state)