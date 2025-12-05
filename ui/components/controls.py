import flet as ft
import time

class ControlPanel(ft.Container):
    def __init__(self, wiz_manager):
        super().__init__()
        self.wiz = wiz_manager
        self.expand = True
        self.padding = 20
        self.bgcolor = ft.Colors.TRANSPARENT 

        # Variables de control
        self._syncing = False # Evita rebote al recibir datos
        self._last_user_interaction = 0.0

        self.lbl_bri = ft.Text("100%", size=16, weight="bold", color="white")
        self.lbl_temp = ft.Text("4200K", size=16, weight="bold", color="white")

        self.content = ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.TUNE, color="#38bdf8"),
                    ft.Text("AJUSTES DE LUZ", size=14, weight="bold", color="#38bdf8")
                ]),
                padding=ft.padding.only(bottom=10)
            ),
            
            # --- SECCIÓN BRILLO ---
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Brillo General", color="#94a3b8", size=12),
                        ft.Container(expand=True),
                        self.lbl_bri
                    ]),
                    ft.Slider(
                        min=10, max=100, value=100, label="{value}%",
                        active_color="#38bdf8", thumb_color="white",
                        # Sin divisiones para movimiento fluido
                        on_change=lambda e: self._on_change_direct(e, self.lbl_bri, "%", self.wiz.set_brightness)
                    )
                ]),
                bgcolor="#0f172a",
                padding=15,
                border_radius=10
            ),
            
            ft.Container(height=10),
            
            # --- SECCIÓN TEMPERATURA ---
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Temperatura", color="#94a3b8", size=12),
                        ft.Container(expand=True),
                        self.lbl_temp
                    ]),
                    ft.Slider(
                        min=2200, max=6500, value=4200, label="{value}K",
                        active_color="#fbbf24", thumb_color="white",
                        on_change=lambda e: self._on_change_direct(e, self.lbl_temp, "K", self.wiz.set_temperature)
                    )
                ]),
                bgcolor="#0f172a",
                padding=15,
                border_radius=10
            ),
            
            ft.Container(expand=True),
            ft.Divider(color="#334155"),
            
            # --- BOTONES ---
            ft.Row([
                self._crear_boton("ENCENDER", ft.Icons.POWER_SETTINGS_NEW, "#22c55e", self.wiz.turn_on),
                ft.Container(width=10),
                self._crear_boton("APAGAR", ft.Icons.POWER_OFF, "#ef4444", self.wiz.turn_off),
            ])
        ])

    def _crear_boton(self, text, icon, color, func):
        return ft.ElevatedButton(
            text, icon=icon,
            style=ft.ButtonStyle(
                bgcolor=color, color="white", 
                shape=ft.RoundedRectangleBorder(radius=12),
                elevation=4, padding=20
            ),
            height=60, expand=True,
            on_click=lambda e: self._ejecutar_accion(e, func, text)
        )

    # --- ENVIAR DATOS (USUARIO) ---
    def _on_change_direct(self, e, label, suffix, func):
        # Si estamos recibiendo datos (Sync), no enviamos nada para evitar bucles
        if self._syncing: return
        
        self._last_user_interaction = time.time()
        val = int(e.control.value)
        
        # Actualizar texto visual
        label.value = f"{val}{suffix}"
        label.update()
        
        # Enviar comando rápido
        func(val)

    def _ejecutar_accion(self, e, func, msg):
        self._last_user_interaction = time.time()
        func()
        e.page.open(ft.SnackBar(ft.Text(f"Acción: {msg}"), duration=500, bgcolor="#333"))

    # --- RECIBIR DATOS (SYNC) ---
    def sync_state(self, state: dict):
        """Actualiza las barras si la bombilla cambia externamente."""
        # Regla de Oro: Si toqué hace poco (<2s), ignoro la red
        if time.time() - self._last_user_interaction < 2.0:
            return

        try:
            self._syncing = True # Modo Fantasma ON
            
            # 1. Sync Brillo
            if "dimming" in state:
                dim = int(state["dimming"])
                # Solo actualizar si hay diferencia real
                if abs(self.content.controls[1].content.controls[1].value - dim) > 1:
                    self.content.controls[1].content.controls[1].value = dim
                    self.lbl_bri.value = f"{dim}%"
                    self.content.controls[1].content.controls[1].update()
                    self.lbl_bri.update()

            # 2. Sync Temperatura
            if "temp" in state:
                temp = int(state["temp"])
                if abs(self.content.controls[3].content.controls[1].value - temp) > 50:
                    self.content.controls[3].content.controls[1].value = temp
                    self.lbl_temp.value = f"{temp}K"
                    self.content.controls[3].content.controls[1].update()
                    self.lbl_temp.update()
                    
        except Exception:
            pass
        finally:
            self._syncing = False # Modo Fantasma OFF