import flet as ft
from config.favorites_manager import FavoritesManager
from ui.wiz_constants import STATIC_SCENES, DYNAMIC_SCENES, RICH_RAINBOW

class FavoritesPanel(ft.Container):
    def __init__(self, wiz_manager):
        super().__init__(padding=20, expand=True, bgcolor="#111111")
        self.wiz = wiz_manager
        self.fav_manager = FavoritesManager()
        self.c_bg_card = "#1e1e1e"
        self.c_accent = "#facc15" 
        
        self.grid = ft.GridView(expand=True, runs_count=5, max_extent=160, child_aspect_ratio=0.9, spacing=15, run_spacing=15)
        
        self.content = ft.Column([
            ft.Row([
                ft.Container(content=ft.Icon(ft.Icons.FLASH_ON, color="black"), padding=8, bgcolor=self.c_accent, border_radius=10),
                ft.Text("ACCIONES RÁPIDAS", size=18, weight="bold", color="white"),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Nuevo", icon=ft.Icons.ADD, 
                    bgcolor="#333333", color="white", 
                    on_click=lambda e: self._open_visual_editor(is_new=True)
                )
            ]),
            ft.Divider(color="#333"), 
            self.grid
        ])
        self.refresh()

    def refresh(self):
        self.grid.controls.clear()
        for d in self.fav_manager.get_favorites():
            icon = getattr(ft.Icons, d.get("icon_name", "STAR"), ft.Icons.STAR)
            # Color del icono: Si es hex lo usa, si no usa el acento amarillo
            col = d.get("value") if str(d.get("value")).startswith("#") else self.c_accent
            
            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon, color=col), 
                        ft.Container(expand=True), 
                        ft.PopupMenuButton(icon=ft.Icons.MORE_VERT, icon_color="grey", items=[
                            ft.PopupMenuItem(text="Editar", icon=ft.Icons.EDIT, on_click=lambda e, x=d: self._open_visual_editor(False, x)),
                            ft.PopupMenuItem(text="Eliminar", icon=ft.Icons.DELETE, on_click=lambda e, x=d["id"]: self._del(x))
                        ])
                    ]),
                    ft.Container(expand=True),
                    ft.Text(d["name"], weight="bold", color="white", size=14),
                    ft.Container(
                        content=ft.Text(d["type"].upper(), size=10, color="black", weight="bold"),
                        bgcolor=col, padding=ft.padding.symmetric(horizontal=6, vertical=2), border_radius=4
                    )
                ]),
                bgcolor=self.c_bg_card, padding=12, border_radius=12, border=ft.border.all(1, "#333"),
                shadow=ft.BoxShadow(blur_radius=5, color="#1a000000"),
                on_click=lambda e, x=d: self._act(x)
            )
            self.grid.controls.append(card)
        if self.page: self.update()

    def _act(self, d):
        try:
            v = d["value"]
            if d["type"] == "rgb": 
                h = v.lstrip('#')
                self.wiz.set_rgb(*tuple(int(h[i:i+2], 16) for i in (0, 2, 4)))
            elif d["type"] == "white": self.wiz.set_white(int(v))
            elif d["type"] == "scene": self.wiz.set_scene(int(v))
            self.page.show_snack_bar(ft.SnackBar(ft.Text(f"Activado: {d['name']}"), bgcolor="green"))
        except: pass

    def _del(self, uid): 
        self.fav_manager.remove_favorite(uid)
        self.refresh()
    
    # --- EDITOR VISUAL NUEVO ---
    def _open_visual_editor(self, is_new, d=None):
        if not self.page: return
        d = d or {}
        
        # Variables de estado para el diálogo
        self.edit_name = ft.TextField(label="Nombre", value=d.get("name", ""), color="white", bgcolor="#222")
        self.edit_val = str(d.get("value", ""))
        self.edit_type = d.get("type", "rgb")
        
        # Previsualización
        self.preview_box = ft.Container(width=40, height=40, border_radius=20, bgcolor="grey")
        self._update_preview(self.edit_val, self.edit_type)

        # 1. Contenido Tab COLOR
        color_grid = ft.Row(wrap=True, spacing=5, controls=[
            ft.Container(
                width=30, height=30, bgcolor=c, border_radius=15, 
                on_click=lambda e, c=c: self._set_edit_val(c, "rgb"),
                border=ft.border.all(1, "white")
            ) for c in RICH_RAINBOW
        ])
        tab_color = ft.Column([ft.Text("Selecciona un color:", size=12), color_grid], spacing=10)

        # 2. Contenido Tab BLANCO
        white_opts = [("Cálido", "2700", "#ffaa00"), ("Neutro", "4200", "#fff"), ("Frío", "6500", "#ccffff")]
        white_row = ft.Row(controls=[
            ft.ElevatedButton(txt, bgcolor="#333", color=col, on_click=lambda e, v=val: self._set_edit_val(v, "white")) 
            for txt, val, col in white_opts
        ])
        tab_white = ft.Column([ft.Text("Selecciona temperatura:", size=12), white_row], spacing=10)

        # 3. Contenido Tab ESCENA
        # Llenamos el dropdown con nombres reales
        all_scenes = STATIC_SCENES + DYNAMIC_SCENES
        dd_scenes = ft.Dropdown(
            label="Escena", 
            value=self.edit_val if self.edit_type == "scene" else None,
            options=[ft.dropdown.Option(str(s["id"]), s["name"]) for s in all_scenes],
            color="white", bgcolor="#222",
            on_change=lambda e: self._set_edit_val(e.control.value, "scene")
        )
        tab_scene = ft.Column([dd_scenes], spacing=10)

        # TABS CONTROL
        tabs = ft.Tabs(
            selected_index={"rgb": 0, "white": 1, "scene": 2}.get(self.edit_type, 0),
            animation_duration=300,
            indicator_color=self.c_accent,
            on_change=lambda e: self._on_tab_change(e.control.selected_index),
            tabs=[
                ft.Tab(text="Color", content=ft.Container(content=tab_color, padding=10)),
                ft.Tab(text="Blanco", content=ft.Container(content=tab_white, padding=10)),
                ft.Tab(text="Escena", content=ft.Container(content=tab_scene, padding=10)),
            ],
            expand=True
        )

        def save(e):
            # Icono automático
            icon = "STAR"
            if self.edit_type == "rgb": icon = "COLOR_LENS"
            elif self.edit_type == "white": icon = "WB_SUNNY"
            elif self.edit_type == "scene": icon = "THEATER_COMEDY"
            
            # Nombre automático si está vacío
            final_name = self.edit_name.value or f"Acción {self.edit_type}"
            
            if is_new: 
                self.fav_manager.add_favorite(final_name, self.edit_type, self.edit_val, icon)
            else: 
                self.fav_manager.update_favorite(d["id"], final_name, self.edit_type, self.edit_val, icon)
            
            self.page.close(dlg)
            self.refresh()

        dlg = ft.AlertDialog(
            title=ft.Row([ft.Text("Editor Visual"), self.preview_box], alignment="spaceBetween"),
            bgcolor="#1e1e1e",
            content=ft.Container(content=ft.Column([self.edit_name, tabs], tight=True), width=350, height=300),
            actions=[ft.ElevatedButton("Guardar Acción", bgcolor=self.c_accent, color="black", on_click=save)]
        )
        self.page.open(dlg)

    def _set_edit_val(self, val, type_):
        self.edit_val = str(val)
        self.edit_type = type_
        self._update_preview(val, type_)
        
    def _on_tab_change(self, index):
        types = ["rgb", "white", "scene"]
        if index < len(types):
            self.edit_type = types[index]
            # Reset visual temporal
            if self.edit_type == "rgb": self._set_edit_val("#ff0000", "rgb")
            elif self.edit_type == "white": self._set_edit_val("4200", "white")

    def _update_preview(self, val, type_):
        col = "grey"
        if type_ == "rgb" and str(val).startswith("#"): col = val
        elif type_ == "white": col = "#ffffff"
        elif type_ == "scene": col = "#9c27b0"
        self.preview_box.bgcolor = col
        self.preview_box.update()