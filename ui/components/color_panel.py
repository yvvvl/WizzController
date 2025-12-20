import flet as ft
import time
import threading
import colorsys
from ui.styles import Theme
from config.favorites_manager import FavoritesManager
from ui.wiz_constants import STATIC_SCENES, DYNAMIC_SCENES

class ColorPanel(ft.Container):
    def __init__(self, wiz_manager, on_bg_change=None):
        super().__init__()
        self.wiz = wiz_manager
        self.fav_manager = FavoritesManager()
        self.expand = True
        
        # --- MOTOR DE ALTA VELOCIDAD ---
        self._target_color = None 
        self._last_sent_color = None
        self._running = True
        
        # Iniciamos el hilo de transmisión
        threading.Thread(target=self._transmission_loop, daemon=True).start()

        self._build_ui()

    def _transmission_loop(self):
        """
        Bucle de transmisión de alta frecuencia (Turbo Mode).
        Envía comandos lo más rápido posible sin congelar la UI.
        """
        while self._running:
            if self._target_color and self._target_color != self._last_sent_color:
                try:
                    mode, v1, v2, v3 = self._target_color
                    if mode == "rgb": 
                        self.wiz.set_rgb(v1, v2, v3)
                    elif mode == "white": 
                        self.wiz.set_white(v1)
                    
                    self._last_sent_color = self._target_color
                except: 
                    pass
            
            # 0.01s = 100 FPS (Sensación instantánea)
            time.sleep(0.01)

    def did_unmount(self):
        self._running = False

    def _build_ui(self):
        # 1. Sliders
        self.slider_hue = self._make_gradient_slider(0, 360, 0, Theme.GRADIENT_HUE, self._on_color_change)

        self.grad_sat = ft.LinearGradient(colors=["white", "red"]) 
        self.container_sat = ft.Container(
            height=28, border_radius=14, gradient=self.grad_sat,
            content=ft.Slider(min=0, max=100, value=100, on_change=self._on_color_change, 
                            active_color="transparent", inactive_color="transparent", thumb_color="white")
        )
        
        self.slider_temp = self._make_gradient_slider(2200, 6500, 2700, Theme.GRADIENT_KELVIN, self._on_white_change)
        
        # 2. Preview (Esfera)
        self.preview_box = ft.Container(
            width=130, height=130, 
            border_radius=65,      
            bgcolor="red", 
            border=ft.border.all(4, Theme.BG_CARD), 
            shadow=ft.BoxShadow(blur_radius=40, color="red", spread_radius=2, offset=ft.Offset(0,0)),
            alignment=ft.alignment.center,
            content=ft.Icon(ft.Icons.LIGHTBULB, color=ft.Colors.with_opacity(0.5, "white"), size=40)
        )

        # 3. Panel Principal
        colors_section = ft.Column([
            self._build_slider_row(ft.Icons.COLOR_LENS, "Matiz", self.slider_hue),
            ft.Container(height=10),
            self._build_slider_row(ft.Icons.WATER_DROP, "Saturación", self.container_sat),
        ], spacing=0)

        whites_section = self._build_slider_row(ft.Icons.THERMOSTAT, "Temp K", self.slider_temp)

        mixing_card = ft.Container(
            padding=30, bgcolor=Theme.CARD_BG, border_radius=24,
            border=ft.border.all(1, ft.Colors.with_opacity(0.05, "white")),
            content=ft.Column([
                ft.Row([self.preview_box], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=30, color="transparent"),
                ft.Text("COLOR CROMÁTICO", style=Theme.LABEL),
                ft.Container(height=10),
                colors_section,
                ft.Divider(height=30, color=ft.Colors.with_opacity(0.2, "grey")),
                ft.Text("BLANCOS Y TONOS", style=Theme.LABEL),
                ft.Container(height=10),
                whites_section
            ])
        )

        # 4. Grids
        self.favs_grid = ft.Row(wrap=True, spacing=15, run_spacing=15)
        self.scenes_grid = self._build_scenes_grid()

        self.content = ft.ListView(
            padding=ft.padding.symmetric(horizontal=20, vertical=30), 
            spacing=25,
            controls=[
                ft.Text("Estudio Creativo", style=Theme.H1, size=28),
                mixing_card,
                ft.Column([
                     ft.Row([
                        ft.Text("MIS FAVORITOS", style=Theme.H2), 
                        ft.IconButton(ft.Icons.SAVE_ALT, icon_color=Theme.PRIMARY, tooltip="Guardar actual", on_click=self._save_favorite)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.favs_grid,
                ], spacing=15),
                ft.Column([
                    ft.Text("ESCENAS RÁPIDAS", style=Theme.H2),
                    self.scenes_grid
                ], spacing=15)
            ]
        )

    def _make_gradient_slider(self, min_v, max_v, val, grad, change_fn):
        return ft.Container(
            height=28, border_radius=14, gradient=grad,
            content=ft.Slider(min=min_v, max=max_v, value=val, on_change=change_fn, 
                            active_color="transparent", inactive_color="transparent", thumb_color="white")
        )

    def _build_slider_row(self, icon_name, label_text, slider_control):
        return ft.Row([
            ft.Icon(icon_name, color=Theme.TEXT_MUTED, size=20),
            ft.Container(width=10),
            ft.Text(label_text, color=Theme.TEXT_MAIN, size=14, weight=ft.FontWeight.W_500, width=90),
            ft.Container(content=slider_control, expand=True)
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _on_color_change(self, e):
        h = self.slider_hue.content.value
        s = self.container_sat.content.value
        r, g, b = colorsys.hsv_to_rgb(h/360, s/100, 1.0)
        
        hex_c = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        self.preview_box.bgcolor = hex_c
        self.preview_box.shadow.color = hex_c
        self.preview_box.update()
        
        r_p, g_p, b_p = colorsys.hsv_to_rgb(h/360, 1.0, 1.0)
        self.grad_sat.colors = ["#ffffff", f"#{int(r_p*255):02x}{int(g_p*255):02x}{int(b_p*255):02x}"]
        self.container_sat.update()

        if s < 5: 
            k = int(self.slider_temp.content.value)
            self._target_color = ("white", k, 0, 0)
        else:
            self._target_color = ("rgb", int(r*255), int(g*255), int(b*255))

    def _on_white_change(self, e):
        k = int(e.control.value)
        self.preview_box.bgcolor = "#ffffff"
        self.preview_box.shadow.color = "#ffffff"
        self.preview_box.update()
        self._target_color = ("white", k, 0, 0)

    def did_mount(self): self._refresh_favorites()

    def _save_favorite(self, e):
        if self.container_sat.content.value < 5:
            val = int(self.slider_temp.content.value)
            self.fav_manager.add_favorite(f"Blanco {val}K", "white", val, "WB_SUNNY")
        else:
            h = self.slider_hue.content.value
            s = self.container_sat.content.value
            r, g, b = colorsys.hsv_to_rgb(h/360, s/100, 1.0)
            hex_v = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            self.fav_manager.add_favorite("Color Personal", "rgb", hex_v, "COLOR_LENS")
        self._refresh_favorites()
        self.page.open(ft.SnackBar(ft.Text("¡Color guardado en favoritos!"), bgcolor=Theme.SUCCESS))

    def _delete_fav(self, fid):
        self.fav_manager.remove_favorite(fid)
        self._refresh_favorites()

    def _refresh_favorites(self):
        self.favs_grid.controls.clear()
        for f in self.fav_manager.get_favorites():
            c = f["value"] if f["type"] == "rgb" else "#ffffff"
            
            # --- AQUÍ ESTABA EL ERROR ---
            # Corregido: Opacidad aplicada al COLOR, no como propiedad del Shadow
            shadow_color = ft.Colors.with_opacity(0.4, c)
            
            self.favs_grid.controls.append(ft.Container(
                width=65, height=65, bgcolor=c, border_radius=18, 
                border=ft.border.all(2, ft.Colors.with_opacity(0.3, "white")),
                shadow=ft.BoxShadow(blur_radius=10, color=shadow_color),
                content=ft.Stack([
                    ft.IconButton(ft.Icons.CLOSE, icon_size=14, icon_color=ft.Colors.with_opacity(0.7, "black"), 
                                right=-5, top=-5, 
                                on_click=lambda _, x=f["id"]: self._delete_fav(x))
                ]),
                on_click=lambda _, x=f: self._apply_fav(x),
                ink=True, tooltip=f["name"]
            ))
        self.favs_grid.update()

    def _apply_fav(self, f):
        if f["type"] == "rgb":
            h = f["value"].lstrip('#')
            rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            self.wiz.set_rgb(*rgb)
        else: self.wiz.set_white(int(f["value"]))

    def _build_scenes_grid(self):
        return ft.Row(wrap=True, spacing=15, run_spacing=15, controls=[
            ft.Container(
                width=85, height=70, bgcolor=Theme.BG_CARD, border_radius=16,
                border=ft.border.all(1, ft.Colors.with_opacity(0.1, s["color"])),
                content=ft.Column([
                    ft.Icon(s["icon"], color=s["color"], size=24), 
                    ft.Text(s["name"], size=11, weight=ft.FontWeight.W_500, no_wrap=True)
                ], alignment="center", spacing=5),
                on_click=lambda _, x=s["id"]: self.wiz.set_scene(x),
                # Corrección también aquí para seguridad
                ink=True, shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.with_opacity(0.1, s["color"]))
            ) for s in STATIC_SCENES + DYNAMIC_SCENES
        ])