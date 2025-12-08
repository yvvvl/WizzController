import flet as ft
from ui.components.header import Header
from ui.components.color_panel import ColorPanel
from ui.components.hotkeys_dialog import HotkeysDialog # Importar diálogo
from config.hotkeys_manager import HotkeysManager # Importar manager

class WizzApp:
    def __init__(self, page: ft.Page, wiz_manager):
        self.page = page
        self.wiz = wiz_manager

        # --- SISTEMA DE HOTKEYS ---
        self.hotkeys_manager = HotkeysManager(self.wiz)
        self.hotkeys_dialog = HotkeysDialog(self.page, self.hotkeys_manager)
        self.page.overlay.append(self.hotkeys_dialog) # Añadir a overlay

        # Pasar callback al Header
        self.header = Header(self.wiz, on_open_hotkeys=self._open_hotkeys) 
        
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
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            )
        )
        
        self._build_layout()

    def _build_layout(self):
        self.page.add(self.root_container)

    def _open_hotkeys(self):
        self.hotkeys_dialog.open = True
        self.page.update()

    def _update_bg(self, color):
        self.root_container.bgcolor = color
        self.root_container.update()

    def _apply_window_resize(self, height):
        current = self.page.window_height
        if abs(current - height) > 5:
            self.page.window_height = height
            self.page.update()

    def update_ui(self, state):
        self.header.update_state(state)
        self.color_panel.sync_state(state)