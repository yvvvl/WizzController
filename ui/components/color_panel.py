import flet as ft
import math
import time
import time as _time
from config.presets_manager import PresetsManager

class HueRing(ft.Stack):
    def __init__(self, on_hue_change, size=280, thickness=36):
        self.on_change = on_hue_change
        self.size = size
        self.thickness = thickness
        self.center_coord = size / 2
        self._angle = 0.0 
        
        # 1. El Anillo de Color (Fondo)
        self.gradient_ring = ft.Container(
            width=size, height=size,
            border_radius=size/2,
            gradient=ft.SweepGradient(
                center=ft.alignment.center,
                colors=[
                    ft.Colors.RED, ft.Colors.YELLOW, ft.Colors.GREEN,
                    ft.Colors.CYAN, ft.Colors.BLUE, ft.Colors.PURPLE, ft.Colors.RED
                ],
            ),
            border=ft.border.all(2, "#3a3f47"),
            shadow=ft.BoxShadow(blur_radius=16, color="#00000066", offset=ft.Offset(0, 4))
        )

        # 2. Máscara central
        self.mask = ft.Container(
            width=size - (thickness * 2), 
            height=size - (thickness * 2),
            border_radius=(size - thickness*2)/2,
            bgcolor="#1e293b", 
            left=thickness, top=thickness,
        )

        # 3. El Selector (Bolita)
        self.thumb = ft.Container(
            width=28, height=28, border_radius=14, bgcolor="#f2f2f2",
            border=ft.border.all(2, "#1a1a1a"),
            shadow=ft.BoxShadow(blur_radius=16, color="#00000066", offset=ft.Offset(0, 4)),
            left=0, top=0
        )

        # 4. Detector Invisible (Capa Superior)
        self.glass_layer = ft.GestureDetector(
            content=ft.Container(width=size, height=size, bgcolor=ft.Colors.TRANSPARENT),
            on_pan_update=self._on_pan,
            on_tap_down=self._on_pan
        )

        super().__init__(controls=[self.gradient_ring, self.mask, self.thumb, self.glass_layer], width=size, height=size)
        self._update_thumb_position(0, update_mode=False)

    def _on_pan(self, e):
        x = e.local_x - self.center_coord; y = e.local_y - self.center_coord
        angle = math.atan2(y, x)
        self._update_thumb_position(angle, update_mode=True)
        deg = math.degrees(angle)
        if deg < 0: deg += 360
        self.on_change(deg)

    def _update_thumb_position(self, angle, update_mode=True):
        self._angle = angle
        track_radius = (self.size - self.thickness) / 2
        thumb_offset = 14
        self.thumb.left = self.center_coord + track_radius * math.cos(angle) - thumb_offset
        self.thumb.top = self.center_coord + track_radius * math.sin(angle) - thumb_offset
        if update_mode: self.thumb.update()

    def resize(self, new_size, new_thickness):
        self.size = new_size; self.thickness = new_thickness; self.center_coord = new_size / 2
        self.width = new_size; self.height = new_size
        self.gradient_ring.width = new_size; self.gradient_ring.height = new_size
        self.gradient_ring.border_radius = new_size/2
        self.mask.width = new_size - (new_thickness * 2); self.mask.height = new_size - (new_thickness * 2)
        self.mask.border_radius = (new_size - new_thickness*2)/2
        self.mask.left = new_thickness; self.mask.top = new_thickness
        self.glass_layer.content.width = new_size; self.glass_layer.content.height = new_size
        self._update_thumb_position(self._angle, update_mode=False)
        self.update()

class ColorPanel(ft.Container):
    def __init__(self, wiz_manager):
        super().__init__()
        self.wiz = wiz_manager
        self.presets_manager = PresetsManager()
        
        self.expand = True; self.padding = 20; self.bgcolor = ft.Colors.TRANSPARENT 
        
        # Inicializa en color pleno para evitar confusión visual hasta la primera sincronización
        self._hue_deg = 0; self._sat = 1.0; self._val = 1.0
        self._sat_last_ts = 0.0; self._val_last_ts = 0.0; self._min_interval_sec = 0.02

        # Preview Box
        self.preview_hex = ft.Text("#FFFFFF", size=12, color="#bbb")
        self.preview_rgb = ft.Text("Modo: Blanco", size=12, color="#888")
        self.preview_box = ft.Container(
            width=100, height=60, border_radius=12, bgcolor="#ffffff",
            border=ft.border.all(2, "#3a3f47"),
            shadow=ft.BoxShadow(blur_radius=12, color="#00000055", offset=ft.Offset(0, 3)),
            content=ft.Column([
                self.preview_hex, 
                self.preview_rgb,
                ft.Text("GUARDAR", size=8, color="#555", weight="bold")
            ], spacing=0, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            on_click=self._open_save_dialog,
            tooltip="Click para guardar en Favoritos"
        )

        # Sliders
        self.lbl_sat = ft.Text("100%", size=12, color="#bbb")
        self.lbl_val = ft.Text("100%", size=12, color="#bbb")
        
        self.slider_sat = ft.Slider(min=0, max=100, value=100, label=None, height=10,
                         active_color="#86b6ff", inactive_color="#3a3f47", thumb_color="#cfe2ff",
                         on_change=self._on_sat_change)
        
        self.slider_val = ft.Slider(min=0, max=100, value=100, label=None, height=10,
                         active_color="#86b6ff", inactive_color="#3a3f47", thumb_color="#cfe2ff",
                         on_change=self._on_val_change)

        self.hue_ring = HueRing(on_hue_change=self._on_hue_change, size=280, thickness=36)

        # Grid de Favoritos
        self.presets_row = ft.Row(wrap=True, spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        self._load_presets_ui()

        # Layout
        self.content = ft.Column([
            ft.Row([
                ft.Column([
                    ft.Text("COLOR PICKER", color="white", size=14, weight="bold"),
                    ft.Text("Mezcla RGB + W", color="grey", size=10),
                ]),
                ft.Container(expand=True),
                self.preview_box
            ]),
            ft.Container(height=10),
            ft.Container(content=self.hue_ring, alignment=ft.alignment.center, expand=False),
            ft.Container(height=20),
            ft.Text("SATURACIÓN", color="#94a3b8", size=10, weight="bold"),
            ft.Row([ft.Icon(ft.Icons.COLOR_LENS, size=16, color="#94a3b8"), ft.Container(expand=True), self.lbl_sat]),
            self.slider_sat,
            ft.Text("BRILLO", color="#94a3b8", size=10, weight="bold"),
            ft.Row([ft.Icon(ft.Icons.TONALITY, size=16, color="#94a3b8"), ft.Container(expand=True), self.lbl_val]),
            self.slider_val,
            ft.Divider(color="#334155", height=30),
            ft.Row([
                ft.Text("MIS COLORES", color="white", size=12, weight="bold"),
                ft.Container(expand=True),
                ft.IconButton(icon=ft.Icons.ADD_CIRCLE_OUTLINE, icon_color="#38bdf8", tooltip="Guardar actual", on_click=self._open_save_dialog)
            ]),
            # Contenedor de presets (sin constraints para compatibilidad)
            ft.Container(
                content=self.presets_row,
                padding=10,
                bgcolor="#0f172a",
                border_radius=10,
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.HIDDEN)

    # --- LÓGICA DE PRESETS (CRUD) ---
    def _load_presets_ui(self):
        self.presets_row.controls.clear()
        presets = self.presets_manager.get_presets()
        
        if not presets:
            self.presets_row.controls.append(ft.Text("Sin favoritos guardados", color="grey", size=12))
        else:
            for name, rgb in presets.items():
                self.presets_row.controls.append(self._crear_preset_chip(name, rgb))
        
        if self.presets_row.page:
            self.presets_row.update()

    def _crear_preset_chip(self, name, rgb):
        r, g, b = rgb
        color_hex = f"#{r:02X}{g:02X}{b:02X}"
        return ft.Container(
            width=36, height=36, border_radius=18, bgcolor=color_hex,
            border=ft.border.all(2, "#333"),
            tooltip=f"{name}\nClick para aplicar\nClick derecho para borrar",
            on_click=lambda e: self._aplicar_preset(rgb),
            on_long_press=lambda e: self._borrar_preset(name),
            ink=True
        )

    def _open_save_dialog(self, e):
        txt_name = ft.TextField(label="Nombre del color", autofocus=True)
        def close_dlg(e): self.page.close_dialog()
        def save_preset(e):
            name = txt_name.value.strip() or "Color sin nombre"
            rgb = self._hsv_to_rgb(self._hue_deg, self._sat, self._val)
            self.presets_manager.add_preset(name, list(rgb))
            self._load_presets_ui()
            self.page.close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"Guardado: {name}"), bgcolor="green"))

        dlg = ft.AlertDialog(
            title=ft.Text("Guardar Color"), content=txt_name,
            actions=[ft.TextButton("Cancelar", on_click=close_dlg), ft.TextButton("Guardar", on_click=save_preset)],
        )
        self.page.show_dialog(dlg)

    def _borrar_preset(self, name):
        def confirm_delete(e):
            self.presets_manager.delete_preset(name)
            self._load_presets_ui()
            self.page.close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"Eliminado: {name}"), bgcolor="red"))

        dlg = ft.AlertDialog(
            title=ft.Text("¿Eliminar color?"),
            content=ft.Text(f"Vas a borrar '{name}' de tus favoritos."),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: self.page.close_dialog()), ft.TextButton("Eliminar", on_click=confirm_delete, style=ft.ButtonStyle(color="red"))],
        )
        self.page.show_dialog(dlg)

    def _aplicar_preset(self, rgb):
        r, g, b = rgb
        self._hue_deg = self._rgb_to_hue_deg((r, g, b))
        self._sat = 1.0; self._val = 1.0
        self.slider_sat.value = 100; self.slider_val.value = 100
        self.lbl_sat.value = "100%"; self.lbl_val.value = "100%"
        self.slider_sat.update(); self.slider_val.update(); self.lbl_sat.update(); self.lbl_val.update()
        self._update_logic()

    # --- LÓGICA DE COLOR ---
    def set_mode(self, compact: bool = False, wide: bool = False):
        if compact: self.padding = 10; self.hue_ring.resize(200, 25)
        elif wide: self.padding = 40; self.hue_ring.resize(320, 45)
        else: self.padding = 30; self.hue_ring.resize(280, 36)
        self.update()

    def _cambiar_color(self, hex_code):
        h = hex_code.lstrip('#'); rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        self._hue_deg = self._rgb_to_hue_deg(rgb)
        self._sat = 1.0; self._val = 1.0
        self.slider_sat.value = 100; self.slider_val.value = 100
        self.lbl_sat.value = "100%"; self.lbl_val.value = "100%"
        self.slider_sat.update(); self.slider_val.update(); self.lbl_sat.update(); self.lbl_val.update()
        self._update_logic()

    def _on_hue_change(self, deg):
        self._hue_deg = deg
        self._update_logic()

    def _on_sat_change(self, e):
        val = int(e.control.value)
        self._sat = val / 100.0
        self.lbl_sat.value = f"{val}%"
        self.lbl_sat.update()
        self._update_logic()

    def _on_val_change(self, e):
        val = int(e.control.value)
        self._val = val / 100.0
        self.lbl_val.value = f"{val}%"
        self.lbl_val.update()
        if val == 0:
            self.wiz.turn_off()
            self.preview_box.bgcolor = "#000000"
            self.preview_hex.value = "OFF"
            self.preview_rgb.value = "Apagado"
            self.preview_box.update(); self.preview_hex.update(); self.preview_rgb.update()
            return
        self._update_logic()

    def _update_logic(self):
        if self._val == 0: return
        rgb_pure = self._hsv_to_rgb(self._hue_deg, 1.0, self._val) 
        warm_white = int((1.0 - self._sat) * 255 * self._val)
        
        visual_sat_rgb = self._hsv_to_rgb(self._hue_deg, self._sat, 1.0)
        visual_r = int(visual_sat_rgb[0] * self._val)
        visual_g = int(visual_sat_rgb[1] * self._val)
        visual_b = int(visual_sat_rgb[2] * self._val)
        hex_code = f"#{visual_r:02X}{visual_g:02X}{visual_b:02X}"
        self.preview_box.bgcolor = hex_code
        self.preview_hex.value = hex_code
        
        if self._sat < 0.05:
            self.preview_rgb.value = "Modo: Blanco"
            self.wiz.set_temperature(2700) 
        else:
            self.preview_rgb.value = f"RGB: {visual_r},{visual_g},{visual_b}"
            self.wiz.set_color(rgb_pure, warm_white)

        self.preview_box.update(); self.preview_hex.update(); self.preview_rgb.update()

    def _hsv_to_rgb(self, h_deg, s, v):
        h = (h_deg % 360) / 60.0; c = v * s; x = c * (1 - abs((h % 2) - 1)); m = v - c
        r, g, b = 0, 0, 0
        if 0<=h<1: r,g,b = c,x,0
        elif 1<=h<2: r,g,b = x,c,0
        elif 2<=h<3: r,g,b = 0,c,x
        elif 3<=h<4: r,g,b = 0,x,c
        elif 4<=h<5: r,g,b = x,0,c
        elif 5<=h<6: r,g,b = c,0,x
        return (int((r+m)*255), int((g+m)*255), int((b+m)*255))

    def _rgb_to_hue_deg(self, rgb):
        r, g, b = [x/255.0 for x in rgb]
        mx, mn = max(r,g,b), min(r,g,b); d = mx - mn
        if d == 0: return 0
        if mx == r: h = (g-b)/d % 6
        elif mx == g: h = (b-r)/d + 2
        else: h = (r-g)/d + 4
        return h * 60