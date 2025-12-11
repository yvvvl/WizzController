import flet as ft

class Header(ft.Container):
    # Añadimos on_toggle_voice al init
    def __init__(self, wiz_manager, on_open_hotkeys, on_toggle_sidebar, on_toggle_voice):
        super().__init__()
        self.wiz = wiz_manager
        self.on_open_hotkeys = on_open_hotkeys
        self.on_toggle_sidebar = on_toggle_sidebar
        self.on_toggle_voice = on_toggle_voice # Nuevo callback
        
        self.padding = ft.padding.symmetric(horizontal=20, vertical=15)
        self.bgcolor = "#1f2937" 
        self.border_radius = 12
        
        # Botón Menú
        self.btn_menu = ft.IconButton(
            icon=ft.Icons.MENU,
            icon_color="white",
            tooltip="Alternar menú",
            on_click=lambda _: self.on_toggle_sidebar()
        )

        self.title = ft.Text("WizZ Desktop", size=20, weight="bold", color="white")
        
        # Botón de Voz (NUEVO)
        self.btn_voice = ft.IconButton(
            icon=ft.Icons.MIC_OFF, # Empieza apagado o cargando
            icon_color="grey",
            tooltip="Control por Voz",
            on_click=lambda _: self.on_toggle_voice()
        )

        # Botón de Hotkeys
        self.btn_hotkeys = ft.IconButton(
            ft.Icons.KEYBOARD,
            tooltip="Configurar Hotkeys",
            icon_color="blue200",
            on_click=lambda _: self.on_open_hotkeys()
        )

        self.content = ft.Row(
            controls=[
                # Izquierda
                ft.Row([self.btn_menu, self.title], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                
                # Derecha
                ft.Row(
                    controls=[
                        self.btn_voice,  # <-- Aquí está el micro
                        ft.Container(width=5),
                        self.btn_hotkeys
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

    def update_voice_status(self, status: str):
        """Actualiza el icono según el estado del VoiceController."""
        if status == "listening":
            self.btn_voice.icon = ft.Icons.MIC
            self.btn_voice.icon_color = "green400"
            self.btn_voice.tooltip = "Escuchando... (Click para pausar)"
        
        elif status == "paused":
            self.btn_voice.icon = ft.Icons.MIC_OFF
            self.btn_voice.icon_color = "red400"
            self.btn_voice.tooltip = "Voz Pausada (Click para activar)"
            
        elif status == "downloading":
            self.btn_voice.icon = ft.Icons.cloud_download
            self.btn_voice.icon_color = "yellow"
            self.btn_voice.tooltip = "Descargando modelo de voz..."
            
        elif status == "recognized":
            self.btn_voice.icon = ft.Icons.RECORD_VOICE_OVER
            self.btn_voice.icon_color = "cyan"
        
        elif status == "error":
            self.btn_voice.icon = ft.Icons.ERROR_OUTLINE
            self.btn_voice.icon_color = "red"
            self.btn_voice.tooltip = "Error en sistema de voz"

        self.btn_voice.update()

    def update_state(self, state):
        # El switch de power lo borramos en pasos anteriores para limpiar, 
        # así que este método ya no necesita actualizar el switch si no existe.
        pass