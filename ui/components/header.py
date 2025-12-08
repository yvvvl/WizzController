import flet as ft

class Header(ft.Container):
    def __init__(self, wiz_manager, on_open_hotkeys=None): # Nuevo callback
        super().__init__()
        self.wiz = wiz_manager
        self.on_open_hotkeys = on_open_hotkeys
        
        self.padding = ft.padding.all(12)
        self.bgcolor = ft.Colors.TRANSPARENT
        
        self.status_dot = ft.Container(
            width=10, height=10, border_radius=5, bgcolor="red",
            animate=ft.Animation(500, ft.AnimationCurve.EASE_OUT)
        )
        self.status_text = ft.Text("Desconectado", size=12, color="grey")
        
        # Botón de Atajos
        self.btn_hotkeys = ft.IconButton(
            icon=ft.Icons.KEYBOARD,
            icon_color="white",
            tooltip="Configurar Atajos",
            on_click=self._on_hotkeys_click
        )

        self.content = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row([
                    ft.Text("WizZ", size=24, weight="bold", color="white"),
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=4,
                        bgcolor=ft.Colors.with_opacity(0.1, "white"),
                        content=ft.Text("BETA", size=10, color="white")
                    )
                ]),
                ft.Row([
                    self.btn_hotkeys, # Añadido
                    ft.Container(width=10),
                    self.status_dot,
                    self.status_text
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ]
        )

    def _on_hotkeys_click(self, e):
        if self.on_open_hotkeys:
            self.on_open_hotkeys()

    def update_state(self, state):
        if state and state.get("state") is not None:
            self.status_dot.bgcolor = "#00ff00"
            self.status_dot.shadow = ft.BoxShadow(blur_radius=10, color="#00ff00")
            self.status_text.value = "Conectado"
            self.status_text.color = "white"
        else:
            self.status_dot.bgcolor = "red"
            self.status_dot.shadow = None
            self.status_text.value = "Buscando..."
            self.status_text.color = "grey"
        self.update()