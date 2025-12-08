import flet as ft
import keyboard
import threading

class HotkeysDialog(ft.AlertDialog):
    def __init__(self, page: ft.Page, hotkeys_manager):
        super().__init__()
        self.page = page
        self.manager = hotkeys_manager
        
        # Recordar pestaña actual
        self.selected_tab_index = 0
        
        self.title = ft.Text("CONFIGURACIÓN DE ATAJOS", size=16, weight="bold", color="white")
        self.modal = True
        self.bgcolor = "#1f2937"
        
        self.static_categories = {
            "GENERAL": [
                ("Alternar (On/Off)", "toggle"),
                ("Encender", "on"), ("Apagar", "off"),
                ("Subir Brillo", "bri_up"), ("Bajar Brillo", "bri_down"),
            ],
            "TEMPERATURA": [
                ("Más Fría (+)", "temp_up"), ("Más Cálida (-)", "temp_down"),
                ("Cálida (2700K)", "temp_warm"), ("Neutra (4000K)", "temp_neutral"),
                ("Fría (6500K)", "temp_cold"),
            ],
            "VELOCIDAD FX": [
                ("Más Rápido (+)", "speed_up"), ("Más Lento (-)", "speed_down"),
                ("Velocidad Máx", "speed_max"), ("Velocidad Mín", "speed_min"),
            ],
            "ESCENAS": [
                ("🌊 Océano", "scene_ocean"), ("🌅 Atardecer", "scene_sunset"),
                ("🔥 Chimenea", "scene_fireplace"), ("🎉 Fiesta", "scene_party"),
                ("🌲 Bosque", "scene_forest"), ("🧘 Relax", "scene_relax"),
                ("💑 Romance", "scene_romance"), ("🕯️ Vela", "scene_candlelight"),
                ("📖 Lectura", "scene_focus"), ("🌙 Noche", "scene_night_light"),
            ]
        }
        
        # Tamaño responsive con límites seguros (sin usar constraints para compatibilidad)
        self.content = ft.Container(
            width=self._calc_width(),
            height=self._calc_height(),
            content=self._build_tabs_block(),
            padding=ft.padding.all(12),
        )
        
        self.actions = [
            ft.TextButton("CERRAR", style=ft.ButtonStyle(color="white"), on_click=self._close_dialog)
        ]

    # --- Dimensiones responsivas ---
    def _calc_width(self):
        base = 0.9 * (self.page.window_width or 400)
        return max(340, min(560, base))

    def _calc_height(self):
        base = 0.8 * (self.page.window_height or 700)
        return max(420, min(680, base))

    def _build_tabs(self):
        """Tabs con indicador acotado y alineación izquierda."""
        tabs = []
        for cat_name, actions in self.static_categories.items():
            content = self._build_action_list(actions)
            tabs.append(ft.Tab(text=cat_name, content=content))

        colores_content = self._build_colors_tab()
        tabs.append(ft.Tab(text="COLORES", content=colores_content))

        self.tabs_control = ft.Tabs(
            selected_index=self.selected_tab_index,
            animation_duration=300,
            tabs=tabs,
            expand=True,
            divider_color="transparent",
            indicator_color="cyan",
            indicator_tab_size=True,
            scrollable=True,
            tab_alignment=ft.TabAlignment.START,
            on_change=self._on_tab_change,
        )

        return self.tabs_control

    def _build_tabs_block(self):
        """Bloque completo: flechas + título + tabs."""
        tabs = self._build_tabs()

        # Header con flechas a los lados del título
        header_row = ft.Row(
            [
                ft.IconButton(
                    ft.Icons.CHEVRON_LEFT,
                    icon_color="white",
                    tooltip="Anterior",
                    on_click=self._prev_tab,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                ),
                self.title,
                ft.IconButton(
                    ft.Icons.CHEVRON_RIGHT,
                    icon_color="white",
                    tooltip="Siguiente",
                    on_click=self._next_tab,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        )

        return ft.Column(
            [
                header_row,
                tabs,
            ],
            spacing=10,
            expand=True,
        )

    def _on_tab_change(self, e):
        self._set_tab_index(e.control.selected_index)

    def _set_tab_index(self, new_index: int):
        # Limitar dentro del rango disponible
        max_idx = len(self.static_categories)  # +1 para COLORES
        new_index = max(0, min(new_index, max_idx))
        self.selected_tab_index = new_index
        if hasattr(self, "tabs_control") and self.tabs_control:
            self.tabs_control.selected_index = new_index
            self.tabs_control.update()

    def _prev_tab(self, e=None):
        self._set_tab_index(self.selected_tab_index - 1)

    def _next_tab(self, e=None):
        self._set_tab_index(self.selected_tab_index + 1)

    def _refresh_ui(self):
        # Actualizamos el contenido del contenedor principal
        self.content.width = self._calc_width()
        self.content.height = self._calc_height()
        self.content.content = self._build_tabs_block()
        self.page.update()

    def _build_action_list(self, actions_list, is_custom=False):
        controls = []
        current_map = self.manager.hotkeys
        
        for label, action_id in actions_list:
            current_key = current_map.get(action_id, None)
            
            key_text = current_key.upper() if current_key else "ASIGNAR"
            key_color = "cyan" if current_key else "grey"
            key_bg = ft.Colors.with_opacity(0.1, "cyan") if current_key else ft.Colors.with_opacity(0.1, "white")
            
            key_btn = ft.Container(
                content=ft.Text(key_text, size=11, color=key_color, weight="bold", text_align="center"),
                bgcolor=key_bg,
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
                border_radius=6,
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, key_color)),
                on_click=lambda e, aid=action_id: self._start_recording(aid),
                width=90,
                alignment=ft.alignment.center
            )
            
            action_buttons = []
            if is_custom:
                action_buttons.append(
                    ft.IconButton(ft.Icons.DELETE_FOREVER, icon_size=18, icon_color="red", 
                    tooltip="Eliminar color", on_click=lambda e, aid=action_id: self._delete_custom_action(aid))
                )
            else:
                action_buttons.append(
                    ft.IconButton(ft.Icons.CLOSE, icon_size=16, icon_color="red", 
                    visible=bool(current_key), tooltip="Quitar atajo", 
                    on_click=lambda e, aid=action_id: self._remove_hotkey(aid))
                )

            row = ft.Container(
                bgcolor=ft.Colors.with_opacity(0.05, "black"),
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                border_radius=8,
                content=ft.Row(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.PALETTE if is_custom else ft.Icons.KEYBOARD_ARROW_RIGHT, size=16, color="grey"),
                            ft.Text(label, size=13, color="white", no_wrap=False, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ], expand=True), 
                        ft.Row([key_btn] + action_buttons, spacing=0)
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            )
            controls.append(row)
            
        return ft.Column(controls, scroll=ft.ScrollMode.AUTO, spacing=5, expand=True)

    def _build_colors_tab(self):
        add_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.ADD_CIRCLE, color="black"),
                ft.Text("GUARDAR COLOR ACTUAL COMO ATAJO", color="black", weight="bold", size=11)
            ], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="cyan", border_radius=8, padding=10,
            on_click=self._add_current_color, margin=ft.margin.only(bottom=10)
        )
        
        base_colors = [
            ("🔴 Rojo", "color_red"), ("🟢 Verde", "color_green"),
            ("🔵 Azul", "color_blue"),
        ]
        
        custom_list = []
        for aid, data in self.manager.custom_actions.items():
            if data['type'] == 'rgb':
                custom_list.append((data['name'], aid))
        
        list_content = ft.Column([
            ft.Text("Colores Base", size=12, color="grey", weight="bold"),
            self._build_action_list(base_colors, is_custom=False),
            ft.Divider(color="transparent", height=10),
            ft.Text("Mis Colores Personalizados", size=12, color="grey", weight="bold"),
            self._build_action_list(custom_list, is_custom=True)
        ], scroll=ft.ScrollMode.AUTO, expand=True)
        
        return ft.Container(
            content=ft.Column([add_btn, list_content], expand=True),
            padding=ft.padding.only(top=10),
            expand=True
        )

    # --- LÓGICA ---

    def _add_current_color(self, e):
        state = self.manager.wiz.get_state()
        # Validación robusta
        rgb = state.get("rgb", (0,0,0))
        if rgb is None: rgb = (0,0,0)
        
        r, g, b = rgb
        aid, name = self.manager.add_custom_color(r, g, b)
        self._refresh_ui()
        self._start_recording(aid)

    def _delete_custom_action(self, action_id):
        self.manager.remove_custom_action(action_id)
        self._refresh_ui()

    def _remove_hotkey(self, action_id):
        self.manager.remove_hotkey(action_id)
        self._refresh_ui()

    def _start_recording(self, action_id):
        self.title.value = "🔴 PULSA LA COMBINACIÓN..."
        self.title.color = "red"
        self.page.update()
        
        def _wait_key():
            try:
                key = keyboard.read_hotkey(suppress=False)
                self.manager.set_hotkey(action_id, key)
                self.title.value = "CONFIGURACIÓN DE ATAJOS"
                self.title.color = "white"
                self._refresh_ui()
            except: pass

        threading.Thread(target=_wait_key, daemon=True).start()

    def _close_dialog(self, e):
        self.open = False
        self.page.update()