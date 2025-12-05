import flet as ft
import colorsys
import time
import math
from config.favorites_manager import FavoritesManager
from ui.wiz_constants import STATIC_SCENES, DYNAMIC_SCENES, ALL_SCENES_MAP, RICH_RAINBOW, UPDATE_INTERVAL_SECONDS

class ColorPanel(ft.Container):
    def __init__(self, wiz_manager, on_bg_change=None, on_resize_request=None):
        super().__init__()
        self.wiz = wiz_manager
        self.fav_manager = FavoritesManager()
        self.on_bg_change = on_bg_change 
        self.on_resize_request = on_resize_request 
        
        self.current_hue = 0.0
        self.current_temp_pct = 0.0
        # Iniciamos alineados al ancho inicial del picker
        self.current_width = 220 
        self.last_update_time = 0

        self.expand = True
        self.bgcolor = ft.Colors.TRANSPARENT 
        
        self.rgb_indicator = None
        self.temp_indicator = None
        self.scene_buttons = [] 

        self.rgb_picker = self._build_rgb_picker()
        self.white_picker = self._build_white_picker()
        
        self.slider_bri = ft.Slider(
            min=10, max=100, value=100, 
            active_color="white", thumb_color="white",
            inactive_color=ft.Colors.with_opacity(0.3, "white"),
            on_change=lambda e: self.wiz.set_brightness(int(e.control.value))
        )

        self.fav_grid_rgb = ft.Row(wrap=True, spacing=10, alignment=ft.MainAxisAlignment.START)
        self.fav_grid_white = ft.Row(wrap=True, spacing=10, alignment=ft.MainAxisAlignment.START)
        
        self.scenes_container = ft.Column(scroll=ft.ScrollMode.HIDDEN, spacing=10)

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
                    content=self._build_picker_tab("Color", self.rgb_picker, self.fav_grid_rgb, "rgb")),
                ft.Tab(icon=ft.Icons.WB_SUNNY, text="Blancos",
                    content=self._build_picker_tab("Temperatura", self.white_picker, self.fav_grid_white, "white")),
                ft.Tab(icon=ft.Icons.AUTO_AWESOME, text="Escenas",
                    content=self._build_scenes_tab()),
            ],
            expand=True
        )

        self.content = ft.Column(
            spacing=0,
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

    def did_mount(self):
        self.page.on_resize = self._on_page_resize
        # Forzamos ajuste inicial
        self._on_page_resize(None)
        self._request_smart_resize()

    def _on_page_resize(self, e):
        if not self.page:
            return

        # Calculamos el ancho disponible usando el ancho cliente si existe,
        # de lo contrario usamos el ancho de ventana. Restamos un margen fijo
        # que aproxima los paddings internos.
        available = None
        if getattr(self.page, "width", None):
            available = self.page.width
        else:
            available = self.page.window_width

        margin = 60  # resta moderada que considera paddings internos
        new_width = max(180, available - margin)

        # Actualizamos el ancho de los gradientes y Stacks
        if hasattr(self, "rgb_gradient"):
            self.rgb_gradient.width = new_width
            self.rgb_stack.width = new_width
            self.rgb_picker.width = new_width
            self.rgb_stack.update()
            self.rgb_picker.update()

        if hasattr(self, "white_gradient"):
            self.white_gradient.width = new_width
            self.white_stack.width = new_width
            self.white_picker.width = new_width
            self.white_stack.update()
            self.white_picker.update()

        # Medimos el ancho real tras el layout para usarlo en la lógica
        measured_w = None
        if hasattr(self, "rgb_stack") and getattr(self.rgb_stack, "width", None):
            measured_w = self.rgb_stack.width
        if measured_w is None:
            measured_w = new_width

        self.current_width = measured_w

        # Reposicionar indicadores con el ancho real
        if self.rgb_indicator:
            self.rgb_indicator.left = max(0, min(self.current_hue * measured_w - 2, measured_w - 4))
            self.rgb_indicator.update()
        if self.temp_indicator:
            self.temp_indicator.left = max(0, min(self.current_temp_pct * measured_w - 2, measured_w - 4))
            self.temp_indicator.update()

        scene_btn_width = max(60, (new_width / 3) - 10)
        for btn in self.scene_buttons:
            btn.width = scene_btn_width
            btn.update()

        self.sync_state(self.wiz.get_state())

    # --- LÓGICA DE MOVIMIENTO CORREGIDA ---

    def _on_rgb_pan(self, e):
        # Usamos el ancho real del Stack/gradiente para evitar desfase tras redimensionar
        width = getattr(self.rgb_stack, "width", None) or getattr(self.rgb_gradient, "width", None) or self.current_width
        # Aseguramos que x esté dentro de los límites
        x = max(0, min(e.local_x, width))
        self.current_hue = x / width
        
        if self.rgb_indicator:
            # Movemos el indicador
            self.rgb_indicator.left = max(0, min(x - 2, width - 4))
            # IMPORTANTE: Actualizamos el indicador Y el stack padre para evitar congelamientos
            self.rgb_indicator.update()
            self.rgb_stack.update()
            
        now = time.time()
        # Limitamos el envío de comandos WiZ para no saturar, pero la UI se mueve fluida siempre
        if now - self.last_update_time > UPDATE_INTERVAL_SECONDS:
            self.last_update_time = now
            self._send_rgb_command()

    def _on_temp_pan(self, e):
        width = getattr(self.white_stack, "width", None) or getattr(self.white_gradient, "width", None) or self.current_width
        x = max(0, min(e.local_x, width))
        self.current_temp_pct = x / width
        
        if self.temp_indicator:
            self.temp_indicator.left = max(0, min(x - 2, width - 4))
            self.temp_indicator.update()
            self.white_stack.update()
            
        now = time.time()
        if now - self.last_update_time > UPDATE_INTERVAL_SECONDS:
            self.last_update_time = now
            self._send_white_command()

    # --- COMANDOS Y LÓGICA DE COLOR ---

    def _send_rgb_command(self):
        r, g, b = colorsys.hsv_to_rgb(self.current_hue, 1.0, 1.0)
        r, g, b = int(r*255), int(g*255), int(b*255)
        self._update_ambient_bg(r, g, b)
        self.wiz.set_rgb(r, g, b)

    def _send_white_command(self):
        kelvin = int(2200 + (self.current_temp_pct * (6500 - 2200)))
        self.wiz.set_white(kelvin)
        if kelvin < 4000: self._update_ambient_bg(255, 140, 0)
        else: self._update_ambient_bg(200, 230, 255)

    def _update_ambient_bg(self, r, g, b):
        bg_r = int(r * 0.15); bg_g = int(g * 0.15); bg_b = int(b * 0.15)
        final_color = "#111827" 
        if not (bg_r < 17 and bg_g < 24 and bg_b < 39):
            final_color = f"#{bg_r:02x}{bg_g:02x}{bg_b:02x}"
        if self.on_bg_change: self.on_bg_change(final_color)

    def _update_ambient_bg_from_hex(self, hex_color):
        h = hex_color.lstrip('#')
        rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        self._update_ambient_bg(*rgb)

    # --- INTERFAZ / BUILDERS ---

    def _build_rgb_picker(self):
        initial_w = 220 
        self.rgb_indicator = ft.Container(
            width=4, height=120, bgcolor="white", border_radius=2, 
            shadow=ft.BoxShadow(blur_radius=5, color="black"), 
            top=0, left=0, border=ft.border.all(1, ft.Colors.with_opacity(0.5, "black"))
        )
        self.rgb_gradient = ft.Container(
            width=initial_w, height=120, border_radius=15, 
            gradient=ft.LinearGradient(colors=RICH_RAINBOW)
        )
        self.rgb_stack = ft.Stack([self.rgb_gradient, self.rgb_indicator], width=initial_w, height=120)
        
        return ft.GestureDetector(
            content=self.rgb_stack, 
            on_pan_update=self._on_rgb_pan, 
            on_tap_down=self._on_rgb_pan, 
            on_pan_end=lambda e: self._send_rgb_command()
        )

    def _build_white_picker(self):
        initial_w = 220
        self.temp_indicator = ft.Container(
            width=4, height=120, bgcolor="white", border_radius=2, 
            shadow=ft.BoxShadow(blur_radius=5, color="black"), 
            top=0, left=0, border=ft.border.all(1, ft.Colors.with_opacity(0.5, "black"))
        )
        self.white_gradient = ft.Container(
            width=initial_w, height=120, border_radius=15, 
            gradient=ft.LinearGradient(colors=[ft.Colors.ORANGE_700, ft.Colors.ORANGE_300, ft.Colors.WHITE, ft.Colors.BLUE_100, ft.Colors.BLUE_300])
        )
        self.white_stack = ft.Stack([self.white_gradient, self.temp_indicator], width=initial_w, height=120)
        
        return ft.GestureDetector(
            content=self.white_stack, 
            on_pan_update=self._on_temp_pan, 
            on_tap_down=self._on_temp_pan, 
            on_pan_end=lambda e: self._send_white_command()
        )

    def _build_picker_tab(self, title, picker, fav_container, mode):
        save_btn = ft.IconButton(
            ft.Icons.ADD, 
            style=ft.ButtonStyle(bgcolor=ft.Colors.with_opacity(0.2, "white"), shape=ft.CircleBorder()),
            icon_color="white", tooltip="Guardar Favorito", 
            on_click=self._save_current_rgb if mode == "rgb" else self._save_current_white
        )
        return ft.Container(
            padding=ft.padding.all(16),
            content=ft.Column([
                ft.Container(height=8),
                ft.Container(
                    content=picker, height=120, border_radius=15, 
                    shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.3, "black")),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE
                ),
                ft.Divider(height=30, color=ft.Colors.with_opacity(0.1, "white")),
                ft.Row([ft.Text("FAVORITOS", size=12, weight="bold", color=ft.Colors.with_opacity(0.7, "white")), save_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Clic derecho para eliminar", size=10, color=ft.Colors.with_opacity(0.4, "white")),
                ft.Container(content=fav_container, padding=ft.padding.only(top=10), expand=True)
            ], scroll=ft.ScrollMode.HIDDEN)
        )

    def _build_scenes_tab(self):
        return ft.Container(padding=ft.padding.all(20), content=self.scenes_container)

    def _load_scenes_ui(self):
        self.scenes_container.controls.clear(); self.scene_buttons.clear()
        self.scenes_container.controls.append(ft.Text("ILUMINACIÓN ESTÁTICA", size=12, weight="bold", color=ft.Colors.with_opacity(0.5, "white")))
        self.scenes_container.controls.append(self._create_scene_row(STATIC_SCENES))
        self.scenes_container.controls.append(ft.Text("EFECTOS DINÁMICOS", size=12, weight="bold", color=ft.Colors.with_opacity(0.5, "white")))
        self.scenes_container.controls.append(self._create_scene_row(DYNAMIC_SCENES))

    def _create_scene_row(self, scenes_list):
        row = ft.Row(wrap=True, spacing=10, run_spacing=10, alignment=ft.MainAxisAlignment.START)
        initial_width = 80 
        if self.current_width > 10: initial_width = (self.current_width / 3) - 10
        for scene in scenes_list:
            btn = ft.Container(
                width=initial_width, height=initial_width * 0.75, 
                bgcolor=ft.Colors.with_opacity(0.15, "white"), border=ft.border.all(1, ft.Colors.with_opacity(0.2, "white")), border_radius=15, padding=10,
                content=ft.Column([ft.Icon(scene["icon"], color=scene["color"], size=24), ft.Text(scene["name"], color="white", size=11, weight="bold", text_align="center", no_wrap=True)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                on_click=lambda _, s_id=scene["id"], c=scene["color"]: self._activate_scene(s_id, c), ink=True,
            )
            row.controls.append(btn); self.scene_buttons.append(btn)
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
            self._request_smart_resize() 

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

    # --- AUTO RESIZE ---
    def _on_tab_change(self, e):
        self._refresh_favorites(e)
        self._request_smart_resize()

    def _request_smart_resize(self):
        if not self.on_resize_request: return
        
        base_height = 240 
        content_height = 0
        idx = self.tabs.selected_index
        safe_width = self.current_width if self.current_width > 200 else 280
        
        if idx == 0: # RGB
            content_height = 200
            count = len(self.fav_manager.get_rgb_favorites())
            btn_w = 60 
            cols = max(1, int(safe_width / btn_w))
            rows = math.ceil(count / cols)
            content_height += rows * 65 
        elif idx == 1: # White
            content_height = 200
            count = len(self.fav_manager.get_white_favorites())
            btn_w = 60
            cols = max(1, int(safe_width / btn_w))
            rows = math.ceil(count / cols)
            content_height += rows * 65
        elif idx == 2: # Escenas
            content_height = 40
            count_static = len(STATIC_SCENES)
            cols = 3 
            rows_static = math.ceil(count_static / cols)
            content_height += rows_static * 90 
            content_height += 30 
            count_dynamic = len(DYNAMIC_SCENES)
            rows_dyn = math.ceil(count_dynamic / cols)
            content_height += rows_dyn * 90

        total_needed = base_height + content_height + 50
        total_needed = max(500, min(950, total_needed))
        
        self.on_resize_request(int(total_needed))

    def sync_state(self, state):
        if not state: return
        bri = state.get("brightness")
        if bri is not None:
            try:
                val = float(bri); val = max(self.slider_bri.min, min(self.slider_bri.max, val))
                self.slider_bri.value = val; self.slider_bri.update()
            except: pass
        scene_id = state.get("sceneId", 0)
        if scene_id != 0 and scene_id in ALL_SCENES_MAP:
            self._update_ambient_bg_from_hex(ALL_SCENES_MAP[scene_id]["color"]); return 
        if "rgb" in state and isinstance(state["rgb"], (list, tuple)):
            r, g, b = state["rgb"]
            try:
                h, _, _ = colorsys.rgb_to_hsv(r/255, g/255, b/255); self.current_hue = h
                if self.rgb_indicator:
                    pos = (h * self.current_width) - 2; self.rgb_indicator.left = max(0, min(pos, self.current_width - 4))
                    self.rgb_indicator.update(); self.rgb_stack.update()
                self._update_ambient_bg(r, g, b)
            except: pass
        temp = state.get("temp")
        if temp is not None and isinstance(temp, (int, float)) and temp > 0:
            try:
                temp_clamped = max(2200, min(6500, temp)); self.current_temp_pct = (temp_clamped - 2200) / (6500 - 2200)
                if self.temp_indicator:
                    pos = (self.current_temp_pct * self.current_width) - 2; self.temp_indicator.left = max(0, min(pos, self.current_width - 4))
                    self.temp_indicator.update(); self.white_stack.update()
            except: pass