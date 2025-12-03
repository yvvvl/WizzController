import flet as ft

class Header(ft.Container):
    def __init__(self):
        super().__init__()
        self.padding = 20
        self.bgcolor = "#252525"
        self.content = ft.Row([
            # CORREGIDO: ft.Icons y ft.Colors (ambos con mayúscula inicial)
            ft.Icon(ft.Icons.LIGHTBULB, color=ft.Colors.AMBER, size=30),
            ft.Text("WizZ Control Center", size=25, weight=ft.FontWeight.BOLD),
        ], alignment=ft.MainAxisAlignment.START)