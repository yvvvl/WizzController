import flet as ft

class Header(ft.Container):
    def __init__(self, wiz_manager, on_open_hotkeys):
        super().__init__()
        self.wiz = wiz_manager
        self.on_open_hotkeys = on_open_hotkeys
        
        # Estilos del contenedor Header
        self.padding = ft.padding.symmetric(horizontal=20, vertical=15)
        self.bgcolor = "#1f2937" # Un gris un poco más claro que el fondo
        self.border_radius = 12
        
        # --- Elementos ---
        self.title = ft.Text(
            "WizZ Desktop", 
            size=20, 
            weight=ft.FontWeight.BOLD, 
            color="white"
        )
        
        # El Interruptor (Switch)
        self.power_switch = ft.Switch(
            label="OFF",
            label_position=ft.LabelPosition.LEFT,
            active_color=ft.colors.GREEN_400,
            active_track_color=ft.colors.GREEN_900,
            inactive_thumb_color=ft.colors.GREY_400,
            inactive_track_color=ft.colors.GREY_800,
            on_change=self._on_switch_change,
            scale=0.9
        )

        self.btn_hotkeys = ft.IconButton(
            icon=ft.Icons.KEYBOARD,
            tooltip="Configurar Hotkeys",
            icon_color=ft.colors.BLUE_200,
            on_click=lambda _: self.on_open_hotkeys()
        )

        # --- Layout ---
        self.content = ft.Row(
            controls=[
                self.title,
                ft.Row(
                    controls=[
                        self.power_switch,
                        ft.Container(width=10), # Separador
                        self.btn_hotkeys
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

    def _on_switch_change(self, e):
        """Maneja el click manual en el interruptor"""
        if self.power_switch.value:
            self.power_switch.label = "ON"
            self.wiz.turn_on()
        else:
            self.power_switch.label = "OFF"
            self.wiz.turn_off()
        self.power_switch.update()

    def update_state(self, state):
        """Sincroniza el interruptor cuando el estado cambia externamente (ej. Hotkeys)"""
        if not state: return
        
        is_on = state.get("state", False)
        
        # Solo actualizamos si hay diferencia para evitar loops visuales
        if self.power_switch.value != is_on:
            self.power_switch.value = is_on
            self.power_switch.label = "ON" if is_on else "OFF"
            self.power_switch.update()