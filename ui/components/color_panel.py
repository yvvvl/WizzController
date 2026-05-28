import flet as ft
import colorsys
from ui.styles import Theme

class ColorPanel(ft.Container):
    def __init__(self, wiz_manager):
        super().__init__()
        self.wiz = wiz_manager
        self.expand = True
        self.padding = 20
        
        # Estado local visual
        self.hue = 0.0
        self.sat = 1.0
        self.val = 1.0
        
        self._build_ui()

    def _build_ui(self):
        # --- SECCIÓN 1: PREVISUALIZACIÓN ---
        self.color_preview = ft.Container(
            height=120,
            border_radius=15,
            bgcolor="red",
            shadow=ft.BoxShadow(blur_radius=50, color=ft.Colors.with_opacity(0.5, "red")),
            animate=ft.Animation(200, "easeOut"),
            content=ft.Column([
                ft.Icon(ft.Icons.LIGHTBULB, color="white", size=40),
                ft.Text("Color Actual", color="white", weight="bold")
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

        # --- SECCIÓN 2: CONTROLES RGB ---
        # Slider de Matiz (Hue)
        self.slider_hue = ft.Slider(
            min=0, max=360, value=0, 
            label="{value}°",
            on_change=self._on_input_change,
            active_color="transparent", 
            thumb_color="white"
        )
        
        # Contenedor con fondo gradiente para el slider (CORREGIDO AQUÍ)
        hue_container = ft.Container(
            content=self.slider_hue,
            gradient=ft.LinearGradient(
                colors=["red", "yellow", "green", "cyan", "blue", "magenta", "red"],
                # Usamos coordenadas manuales: (-1,0) es Izquierda Centro, (1,0) es Derecha Centro
                begin=ft.Alignment(-1.0, 0.0), 
                end=ft.Alignment(1.0, 0.0)
            ),
            border_radius=10, height=30
        )

        # Slider Saturación
        self.slider_sat = ft.Slider(min=0, max=100, value=100, label="{value}%", on_change=self._on_input_change)
        
        controls_card = ft.Container(
            bgcolor=Theme.BG_CARD, padding=20, border_radius=20,
            content=ft.Column([
                ft.Text("MEZCLADOR CROMÁTICO", style=Theme.LABEL),
                ft.Text("Matiz (Color)", size=12),
                hue_container,
                ft.Text("Saturación (Intensidad)", size=12),
                self.slider_sat
            ])
        )

        # --- SECCIÓN 3: BLANCOS (Temperaturas) ---
        temps = [
            (2200, "Relax", "#ffaa00"),
            (2700, "Cálido", "#ffcc00"),
            (4000, "Neutro", "#ffffff"),
            (6500, "Frío", "#ccf0ff")
        ]
        
        temp_buttons = [
            ft.Container(
                expand=True, height=50, bgcolor=ft.Colors.with_opacity(0.1, color),
                border=ft.border.all(1, color), border_radius=10,
                content=ft.Column([
                    ft.Icon(ft.Icons.THERMOSTAT, color=color, size=16),
                    ft.Text(label, size=10, color="white")
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=2),
                on_click=lambda e, k=k: self.wiz.set_white(k),
                ink=True
            ) for k, label, color in temps
        ]

        whites_card = ft.Container(
            bgcolor=Theme.BG_CARD, padding=20, border_radius=20,
            content=ft.Column([
                ft.Text("TEMPERATURA DE BLANCOS", style=Theme.LABEL),
                ft.Row(temp_buttons, spacing=10)
            ])
        )

        # LAYOUT RESPONSIVO
        self.content = ft.ListView(
            spacing=20,
            controls=[
                self.color_preview,
                controls_card,
                whites_card
            ]
        )

    def _on_input_change(self, e):
        # 1. Calcular color
        h = self.slider_hue.value
        s = self.slider_sat.value
        
        # Conversión HSV a RGB
        r, g, b = colorsys.hsv_to_rgb(h/360, s/100, 1.0)
        r, g, b = int(r*255), int(g*255), int(b*255)
        
        # 2. Actualizar UI (Feedback instantáneo local)
        hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
        self.color_preview.bgcolor = hex_color
        self.color_preview.shadow.color = ft.Colors.with_opacity(0.6, hex_color)
        self.color_preview.update()

        # 3. Enviar al controlador
        self.wiz.set_rgb(r, g, b)