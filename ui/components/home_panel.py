import flet as ft
from ui.styles import Theme

class HomePanel(ft.Container):
    def __init__(self, wiz_controller):
        super().__init__()
        self.wiz = wiz_controller
        self.expand = True
        self.padding = 30
        
        # Estado visual
        self.is_on = True 
        
        self._build_ui()

    def _build_ui(self):
        # 1. ENCABEZADO
        header = ft.Column([
            ft.Text("Bienvenido", style=Theme.H1),
            ft.Text("Panel de Control Principal", style=Theme.LABEL)
        ], spacing=5)

        # 2. BOTÓN MAESTRO (ENCENDER/APAGAR TODO)
        self.master_icon = ft.Icon(ft.Icons.POWER_SETTINGS_NEW, size=40, color="white")
        self.master_status = ft.Text("ENCENDIDO", size=16, weight="bold", color="white")
        
        master_card = ft.Container(
            bgcolor=Theme.PRIMARY,
            border_radius=20,
            padding=20,
            shadow=Theme.CARD_SHADOW,
            content=ft.Row([
                ft.Container(
                    content=self.master_icon,
                    bgcolor=ft.Colors.with_opacity(0.2, "white"),
                    padding=15,
                    border_radius=50
                ),
                ft.Column([
                    ft.Text("Control Maestro", color="white", size=12, opacity=0.8),
                    self.master_status
                ], spacing=2)
            ], alignment="start", vertical_alignment="center"),
            on_click=self._toggle_master,
            ink=True
        )

        # 3. ACCESOS RÁPIDOS
        quick_actions = ft.Row([
            self._build_action_card("Cine", ft.Icons.MOVIE, "#8b5cf6", lambda e: self.wiz.set_scene(12)),
            self._build_action_card("Lectura", ft.Icons.BOOK, "#f59e0b", lambda e: self.wiz.set_white(4000)),
            self._build_action_card("Relax", ft.Icons.SPA, "#10b981", lambda e: self.wiz.set_white(2700)),
        ], spacing=15, wrap=True)

        # LAYOUT
        self.content = ft.Column([
            header,
            ft.Divider(height=30, color="transparent"),
            ft.Text("ESTADO DEL SISTEMA", style=Theme.LABEL),
            master_card,
            ft.Divider(height=20, color="transparent"),
            ft.Text("ACCESOS RÁPIDOS", style=Theme.LABEL),
            quick_actions
        ], scroll="auto")

    def _build_action_card(self, title, icon, color, action):
        return ft.Container(
            expand=True,
            height=100,
            bgcolor=Theme.BG_CARD,
            border_radius=15,
            padding=15,
            content=ft.Column([
                ft.Icon(icon, color=color, size=24),
                ft.Text(title, color=Theme.TEXT_MAIN, weight="bold", size=14)
            ], alignment="space_between"),
            on_click=action,
            ink=True
        )

    def _toggle_master(self, e):
        self.is_on = not self.is_on
        if self.is_on:
            self.wiz.turn_on()
            self.master_status.value = "ENCENDIDO"
            self.master_icon.icon = ft.Icons.POWER_SETTINGS_NEW
            e.control.bgcolor = Theme.PRIMARY
        else:
            self.wiz.turn_off()
            self.master_status.value = "APAGADO"
            self.master_icon.icon = ft.Icons.POWER_OFF
            e.control.bgcolor = Theme.BG_CARD
            
        e.control.update()