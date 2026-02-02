import flet as ft
from ui.styles import Theme

class Header(ft.Container):
    def __init__(self, wiz_manager, on_open_hotkeys, on_toggle_sidebar):
        super().__init__()
        self.wiz = wiz_manager
        self.on_open_hotkeys = on_open_hotkeys
        self.on_toggle_sidebar = on_toggle_sidebar
        
        self.padding = ft.padding.symmetric(horizontal=20, vertical=15)
        self.bgcolor = Theme.BG_CARD
        self.border_radius = 12
        
        # BotÃ³n MenÃº
        self.btn_menu = ft.IconButton(
            icon=ft.icons.MENU,
            icon_color=Theme.TEXT_MAIN,
            tooltip="Alternar menÃº",
            on_click=lambda _: self.on_toggle_sidebar()
        )

        self.title = ft.Text("WizZ Desktop", size=20, weight="bold", color=Theme.TEXT_MAIN)
        
        # BotÃ³n de Hotkeys
        self.btn_hotkeys = ft.IconButton(
            ft.icons.KEYBOARD,
            tooltip="Configurar Hotkeys",
            icon_color=Theme.PRIMARY,
            on_click=lambda _: self.on_open_hotkeys()
        )

        self.content = ft.Row(
            controls=[
                # Izquierda
                ft.Row([self.btn_menu, self.title], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                
                # Derecha
                ft.Row(
                    controls=[
                        self.btn_hotkeys
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

    def update_state(self, state):
        # El switch de power lo borramos en pasos anteriores para limpiar, 
        # asÃ­ que este mÃ©todo ya no necesita actualizar el switch si no existe.
        pass
