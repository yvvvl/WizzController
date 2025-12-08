import flet as ft
import colorsys
import time
from config.favorites_manager import FavoritesManager
from ui.wiz_constants import STATIC_SCENES, DYNAMIC_SCENES, ALL_SCENES_MAP, RICH_RAINBOW

class ColorPanel(ft.Container):
    def __init__(self, wiz_manager, on_bg_change=None, on_resize_request=None):
        super().__init__()
        self.wiz = wiz_manager
        self.fav_manager = FavoritesManager()
        self.on_bg_change = on_bg_change 
        self.on_resize_request = on_resize_request 
        
        # --- ESTADO INTERNO ---
        self.current_hue = 0.0
        self.current_temp_pct = 0.0
        
        # Eliminamos el last_update_time porque ya no frenaremos nada

        self.expand = True
        self.bgcolor = ft.Colors.TRANSPARENT 
        
        # Referencias a controles
        self.slider_hue = None
        self.slider_temp = None
        self.scene_buttons = []
        
        # Construcción de componentes
        self._build_components()
        
        # UI Principal
        self.content = ft.Column(
            spacing=0,
            expand=True,
            controls=[
                self.tabs,
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.2, "black"),
                    padding=ft.padding.symmetric(vertical=10, horizontal=20),
                    blur=ft.Blur(10, 10, ft.BlurTileMode.MIRROR),
                    content=ft.Column([
                        ft.Text("INTENSIDAD", size=10, weight="bold", color=ft.Colors.with_opacity(0.7, "white")),
                        self.slider_bri
                    ], spacing=0)
                )
            ]
        )
        
        self._load_favorites_ui(initial=True)
        self._load_scenes_ui()

    def _build_components(self):
        # Slider de Brillo - También instantáneo
        self.slider_bri = ft.Slider(
            min=10, max=100, value=100, 
            active_color="white", thumb_color="white",
            inactive_color=ft.Colors.with_opacity(0.3, "white"),
            on_change=lambda e: self.wiz.set_brightness(int(e.control.value))
        )

        # Grids
        self.fav_grid_rgb = ft.Row(wrap=True, spacing=10, alignment=ft.MainAxisAlignment.START)
        self.fav_grid_white = ft.Row(wrap=True, spacing=10, alignment=ft.MainAxisAlignment.START)
        self.scenes_container = ft.Column(spacing=10)

        # Pickers (Basados en Sliders Nativos)
        self.rgb_picker_ui = self._build_slider_picker(
            colors=RICH_RAINBOW,
            mode="rgb"
        )
        self.white_picker_ui = self._build_slider_picker(
            colors=[ft.Colors.ORANGE_700, ft.Colors.ORANGE_300, ft.Colors.WHITE, ft.Colors.BLUE_100, ft.Colors.BLUE_300],
            mode="white"
        )

        # Tabs
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            indicator_color="white",
            indicator_tab_size=True,
            label_color="white",
            unselected_label_color=ft.Colors.with_opacity(0.5, "white"),
            divider_color="transparent",
            on_change=self._on_tab_change,
            tabs=[
                ft.Tab(icon=ft.Icons.COLOR_LENS, text="Color",
                    content=self._build_tab_content(self.rgb_picker_ui, self.fav_grid_rgb, "rgb")),
                ft.Tab(icon=ft.Icons.WB_SUNNY, text="Blancos",
                    content=self._build_tab_content(self.white_picker_ui, self.fav_grid_white, "white")),
                ft.Tab(icon=ft.Icons.AUTO_AWESOME, text="Escenas",
                    content=self._build_scenes_tab()),
            ],
            expand=True
        )

    # --- UI BUILDERS (LÓGICA SLIDER NATIVO) ---

    def _build_slider_picker(self, colors, mode):
        """
        Slider nativo invisible superpuesto al gradiente.
        Responde a la velocidad de fotogramas nativa de la UI.
        """
        slider = ft.Slider(
            min=0, max=1000, value=0,
            active_color=ft.Colors.TRANSPARENT,
            inactive_color=ft.Colors.TRANSPARENT,
            thumb_color="white",
            overlay_color=ft.Colors.with_opacity(0.1, "white"),
            on_change=lambda e: self._handle_slider_change(e, mode) # <--- Disparo directo
        )

        if mode == "rgb": self.slider_hue = slider
        else: self.slider_temp = slider

        return ft.Stack(
            controls=[
                # Fondo Gradiente
                ft.Container(
                    height=60,
                    border_radius=30,
                    gradient=ft.LinearGradient(colors=colors, begin=ft.alignment.center_left, end=ft.alignment.center_right),
                    shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.3, "black")),
                ),
                # Slider Input
                ft.Container(
                    content=slider,
                    height=60,
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(horizontal=-10) 
                )
            ]
        )

    def _build_tab_content(self, picker_control, fav_container, mode):
        save_btn = ft.IconButton(
            ft.Icons.ADD, 
            style=ft.ButtonStyle(bgcolor=ft.Colors.with_opacity(0.2, "white"), shape=ft.CircleBorder()),
            icon_color="white", tooltip="Guardar Favorito", 
            on_click=self._save_current_rgb if mode == "rgb" else self._save_current_white
        )
        return ft.Container(
            padding=ft.padding.all(20),
            expand=True,
            content=ft.Column([
                ft.Container(height=10),
                picker_control,
                ft.Divider(height=40, color=ft.Colors.with_opacity(0.1, "white")),
                ft.Row([ft.Text("FAVORITOS", size=12, weight="bold", color=ft.Colors.with_opacity(0.7, "white")), save_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Clic derecho para eliminar", size=10, color=ft.Colors.with_opacity(0.4, "white")),
                ft.Container(content=fav_container, padding=ft.padding.only(top=10), expand=True)
            ], expand=True)
        )

    def _build_scenes_tab(self):
        return ft.Container(
            padding=ft.padding.all(20),
            content=self.scenes_container,
            expand=True,
        )

    # --- LÓGICA DE CONTROL (TURBO MODE) ---

    def _handle_slider_change(self, e, mode):
        # Calculamos porcentaje
        val = float(e.control.value)
        pct = val / 1000.0
        
        if mode == "rgb":
            self.current_hue = pct
            self._send_rgb_command() # <--- ¡LLAMADA INMEDIATA!
        else:
            self.current_temp_pct = pct
            self._send_white_command() # <--- ¡LLAMADA INMEDIATA!

    def _send_rgb_command(self):
        # Sin esperas, sin 'if', directo al metal.
        r, g, b = colorsys.hsv_to_rgb(self.current_hue, 1.0, 1.0)
        
        # Enviar a la ampolleta
        self.wiz.set_rgb(int(r*255), int(g*255), int(b*255))
        
        # Actualizar UI
        self._update_ambient_bg(int(r*255), int(g*255), int(b*255))

    def _send_white_command(self):
        kelvin = int(2200 + (self.current_temp_pct * (6500 - 2200)))
        
        # Enviar a la ampolleta
        self.wiz.set_white(kelvin)
        
        # Actualizar UI
        if kelvin < 4000: self._update_ambient_bg(255, 140, 0)
        else: self._update_ambient_bg(200, 230, 255)

    def _update_ambient_bg(self, r, g, b):
        bg_r, bg_g, bg_b = int(r * 0.15), int(g * 0.15), int(b * 0.15)
        if bg_r < 17 and bg_g < 24 and bg_b < 39: 
            final_color = "#111827"
        else:
            final_color = f"#{bg_r:02x}{bg_g:02x}{bg_b:02x}"
        if self.on_bg_change: self.on_bg_change(final_color)

    def _update_ambient_bg_from_hex(self, hex_color):
        h = hex_color.lstrip('#')
        rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        self._update_ambient_bg(*rgb)

    # --- ESCENAS Y FAVORITOS ---

    def _load_scenes_ui(self):
        self.scenes_container.controls.clear(); self.scene_buttons.clear()
        self.scenes_container.controls.append(ft.Text("ILUMINACIÓN ESTÁTICA", size=12, weight="bold", color=ft.Colors.with_opacity(0.5, "white")))
        self.scenes_container.controls.append(self._create_scene_row(STATIC_SCENES))
        self.scenes_container.controls.append(ft.Text("EFECTOS DINÁMICOS", size=12, weight="bold", color=ft.Colors.with_opacity(0.5, "white")))
        self.scenes_container.controls.append(self._create_scene_row(DYNAMIC_SCENES))

    def _create_scene_row(self, scenes_list):
        row = ft.Row(wrap=True, spacing=10, run_spacing=10, alignment=ft.MainAxisAlignment.START)
        for scene in scenes_list:
            btn = ft.Container(
                width=80, height=60, 
                bgcolor=ft.Colors.with_opacity(0.15, "white"), border=ft.border.all(1, ft.Colors.with_opacity(0.2, "white")), border_radius=15, padding=5,
                content=ft.Column([ft.Icon(scene["icon"], color=scene["color"], size=20), ft.Text(scene["name"], color="white", size=10, weight="bold", text_align="center", no_wrap=True)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                on_click=lambda _, s_id=scene["id"], c=scene["color"]: self._activate_scene(s_id, c), ink=True,
            )
            row.controls.append(btn)
        return row

    def _activate_scene(self, scene_id, hex_color):
        self.wiz.set_scene(scene_id); self._update_ambient_bg_from_hex(hex_color)

    def _load_favorites_ui(self, initial=False):
        self.fav_grid_rgb.controls.clear()
        for name, data in self.fav_manager.get_rgb_favorites().items():
            color_hex = f"#{data['r']:02x}{data['g']:02x}{data['b']:02x}"
            btn = self._create_fav_btn(name, color_hex, lambda _, d=data: (self.wiz.set_rgb(d['r'], d['g'], d['b']), self._update_ambient_bg(d['r'], d['g'], d['b'])), lambda _, n=name: self._delete_rgb(n))
            self.fav_grid_rgb.controls.append(btn)
        self.fav_grid_white.controls.clear()
        for name, data in self.fav_manager.get_white_favorites().items():
            visual_color = self._kelvin_to_hex_approx(data['temp'])
            btn = self._create_fav_btn(name, visual_color, lambda _, k=data['temp']: self.wiz.set_white(k), lambda _, n=name: self._delete_white(n))
            self.fav_grid_white.controls.append(btn)
        if not initial:
            self.update()

    def _create_fav_btn(self, name, color, on_click, on_delete):
        return ft.GestureDetector(content=ft.Container(width=50, height=50, border_radius=25, bgcolor=color, border=ft.border.all(2, ft.Colors.with_opacity(0.5, "white")), shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.5, color)), tooltip=f"{name}"), on_tap=on_click, on_secondary_tap=on_delete, mouse_cursor=ft.MouseCursor.CLICK)

    def _refresh_favorites(self, e): self._load_favorites_ui(initial=False)
    def _delete_rgb(self, name): self.fav_manager.remove_rgb_favorite(name); self._load_favorites_ui(False)
    def _delete_white(self, name): self.fav_manager.remove_white_favorite(name); self._load_favorites_ui(False)
    def _save_current_rgb(self, e):
        r, g, b = colorsys.hsv_to_rgb(self.current_hue, 1.0, 1.0); name = f"Color {len(self.fav_manager.get_rgb_favorites()) + 1}"
        self.fav_manager.add_rgb_favorite(name, int(r*255), int(g*255), int(b*255)); self._load_favorites_ui(False)
    def _save_current_white(self, e):
        kelvin = int(2200 + (self.current_temp_pct * (6500 - 2200))); name = f"Blanco {len(self.fav_manager.get_white_favorites()) + 1}"
        self.fav_manager.add_white_favorite(name, kelvin); self._load_favorites_ui(False)
    def _kelvin_to_hex_approx(self, k):
        if k < 3000: return "#fb923c" 
        if k < 4500: return "#ffedd5" 
        if k < 6000: return "#ffffff" 
        return "#bfdbfe" 

    def _on_tab_change(self, e):
        self._refresh_favorites(e)

    def sync_state(self, state):
        if not state: return
        bri = state.get("brightness")
        if bri is not None:
            try:
                val = float(bri); val = max(self.slider_bri.min, min(self.slider_bri.max, val))
                self.slider_bri.value = val; self.slider_bri.update()
            except: pass
        if "rgb" in state and isinstance(state["rgb"], (list, tuple)):
            r, g, b = state["rgb"]
            try:
                h, _, _ = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                self.current_hue = h
                if self.slider_hue:
                    self.slider_hue.value = h * 1000
                    self.slider_hue.update()
                self._update_ambient_bg(r, g, b)
            except: pass
        temp = state.get("temp")
        if temp is not None and isinstance(temp, (int, float)) and temp > 0:
            try:
                temp_clamped = max(2200, min(6500, temp))
                self.current_temp_pct = (temp_clamped - 2200) / (6500 - 2200)
                if self.slider_temp:
                    self.slider_temp.value = self.current_temp_pct * 1000
                    self.slider_temp.update()
            except: pass