import flet as ft
import time
import threading
from ui.styles import Theme
from .favorites_panel import FavoritesPanel

class HomePanel(ft.Container):
    def __init__(self, wiz_manager):
        super().__init__()
        self.wiz = wiz_manager
        self.expand = True
        
        # Estado transmisión
        self._target_bri = -1
        self._last_sent_bri = -1
        self._running = True
        
        # Hilo de fondo
        threading.Thread(target=self._transmission_loop, daemon=True).start()
        
        self._build_ui()

    def _transmission_loop(self):
        while self._running:
            if self._target_bri != -1 and self._target_bri != self._last_sent_bri:
                try:
                    self.wiz.set_brightness(self._target_bri)
                    self._last_sent_bri = self._target_bri
                except: pass
            
            # MODO TURBO: 0.01s (100 actualizaciones por segundo)
            time.sleep(0.01) 

    def did_unmount(self):
        self._running = False

    def _build_ui(self):
        header = ft.Row([
            ft.Icon(ft.Icons.HOME_FILLED, color=Theme.PRIMARY, size=28),
            ft.Text("Panel de Control", style=Theme.H1),
        ])

        self.lbl_bri = ft.Text("100%", size=16, weight="bold", color="white")
        
        self.slider_bri = ft.Slider(
            min=10, max=100, value=100,
            active_color=Theme.PRIMARY,
            thumb_color="white",
            expand=True,
            # Update visual inmediato mientras deslizas
            on_change=self._on_slider_visual
        )

        btn_on = self._make_power_btn("ON", ft.Icons.POWER_SETTINGS_NEW, Theme.SUCCESS, self.wiz.turn_on)
        btn_off = self._make_power_btn("OFF", ft.Icons.POWER_OFF, Theme.ERROR, self.wiz.turn_off)

        self.content = ft.ListView(
            controls=[
                header,
                ft.Container(height=20),
                ft.Container(
                    padding=25, bgcolor=Theme.CARD_BG, border_radius=16,
                    content=ft.Column([
                        ft.Row([ft.Text("INTENSIDAD", style=Theme.LABEL), self.lbl_bri], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        self.slider_bri,
                        ft.Container(height=15),
                        ft.Row([btn_on, ft.Container(width=10), btn_off])
                    ])
                ),
                ft.Container(height=20),
                FavoritesPanel(self.wiz)
            ],
            padding=ft.padding.only(bottom=50)
        )

    def _make_power_btn(self, text, icon, color, func):
        return ft.Container(
            expand=True, height=60,
            bgcolor=ft.Colors.with_opacity(0.1, color),
            border=ft.border.all(1, ft.Colors.with_opacity(0.5, color)),
            border_radius=12,
            content=ft.Row([ft.Icon(icon, color=color), ft.Text(text, weight="bold", color="white")], alignment=ft.MainAxisAlignment.CENTER),
            on_click=lambda _: threading.Thread(target=func).start(),
            ink=True
        )

    def _on_slider_visual(self, e):
        # Esta función corre a 60 FPS en el hilo de UI
        val = int(e.control.value)
        self.lbl_bri.value = f"{val}%"
        self.lbl_bri.update()
        self._target_bri = val # Pasa el dato al hilo turbo

    def sync_state(self, state):
        if self._target_bri != -1 and abs(self._target_bri - self._last_sent_bri) > 2:
            return 
        if "brightness" in state:
            b = int(state["brightness"])
            self.slider_bri.value = b
            self.lbl_bri.value = f"{b}%"
            self.slider_bri.update()
            self.lbl_bri.update()