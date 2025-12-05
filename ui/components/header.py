import flet as ft

class Header(ft.Container):
    def __init__(self, wiz_manager):
        super().__init__()
        self.wiz = wiz_manager
        self.height = 60
        self.padding = ft.padding.symmetric(horizontal=15)
        
        # FONDO TRANSPARENTE: Para dejar ver el color ambiental
        self.bgcolor = ft.Colors.TRANSPARENT 
        
        self.switch = ft.Switch(value=True, active_color="blue", on_change=self._on_switch)
        
        self.content = ft.Row([
            ft.Icon(ft.Icons.LIGHTBULB, color="yellow", size=24),
            ft.Text("WizZ Desktop", size=20, weight="bold", color="white"),
            ft.Container(expand=True),
            self.switch
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
    def _on_switch(self, e):
        print(f"Switch: {e.control.value}")
        if e.control.value:
            self.wiz.turn_on()
        else:
            self.wiz.turn_off()

    def update_state(self, state):
        if "state" in state:
            self.switch.value = state["state"]
            self.switch.update()