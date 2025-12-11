import flet as ft
import time
import threading
import colorsys
import json
from ui.styles import Theme
from config.favorites_manager import FavoritesManager
from ui.wiz_constants import STATIC_SCENES, DYNAMIC_SCENES

class ColorPanel(ft.Container):
    def __init__(self, wiz_manager, on_bg_change=None):
        super().__init__()
        self.wiz = wiz_manager
        self.fav_manager = FavoritesManager()
        self.on_bg_change = on_bg_change
        self.expand = True
        
        self._target_color = None 
        self._last_sent_color = None
        self._running = True
        threading.Thread(target=self._transmission_loop, daemon=True).start()

        self._build_ui()

    def _transmission_loop(self):
        while self._running:
            if self._target_color and self._target_color != self._last_sent_color:
                try:
                    mode, v1, v2, v3 = self._target_color
                    if mode == "rgb": self.wiz.set_rgb(v1, v2, v3)
                    elif mode == "white": self.wiz.set_white(v1)
                    self._last_sent_color = self._target_color
                except: pass
            time.sleep(0.05)

    def did_unmount(self):
        self._running = False

    def _build_ui(self):
        self.slider_hue = self._make_gradient_slider(0, 360, 0, Theme.GRADIENT_HUE, self._on_color_change)
        
        self.grad_sat = ft.LinearGradient(colors=["white", "red"]) 
        self.container_sat = ft.Container(height=25, border_radius=12, gradient=self.grad_sat,
            content=ft.Slider(min=0, max=100, value=100, on_change=self._on_color_change, 
                            active_color="transparent", inactive_color="transparent", thumb_color="white"))
        
        self.slider_temp = self._make_gradient_slider(2200, 6500, 2700, Theme.GRADIENT_KELVIN, self._on_white_change)
        
        self.preview_box = ft.Container(width=60, height=60, border_radius=30, bgcolor="red", 
                                      border=ft.border.all(2, "white"), shadow=ft.BoxShadow(blur_radius=15, color="red"))

        self.favs_grid = ft.Row(wrap=True, spacing=10)
        self.scenes_grid = self._build_scenes_grid()

        self.content = ft.ListView(padding=20, spacing=20, controls=[
            ft.Text("ESTUDIO CREATIVO", style=Theme.H1),
            ft.Container(bgcolor=Theme.CARD_BG, padding=25, border_radius=16, content=ft.Column([
                ft.Row([ft.Text("MEZCLADOR", style=Theme.LABEL), self.preview_box], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Matiz (Hue)", size=10), self.slider_hue,
                ft.Text("Saturación", size=10), self.container_sat,
                ft.Divider(height=30, color="#33ffffff"),
                ft.Text("Blancos (K)", size=10), self.slider_temp
            ])),
            ft.Row([ft.Text("FAVORITOS", style=Theme.H2), 
                   ft.IconButton(ft.Icons.SAVE, icon_color=Theme.ACCENT, on_click=self._save_favorite)], 
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.favs_grid,
            ft.Text("ESCENAS", style=Theme.H2),
            self.scenes_grid
        ])

    def _make_gradient_slider(self, min_v, max_v, val, grad, change_fn):
        return ft.Container(height=25, border_radius=12, gradient=grad,
            content=ft.Slider(min=min_v, max=max_v, value=val, on_change=change_fn, 
                            active_color="transparent", inactive_color="transparent", thumb_color="white"))

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
            if self.on_bg_change: self.on_bg_change(hex_c)

    def _on_white_change(self, e):
        k = int(e.control.value)
        self.preview_box.bgcolor = "#ffffff"
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
        self.page.open(ft.SnackBar(ft.Text("Guardado"), bgcolor=Theme.SUCCESS))

    def _delete_fav(self, fid):
        self.fav_manager.remove_favorite(fid)
        self._refresh_favorites()

    def _refresh_favorites(self):
        self.favs_grid.controls.clear()
        for f in self.fav_manager.get_favorites():
            c = f["value"] if f["type"] == "rgb" else "#ffffff"
            self.favs_grid.controls.append(ft.Container(
                width=60, height=60, bgcolor=c, border_radius=12, border=ft.border.all(1, "white"),
                content=ft.Stack([
                    # CORRECCIÓN AQUÍ: size -> icon_size
                    ft.IconButton(ft.Icons.CLOSE, icon_size=14, icon_color="black", right=0, top=0, 
                                on_click=lambda _, x=f["id"]: self._delete_fav(x))
                ]),
                on_click=lambda _, x=f: self._apply_fav(x)
            ))
        self.favs_grid.update()

    def _apply_fav(self, f):
        if f["type"] == "rgb":
            h = f["value"].lstrip('#')
            rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            self.wiz.set_rgb(*rgb)
        else: self.wiz.set_white(int(f["value"]))

    def _build_scenes_grid(self):
        return ft.Row(wrap=True, spacing=10, controls=[
            ft.Container(width=80, height=60, bgcolor=Theme.CARD_BG, border_radius=10,
                content=ft.Column([ft.Icon(s["icon"], color=s["color"], size=20), 
                                 ft.Text(s["name"], size=10, no_wrap=True)], alignment="center"),
                on_click=lambda _, x=s["id"]: self.wiz.set_scene(x)
            ) for s in STATIC_SCENES + DYNAMIC_SCENES
        ])