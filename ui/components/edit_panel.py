"""
Panel de EdiciÃ³n Profesional con:
- Color Picker Circular (HSV)
- Sistema de Favoritos mejorado
- Escenas organizadas por tipo (EstÃ¡ticas/DinÃ¡micas)
- Control de velocidad y brillo
"""

import flet as ft
import colorsys
import logging
import re
import time
import math
import io
import base64
import threading
from PIL import Image, ImageDraw

from ui.styles import Theme
from config.favorites_manager import FavoritesManager
from config.bulbs_manager import BulbsManager
from ui.wiz_constants import STATIC_SCENES, DYNAMIC_SCENES


class CircularColorPicker(ft.Column):
    """Color picker circular HSV profesional y fluido."""

    def __init__(self, on_color_change=None, size=320):
        super().__init__(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.logger = logging.getLogger(__name__)
        self.on_color_change = on_color_change
        self.size = size
        self.width = size
        
        # Estado HSV
        self._hue = 0.0  # 0-360
        self._saturation = 1.0  # 0-1
        self._value = 1.0  # 0-1
        
        # Cache
        self._hs_cache = {}
        self._hue_cache = {}
        
        self._build_ui()

    def _build_ui(self):
        # Imagen SV (saturation-value)
        self.sv_image = ft.Image(
            src=self._render_sv_circle(),
            width=self.size,
            height=self.size,
            fit=ft.BoxFit.FILL,
            filter_quality=ft.FilterQuality.LOW,
        )

        # Cursor en el picker circular
        self.sv_cursor = ft.Container(
            width=16,
            height=16,
            border_radius=8,
            border=ft.border.all(2.5, "#ffffff"),
            bgcolor=ft.Colors.with_opacity(0.2, "#000000"),
            shadow=ft.BoxShadow(
                blur_radius=6,
                color="#000000",
                spread_radius=0.5,
            ),
            left=self.size - 8,
            top=0,
            animate="80ms",
        )

        # Stack con imagen y cursor
        self.sv_stack = ft.Stack(
            controls=[self.sv_image, self.sv_cursor],
            width=self.size,
            height=self.size,
        )

        # Detector de gestos para el picker
        self.sv_detector = ft.GestureDetector(
            content=ft.Container(
                content=self.sv_stack,
                width=self.size,
                height=self.size,
                border_radius=self.size // 2,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                border=ft.border.all(2, ft.Colors.with_opacity(0.3, Theme.PRIMARY)),
                shadow=ft.BoxShadow(
                    blur_radius=20,
                    color=ft.Colors.with_opacity(0.4, Theme.PRIMARY),
                    spread_radius=0,
                ),
            ),
            on_tap_down=self._on_sv_pick,
            on_pan_start=self._on_sv_pick,
            on_pan_update=self._on_sv_pick,
        )

        # Slider de Value (brillo)
        self.slider_value = ft.Slider(
            min=0,
            max=100,
            value=100,
            divisions=100,
            active_color=Theme.PRIMARY,
            thumb_color=Theme.ACCENT,
            on_change=self._on_value_change,
            width=self.size,
            expand=False,
        )

        value_row = ft.Column(
            [
                ft.Text("Brillo", size=10, color=Theme.TEXT_MUTED, weight="w500"),
                self.slider_value,
            ],
            spacing=6,
        )

        # Hue wheel (barra de Matiz)
        self.hue_bar = ft.Image(
            src=self._render_hue_bar(),
            width=self.size,
            height=40,
            fit=ft.BoxFit.FILL,
        )

        # Slider para Hue (invisible, solo para controlar)
        self.slider_hue = ft.Slider(
            min=0,
            max=360,
            value=0,
            divisions=360,
            active_color=ft.Colors.TRANSPARENT,
            thumb_color=Theme.ACCENT,
            on_change=self._on_hue_change,
            width=self.size,
            expand=False,
            height=20,
        )

        hue_row = ft.Column(
            [
                ft.Text("Matiz", size=10, color=Theme.TEXT_MUTED, weight="w500"),
                ft.Stack(
                    [
                        self.hue_bar,
                        self.slider_hue,
                    ],
                    width=self.size,
                    height=40,
                ),
            ],
            spacing=6,
        )

        self.controls = [
            self.sv_detector,
            value_row,
            hue_row,
        ]

    def _on_sv_pick(self, e):
        """Maneja clics/dragging en el picker circular."""
        x = getattr(e, "local_x", None)
        y = getattr(e, "local_y", None)
        
        if x is None or y is None:
            return

        # Centro del cÃ­rculo
        cx, cy = self.size / 2, self.size / 2
        
        # Coordenadas relativas al centro
        dx = float(x) - cx
        dy = float(y) - cy
        
        # Distancia desde el centro (radio)
        dist = math.sqrt(dx*dx + dy*dy)
        max_radius = self.size / 2 - 8
        
        if dist <= max_radius:
            # Saturation es la proporciÃ³n del radio
            self._saturation = max(0, min(1.0, dist / max_radius))
            
            # Hue es el Ã¡ngulo
            angle = math.degrees(math.atan2(dy, dx))
            if angle < 0:
                angle += 360
            self._hue = angle
            
            # Actualizar sliders y UI
            self._update_from_state()
            
            # Callback
            if self.on_color_change:
                r, g, b = self._get_rgb()
                self.on_color_change(r, g, b)

    def _on_hue_change(self, e):
        """Cambio de matiz."""
        self._hue = float(e.control.value)
        self._update_sv_image()
        
        # Actualizar posiciÃ³n del cursor
        self._update_cursor_position()
        
        if self.on_color_change:
            r, g, b = self._get_rgb()
            self.on_color_change(r, g, b)

    def _on_value_change(self, e):
        """Cambio de brillo."""
        self._value = float(e.control.value) / 100.0
        
        if self.on_color_change:
            r, g, b = self._get_rgb()
            self.on_color_change(r, g, b)

    def _update_from_state(self):
        """Actualiza UI desde el estado interno."""
        try:
            self.slider_hue.value = self._hue
            self.slider_hue.update()
        except Exception:
            pass
        
        self._update_sv_image()
        self._update_cursor_position()

    def _update_sv_image(self):
        """Re-renderiza la imagen SV basada en el hue actual."""
        try:
            self.sv_image.src = self._render_sv_circle()
            self.sv_image.update()
        except Exception:
            pass

    def _update_cursor_position(self):
        """Actualiza la posiciÃ³n del cursor en el picker."""
        try:
            cx, cy = self.size / 2, self.size / 2
            max_radius = self.size / 2 - 8
            
            # Ãngulo en radianes
            angle_rad = math.radians(self._hue)
            
            # Distancia desde el centro
            dist = self._saturation * max_radius
            
            # PosiciÃ³n del cursor
            x = cx + dist * math.cos(angle_rad) - 8
            y = cy + dist * math.sin(angle_rad) - 8
            
            self.sv_cursor.left = x
            self.sv_cursor.top = y
            self.sv_cursor.update()
        except Exception:
            pass

    def _get_rgb(self):
        """Retorna RGB del color actual."""
        r, g, b = colorsys.hsv_to_rgb(
            self._hue / 360.0,
            self._saturation,
            self._value
        )
        return int(r * 255), int(g * 255), int(b * 255)

    def set_rgb(self, r, g, b):
        """Establece el color desde RGB."""
        r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        
        self._hue = h * 360
        self._saturation = s
        self._value = v
        
        self._update_from_state()
        
        try:
            self.slider_value.value = v * 100
            self.slider_value.update()
        except Exception:
            pass

    def _render_sv_circle(self, size=None) -> str:
        """Renderiza cÃ­rculo SV como PNG base64 - versiÃ³n mejorada con degradado radial."""
        if size is None:
            size = self.size
        
        key = int(self._hue) % 360
        if key in self._hs_cache:
            return self._hs_cache[key]
        
        img = Image.new("RGB", (size, size), (0, 0, 0))
        
        cx, cy = size / 2, size / 2
        max_radius = size / 2 - 2
        
        h = self._hue / 360.0
        
        # Renderizado pixel por pixel para cÃ­rculo con degradado SV
        for y in range(size):
            for x in range(size):
                dx = x - cx
                dy = y - cy
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist <= max_radius:
                    # SaturaciÃ³n basada en distancia desde el centro
                    s = dist / max_radius
                    
                    # Value siempre al mÃ¡ximo en este picker simplificado
                    v = 1.0
                    
                    r, g, b = colorsys.hsv_to_rgb(h, s, v)
                    img.putpixel((x, y), (int(r*255), int(g*255), int(b*255)))
        
        # Guardar como PNG base64
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = base64.b64encode(buf.getvalue()).decode()
        
        uri = f"data:image/png;base64,{data}"
        self._hs_cache[key] = uri
        
        # Limitar cache
        if len(self._hs_cache) > 10:
            old_key = list(self._hs_cache.keys())[0]
            del self._hs_cache[old_key]
        
        return uri

    def _render_hue_bar(self) -> str:
        """Renderiza barra de Matiz como PNG base64."""
        if "hue_bar" in self._hue_cache:
            return self._hue_cache["hue_bar"]
        
        width, height = self.size, 40
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        
        for x in range(width):
            h = x / width
            r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
            color = (int(r*255), int(g*255), int(b*255))
            draw.line([(x, 0), (x, height)], fill=color)
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = base64.b64encode(buf.getvalue()).decode()
        
        uri = f"data:image/png;base64,{data}"
        self._hue_cache["hue_bar"] = uri
        
        return uri


class EditPanel(ft.Column):
    """Panel de EdiciÃ³n profesional con color picker circular."""

    def __init__(self, wiz_manager, on_bg_change=None):
        super().__init__(expand=True, scroll="auto", spacing=16)
        self.logger = logging.getLogger(__name__)
        self.wiz = wiz_manager
        self.fav_manager = FavoritesManager()
        self.bulbs_manager = BulbsManager()
        self._on_bg_change = on_bg_change
        
        self._target_ip: str | None = None
        self._state = {
            "state": True,
            "dimming": 100,
            "r": 255,
            "g": 0,
            "b": 0,
            "cw": 0,
            "ww": 0,
            "temperature": 4200,
            "sceneId": 0,
            "speed": 100,
        }
        
        # Threading
        self._pending_state = None
        self._send_event = threading.Event()
        self._send_stop = threading.Event()
        self._send_lock = threading.Lock()
        self._send_thread = None
        self._send_scheduled_at = 0.0
        self._send_delay_s = 0.10
        
        self.padding = ft.padding.symmetric(horizontal=20, vertical=20)
        self.bgcolor = Theme.BG_DARK
        
        self._build_ui()

    def _build_ui(self):
        """Construye la interfaz."""
        
        # --- Header ---
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(ft.icons.PALETTE, color="#ffffff", size=24),
                        width=40,
                        height=40,
                        border_radius=10,
                        bgcolor=Theme.PRIMARY,
                        alignment=Theme.ALIGN_CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text("Estudio Creativo", size=20, weight="bold", color=Theme.TEXT_MAIN),
                            ft.Text("Personaliza tus luces", size=11, color=Theme.TEXT_MUTED),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=10,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.03, Theme.TEXT_MAIN),
        )
        
        # --- Selector de Bombilla ---
        self.dd_target = ft.Dropdown(
            label=" Seleccionar bombilla",
            options=[ft.dropdown.Option("", " Todas las bombillas")],
            value="",
            bgcolor=ft.Colors.with_opacity(0.05, Theme.TEXT_MAIN),
            color=Theme.TEXT_MAIN,
            border_color=ft.Colors.with_opacity(0.2, Theme.ACCENT),
            focused_border_color=Theme.ACCENT,
            width=280,
            text_size=12,
            height=50,
        )
        
        def _on_target_select(e):
            self._target_ip = (e.control.value or "").strip() or None
        
        self.dd_target.on_select = _on_target_select
        
        # --- Color Picker Circular ---
        self.picker = CircularColorPicker(
            on_color_change=self._on_picker_color_change,
            size=220
        )
        
        # --- Hex Input ---
        self.tf_hex = ft.TextField(
            label="CÃ³digo Hex",
            value="#ff0000",
            color=Theme.TEXT_MAIN,
            bgcolor=ft.Colors.with_opacity(0.05, Theme.TEXT_MAIN),
            border_color=ft.Colors.with_opacity(0.2, Theme.PRIMARY),
            focused_border_color=Theme.PRIMARY,
            width=140,
            text_size=11,
            height=50,
            content_padding=10,
        )
        
        def _on_hex_submit(e):
            s = (self.tf_hex.value or "").strip().lower()
            if not s.startswith("#"):
                s = "#" + s
            
            if not re.fullmatch(r"#[0-9a-f]{6}", s):
                self.tf_hex.error_text = "#rrggbb"
                return
            
            self.tf_hex.error_text = None
            h = s.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            self.picker.set_rgb(r, g, b)
            self._apply_rgb(r, g, b)
        
        self.tf_hex.on_submit = _on_hex_submit
        self.tf_hex.on_blur = _on_hex_submit
        
        # --- Color Preview ---
        self.preview_box = ft.Container(
            width=90,
            height=90,
            border_radius=45,
            bgcolor=Theme.PRIMARY,
            border=ft.border.all(3, Theme.ACCENT),
            shadow=ft.BoxShadow(
                blur_radius=20,
                color=ft.Colors.with_opacity(0.6, Theme.PRIMARY),
                spread_radius=1,
            ),
        )
        
        picker_row = ft.Row(
            [
                self.picker,
                ft.Column(
                    [
                        self.preview_box,
                        ft.Column(
                            [
                                ft.Text("Hex", size=10, color=Theme.TEXT_MUTED),
                                self.tf_hex,
                            ],
                            spacing=4,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
            ],
            spacing=24,
            alignment=ft.MainAxisAlignment.START,
        )
        
        # --- Favoritos ---
        self.favs_grid = ft.GridView(
            runs_count=8,
            spacing=8,
            run_spacing=8,
            child_aspect_ratio=1.0,
            expand=False,
            height=100,
        )
        
        favs_card = ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.03, Theme.TEXT_MAIN),
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, Theme.WARNING)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.icons.STAR, size=16, color=Theme.WARNING),
                            ft.Text("Favoritos", size=13, color=Theme.WARNING, weight="w600"),
                            ft.Container(expand=True),
                            ft.IconButton(
                                ft.icons.ADD_CIRCLE_OUTLINE,
                                icon_size=16,
                                icon_color=Theme.WARNING,
                                on_click=self._on_add_favorite,
                                tooltip="Agregar favorito",
                            ),
                        ],
                        spacing=6,
                    ),
                    self.favs_grid,
                ],
                spacing=8,
            ),
        )
        
        # --- Escenas EstÃ¡ticas ---
        self.static_scenes_grid = ft.GridView(
            runs_count=4,
            spacing=8,
            run_spacing=8,
            expand=False,
            height=130,
        )
        
        static_card = ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.03, Theme.SUCCESS),
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, Theme.SUCCESS)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.icons.LIGHTBULB_OUTLINE, size=16, color=Theme.SUCCESS),
                            ft.Text(" EstÃ¡ticas", size=13, color=Theme.SUCCESS, weight="w600"),
                        ],
                        spacing=6,
                    ),
                    self.static_scenes_grid,
                ],
                spacing=8,
            ),
        )
        
        # --- Escenas DinÃ¡micas ---
        self.dynamic_scenes_grid = ft.GridView(
            runs_count=4,
            spacing=8,
            run_spacing=8,
            expand=False,
            height=180,
        )
        
        dynamic_card = ft.Container(
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.03, Theme.PRIMARY),
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, Theme.PRIMARY)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.icons.AUTO_AWESOME, size=16, color=Theme.PRIMARY),
                            ft.Text(" DinÃ¡micas", size=13, color=Theme.PRIMARY, weight="w600"),
                        ],
                        spacing=6,
                    ),
                    self.dynamic_scenes_grid,
                ],
                spacing=8,
            ),
        )
        
        # --- Assemble ---
        self.controls = [
            header,
            self.dd_target,
            ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, Theme.TEXT_MAIN)),
            picker_row,
            ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, Theme.TEXT_MAIN)),
            favs_card,
            ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, Theme.TEXT_MAIN)),
            static_card,
            ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, Theme.TEXT_MAIN)),
            dynamic_card,
            ft.Container(height=20),
        ]

    def did_mount(self):
        """Inicializa el componente."""
        self._start_send_worker()
        self._refresh_targets()
        self._refresh_favorites()
        self._refresh_scenes()

    def did_unmount(self):
        """Limpia recursos."""
        self._stop_send_worker()

    def _refresh_targets(self):
        """Actualiza la lista de bombillas disponibles."""
        try:
            saved = self.bulbs_manager.get_bulbs() or {}
        except Exception:
            saved = {}
        
        detected = {}
        try:
            if hasattr(self.wiz, "get_bulb_states_snapshot"):
                snap = self.wiz.get_bulb_states_snapshot() or {}
                for ip, st in snap.items():
                    detected[ip] = {"ip": ip, "reachable": st.get("reachable", False)}
        except Exception:
            pass
        
        ips = sorted(set(list(saved.keys()) + list(detected.keys())))
        opts = [ft.dropdown.Option("", "Todas")]
        
        for ip in ips:
            name = None
            try:
                name = saved.get(ip, {}).get("name")
            except Exception:
                pass
            
            label = f"{name} ({ip})" if name else ip
            opts.append(ft.dropdown.Option(ip, label))
        
        try:
            self.dd_target.options = opts
            self.dd_target.value = self._target_ip or ""
            self.dd_target.update()
        except Exception:
            pass

    def _refresh_favorites(self):
        """Carga y muestra los favoritos."""
        self.favs_grid.controls.clear()
        
        for fav in (self.fav_manager.get_favorites() or []):
            v = fav.get("value", "")
            
            if isinstance(v, str) and v.startswith("#"):
                color_preview = v
            else:
                color_preview = Theme.TEXT_MUTED
            
            btn = ft.Container(
                width=40,
                height=40,
                border_radius=8,
                bgcolor=color_preview,
                border=ft.border.all(2, ft.Colors.with_opacity(0.4, "#ffffff")),
                shadow=ft.BoxShadow(
                    blur_radius=6,
                    color=ft.Colors.with_opacity(0.3, color_preview),
                ),
                tooltip=fav.get("name", "Favorito"),
                on_click=lambda _e, f=fav: self._apply_favorite(f),
                ink=True,
                animate_opacity=200,
            )
            self.favs_grid.controls.append(btn)
        
        try:
            self.favs_grid.update()
        except Exception:
            pass

    def _refresh_scenes(self):
        """Carga y muestra las escenas."""
        # Escenas estÃ¡ticas
        self.static_scenes_grid.controls.clear()
        
        for scene in STATIC_SCENES:
            btn = self._create_scene_button(scene)
            self.static_scenes_grid.controls.append(btn)
        
        # Escenas dinÃ¡micas
        self.dynamic_scenes_grid.controls.clear()
        
        for scene in DYNAMIC_SCENES:
            btn = self._create_scene_button(scene)
            self.dynamic_scenes_grid.controls.append(btn)
        
        try:
            self.static_scenes_grid.update()
            self.dynamic_scenes_grid.update()
        except Exception:
            pass

    def _create_scene_button(self, scene):
        """Crea un botÃ³n para una escena."""
        scene_id = scene.get("id")
        scene_name = scene.get("name", "Escena")
        scene_icon = scene.get("icon", ft.icons.LIGHTBULB_OUTLINE)
        scene_color = scene.get("color", Theme.PRIMARY)
        
        return ft.Container(
            width=70,
            height=70,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.15, scene_color),
            border=ft.border.all(2, ft.Colors.with_opacity(0.4, scene_color)),
            shadow=ft.BoxShadow(
                blur_radius=6,
                color=ft.Colors.with_opacity(0.2, scene_color),
            ),
            content=ft.Column(
                [
                    ft.Icon(scene_icon, color=scene_color, size=20),
                    ft.Text(scene_name, size=9, text_align=ft.TextAlign.CENTER, no_wrap=True, color=Theme.TEXT_MAIN),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=3,
            ),
            on_click=lambda _e, s=scene_id: self._apply_scene(s),
            ink=True,
            animate_scale=150,
        )

    def _on_picker_color_change(self, r, g, b):
        """Callback cuando cambia el color en el picker."""
        self._apply_rgb(r, g, b)

    def _apply_rgb(self, r: int, g: int, b: int):
        """Aplica un color RGB."""
        r, g, b = max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b)))
        
        self._state["r"] = r
        self._state["g"] = g
        self._state["b"] = b
        
        hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
        
        try:
            self.tf_hex.value = hex_color
            self.tf_hex.update()
        except Exception:
            pass
        
        try:
            self.preview_box.bgcolor = hex_color
            self.preview_box.shadow.color = ft.Colors.with_opacity(0.5, hex_color)
            self.preview_box.update()
        except Exception:
            pass
        
        # Enviar estado
        self._pending_state = {
            "r": r,
            "g": g,
            "b": b,
            "dimming": 100,
            "state": True,
        }
        self._schedule_send(0.08)
        
        if self._on_bg_change:
            try:
                self._on_bg_change(hex_color)
            except Exception:
                pass

    def _apply_favorite(self, fav):
        """Aplica un favorito."""
        v = fav.get("value", "")
        
        if isinstance(v, str) and v.startswith("#"):
            h = v.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            self.picker.set_rgb(r, g, b)
            self._apply_rgb(r, g, b)

    def _apply_scene(self, scene_id: int):
        """Aplica una escena."""
        def _do():
            try:
                self.wiz.set_scene(int(scene_id), ip=self._target_ip)
            except Exception:
                self.logger.exception(f"Error aplicando escena {scene_id}")
        
        try:
            if self.page:
                self.page.run_thread(_do)
            else:
                _do()
        except Exception:
            _do()

    def _on_add_favorite(self, e):
        """Abre un diÃ¡logo para agregar favorito."""
        
        def _save_fav(dlg, name_field):
            name = (name_field.value or "").strip()
            if not name:
                return
            
            hex_color = self.tf_hex.value or "#ff0000"
            self.fav_manager.add_favorite(name, "rgb", hex_color, "STAR")
            self._refresh_favorites()
            dlg.close()
        
        tf_name = ft.TextField(label="Nombre del favorito", autofocus=True)
        
        dlg = ft.AlertDialog(
            title=ft.Text("Agregar Favorito"),
            content=ft.Column([
                ft.Text("Guarda el color actual como favorito", size=12, color=Theme.TEXT_MUTED),
                tf_name,
            ], spacing=12),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: dlg.close()),
                ft.TextButton(
                    "Guardar",
                    on_click=lambda _: _save_fav(dlg, tf_name),
                    style=ft.ButtonStyle(color=Theme.SUCCESS),
                ),
            ],
        )
        
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _start_send_worker(self):
        """Inicia el worker de envÃ­o de estado."""
        if self._send_thread and self._send_thread.is_alive():
            return
        
        self._send_stop.clear()
        
        def _loop():
            while not self._send_stop.is_set():
                self._send_event.wait()
                self._send_event.clear()
                
                if self._send_stop.is_set():
                    break
                
                while not self._send_stop.is_set():
                    with self._send_lock:
                        scheduled_at = float(self._send_scheduled_at)
                        delay_s = float(self._send_delay_s)
                    
                    remaining = (scheduled_at + delay_s) - time.monotonic()
                    if remaining <= 0:
                        break
                    
                    self._send_event.wait(timeout=min(0.10, max(0.01, remaining)))
                
                if self._send_stop.is_set():
                    break
                
                st = self._pending_state
                if not st:
                    continue
                
                self._pending_state = None
                
                try:
                    self._send_state(st)
                except Exception:
                    self.logger.exception("Error enviando estado")
        
        self._send_thread = threading.Thread(target=_loop, daemon=True)
        self._send_thread.start()

    def _stop_send_worker(self):
        """Detiene el worker."""
        try:
            self._send_stop.set()
            self._send_event.set()
            if self._send_thread and self._send_thread.is_alive():
                self._send_thread.join(timeout=0.4)
        except Exception:
            pass

    def _schedule_send(self, delay_s: float = 0.10):
        """Programa un envÃ­o de estado."""
        try:
            self._start_send_worker()
            with self._send_lock:
                self._send_delay_s = float(delay_s)
                self._send_scheduled_at = time.monotonic()
            self._send_event.set()
        except Exception:
            pass

    def _send_state(self, st: dict):
        """EnvÃ­a el estado a las bombillas."""
        try:
            if hasattr(self.wiz, "set_user_interacting"):
                self.wiz.set_user_interacting(0.9)
        except Exception:
            pass
        
        try:
            if hasattr(self.wiz, "apply_piloting_state"):
                self.wiz.apply_piloting_state(st, ip=self._target_ip, emit=False)
                return
        except Exception:
            pass
        
        try:
            if all(k in st for k in ("r", "g", "b")):
                self.wiz.set_rgb(
                    int(st["r"]),
                    int(st["g"]),
                    int(st["b"]),
                    ip=self._target_ip,
                    emit=False
                )
        except Exception:
            self.logger.exception("Error enviando RGB")
