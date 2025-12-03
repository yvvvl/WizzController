import flet as ft
import time

class ControlPanel(ft.Container):
    def __init__(self, wiz_manager):
        super().__init__()
        self.wiz = wiz_manager
        self.expand = True
        self.padding = 20
        self.bgcolor = ft.Colors.TRANSPARENT 

        self.lbl_bri = ft.Text("100%", size=16, weight="bold", color="white")
        self.lbl_temp = ft.Text("4200K", size=16, weight="bold", color="white")
        
        # Variables de control de Sync
        self._syncing = False # "Modo Fantasma"
        self._last_user_interaction = 0.0 # Timestamp de última vez que tocaste

        # Referencias
        self.slider_bri = ft.Slider(
            min=10, max=100, value=100, label="{value}%",
            active_color="#38bdf8", thumb_color="white",
            on_change=lambda e: self._on_change_brightness(e)
        )
        
        self.slider_temp = ft.Slider(
            min=2200, max=6500, value=4200, label="{value}K",
            active_color="#fbbf24", thumb_color="white",
            on_change=lambda e: self._on_change_temperature(e)
        )

        self.content = ft.Column([
            ft.Container(
                content=ft.Row([ft.Icon(ft.Icons.TUNE, color="#38bdf8"), ft.Text("AJUSTES", size=14, weight="bold", color="#38bdf8")]),
                padding=ft.padding.only(bottom=10)
            ),
            
            # Sección Brillo
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("Brillo General", color="#94a3b8", size=12), ft.Container(expand=True), self.lbl_bri]),
                    self.slider_bri
                ]),
                bgcolor="#0f172a", padding=15, border_radius=10
            ),
            
            ft.Container(height=10),
            
            # Sección Temperatura
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("Temperatura", color="#94a3b8", size=12), ft.Container(expand=True), self.lbl_temp]),
                    self.slider_temp
                ]),
                bgcolor="#0f172a", padding=15, border_radius=10
            ),
            
            ft.Container(expand=True),
            ft.Divider(color="#334155"),
            ft.Row([
                self._crear_boton("ENCENDER", ft.Icons.POWER_SETTINGS_NEW, "#22c55e", self.wiz.turn_on),
                ft.Container(width=10),
                self._crear_boton("APAGAR", ft.Icons.POWER_OFF, "#ef4444", self.wiz.turn_off),
            ])
        ])

    def _crear_boton(self, text, icon, color, func):
        return ft.ElevatedButton(text, icon=icon, style=ft.ButtonStyle(bgcolor=color, color="white", shape=ft.RoundedRectangleBorder(radius=12), padding=20), height=60, expand=True, on_click=lambda e: self._ejecutar_accion(e, func, text))

    # --- HANDLERS USUARIO (Envían datos) ---
    def _on_change_brightness(self, e):
        # Si estamos en modo sync, NO enviar comando (evita bucle)
        if self._syncing: return
        
        self._last_user_interaction = time.time() # ¡Estoy tocando!
        val = int(e.control.value)
        self.lbl_bri.value = f"{val}%"
        self.lbl_bri.update()
        self.wiz.set_brightness(val)

    def _on_change_temperature(self, e):
        if self._syncing: return
        self._last_user_interaction = time.time()
        val = int(e.control.value)
        self.lbl_temp.value = f"{val}K"
        self.lbl_temp.update()
        self.wiz.set_temperature(val)

    # --- HANDLERS DE SYNC (Reciben datos) ---
    def sync_state(self, state: dict):
        """Llamado por el Monitor cuando llega info de la bombilla."""
        # 1. Regla de Oro: Si el usuario tocó hace poco (< 2s), NO molestar
        if time.time() - self._last_user_interaction < 2.0:
            return

        try:
            self._syncing = True # ¡Modo Fantasma Activado!
            
            # Sincronizar Brillo
            if "dimming" in state:
                dim = int(state["dimming"])
                if abs(self.slider_bri.value - dim) > 1: # Solo actualizar si cambió
                    self.slider_bri.value = dim
                    self.lbl_bri.value = f"{dim}%"
                    self.slider_bri.update()
                    self.lbl_bri.update()

            # Sincronizar Temperatura
            if "temp" in state:
                temp = int(state["temp"])
                if abs(self.slider_temp.value - temp) > 50:
                    self.slider_temp.value = temp
                    self.lbl_temp.value = f"{temp}K"
                    self.slider_temp.update()
                    self.lbl_temp.update()
                    
        except Exception as e:
            print(f"Sync error UI: {e}")
        finally:
            self._syncing = False # Desactivar modo fantasma

    def _ejecutar_accion(self, e, func, msg):
        self._last_user_interaction = time.time()
        func()
        e.page.open(ft.SnackBar(ft.Text(f"Acción: {msg}"), duration=500, bgcolor="#333"))