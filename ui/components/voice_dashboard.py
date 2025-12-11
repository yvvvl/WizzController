import flet as ft
from ui.styles import Theme
from core.voice_controller import VoiceController

class VoiceDashboard(ft.Container):
    def __init__(self, voice_controller: VoiceController):
        super().__init__()
        self.voice = voice_controller
        self.expand = True
        self.custom_color_rgb = [255, 255, 255]
        
        # Estado para Edición
        self.editing_cmd_id = None  # ID del comando que se está editando
        
        self.voice.set_callbacks(
            on_status=self._update_status_indicator,
            on_text=self._add_log_entry,
            on_command=self._show_command_feedback,
            on_unknown=self._update_suggestions 
        )
        self._build_ui()
        
    def did_mount(self):
        if not self.page: return
        self._update_status_indicator("listening" if self.voice.listening else "paused")
        self._refresh_commands_list()
        self._sync_wake_word_ui()
        self._load_microphones()

    def _build_ui(self):
        self.monitor_tab = self._build_monitor_tab()
        self.commands_tab = self._build_commands_tab()
        self.suggestions_tab = self._build_suggestions_tab()

        self.tabs = ft.Tabs(
            selected_index=0, 
            animation_duration=300,
            tabs=[
                ft.Tab(text="Monitor", icon=ft.Icons.DASHBOARD_CUSTOMIZE, content=self.monitor_tab),
                ft.Tab(text="Comandos", icon=ft.Icons.LIST_ALT, content=self.commands_tab),
                ft.Tab(text="Aprendizaje", icon=ft.Icons.AUTO_FIX_HIGH, content=self.suggestions_tab),
            ],
            expand=True, 
            divider_color="transparent", 
            indicator_color=Theme.PRIMARY,
            label_color=Theme.PRIMARY,
            unselected_label_color=Theme.TEXT_MUTED
        )
        self.content = self.tabs

    # --- PESTAÑA COMANDOS (CRUD COMPLETO) ---
    def _build_commands_tab(self):
        # Campos del formulario
        self.cmd_phrase = ft.TextField(
            label="Frase", hint_text="Ej: luz gaming", 
            expand=True, bgcolor=Theme.BG_DARK, border_color="transparent", text_size=13
        )
        
        self.cmd_action = ft.Dropdown(
            label="Acción",
            options=[
                ft.dropdown.Option("turn_on", "Encender"),
                ft.dropdown.Option("turn_off", "Apagar"),
                ft.dropdown.Option("toggle", "Alternar"),
                ft.dropdown.Option("brightness_up", "Subir Brillo"),
                ft.dropdown.Option("brightness_down", "Bajar Brillo"),
                ft.dropdown.Option("custom_color", "🎨 Color Personalizado..."),
            ],
            width=200, bgcolor=Theme.BG_DARK, border_color="transparent", text_size=13,
            on_change=self._on_action_change
        )

        # Selector de Color
        self.color_preview = ft.Container(width=40, height=40, bgcolor="white", border_radius=20, border=ft.border.all(2, "white"))
        self.slider_r = ft.Slider(min=0, max=255, value=255, active_color="red", on_change=self._update_color_preview)
        self.slider_g = ft.Slider(min=0, max=255, value=255, active_color="green", on_change=self._update_color_preview)
        self.slider_b = ft.Slider(min=0, max=255, value=255, active_color="blue", on_change=self._update_color_preview)

        self.color_picker_container = ft.Container(
            visible=False,
            content=ft.Column([
                ft.Row([ft.Text("Color Objetivo:", size=12), self.color_preview], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("R", color="red", size=10), self.slider_r], spacing=0),
                ft.Row([ft.Text("G", color="green", size=10), self.slider_g], spacing=0),
                ft.Row([ft.Text("B", color="blue", size=10), self.slider_b], spacing=0),
            ]),
            padding=15, bgcolor=Theme.BG_DARK, border_radius=10
        )
        
        # Botones de Acción (Guardar / Cancelar)
        self.btn_save_cmd = ft.ElevatedButton(
            "Guardar Comando", icon=ft.Icons.SAVE, 
            style=Theme.BUTTON_STYLE_PRIMARY, 
            on_click=self._save_command_logic
        )
        
        self.btn_cancel_edit = ft.TextButton(
            "Cancelar Edición", icon=ft.Icons.CANCEL, 
            visible=False, 
            style=ft.ButtonStyle(color=Theme.ERROR),
            on_click=self._cancel_edit_mode
        )

        self.form_title = ft.Text("NUEVO COMANDO", style=Theme.LABEL)

        form = ft.Container(
            content=ft.Column([
                ft.Row([self.form_title, self.btn_cancel_edit], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([self.cmd_phrase, self.cmd_action]),
                self.color_picker_container,
                ft.Row([self.btn_save_cmd], alignment=ft.MainAxisAlignment.END)
            ]),
            padding=20, bgcolor=Theme.CARD_BG, border_radius=Theme.CARD_RADIUS, border=Theme.CARD_BORDER
        )

        self.commands_list_view = ft.Column(spacing=10, scroll="auto")
        
        return ft.Container(
            content=ft.Column([
                form, 
                ft.Divider(height=20, color="transparent"), 
                ft.Text("MIS COMANDOS", style=Theme.LABEL), 
                ft.Container(content=self.commands_list_view, expand=True)
            ], expand=True),
            padding=10, expand=True
        )

    # --- LÓGICA CRUD ---

    def _save_command_logic(self, e):
        """Maneja tanto Creación como Actualización"""
        phrase = self.cmd_phrase.value
        action = self.cmd_action.value
        
        if not phrase or not action:
            self.page.open(ft.SnackBar(ft.Text("Por favor completa los campos"), bgcolor=Theme.ERROR))
            return

        # Procesar acción de color
        final_action = action
        if action == "custom_color":
            r, g, b = self.custom_color_rgb
            final_action = f"set_color_{int(r)}_{int(g)}_{int(b)}"

        if self.editing_cmd_id:
            # MODO ACTUALIZAR
            self.voice.manager.update_command(self.editing_cmd_id, phrase, final_action, "Usuario")
            self.page.open(ft.SnackBar(ft.Text("Comando actualizado"), bgcolor=Theme.SUCCESS))
            self._cancel_edit_mode(None) # Salir modo edición
        else:
            # MODO CREAR
            self.voice.manager.add_command(phrase, final_action, "Usuario")
            self.page.open(ft.SnackBar(ft.Text("Comando creado"), bgcolor=Theme.SUCCESS))
            self.cmd_phrase.value = "" # Limpiar solo si es nuevo
        
        self._refresh_commands_list()
        self.update()

    def _load_command_for_edit(self, cmd):
        """Carga los datos de un comando en el formulario"""
        self.editing_cmd_id = cmd['id']
        
        # 1. Interfaz Visual
        self.form_title.value = "EDITANDO COMANDO"
        self.form_title.color = Theme.ACCENT
        self.btn_save_cmd.text = "Actualizar Comando"
        self.btn_save_cmd.icon = ft.Icons.UPDATE
        self.btn_cancel_edit.visible = True
        
        # 2. Datos
        self.cmd_phrase.value = cmd['phrases']
        
        # 3. Restaurar Acción (Manejo especial para colores)
        action_code = cmd['action']
        if action_code.startswith("set_color_"):
            self.cmd_action.value = "custom_color"
            self.color_picker_container.visible = True
            
            # Parsear RGB
            try:
                parts = action_code.split("_") # set, color, r, g, b
                r, g, b = int(parts[2]), int(parts[3]), int(parts[4])
                self.slider_r.value = r
                self.slider_g.value = g
                self.slider_b.value = b
                self._update_color_preview(None)
            except: pass
        else:
            self.cmd_action.value = action_code
            self.color_picker_container.visible = False
            
        self.update()

    def _cancel_edit_mode(self, e):
        """Limpia el formulario y vuelve a modo Crear"""
        self.editing_cmd_id = None
        self.cmd_phrase.value = ""
        self.cmd_action.value = None
        self.color_picker_container.visible = False
        
        # Restaurar UI
        self.form_title.value = "NUEVO COMANDO"
        self.form_title.color = None
        self.btn_save_cmd.text = "Guardar Comando"
        self.btn_save_cmd.icon = ft.Icons.SAVE
        self.btn_cancel_edit.visible = False
        self.update()

    def _refresh_commands_list(self):
        self.commands_list_view.controls.clear()
        cmds = self.voice.manager.get_commands()
        
        if not cmds: 
            self.commands_list_view.controls.append(ft.Text("No hay comandos personalizados", color="grey", size=12))
        
        for cmd in cmds:
            action_display = cmd['action']
            icon = ft.Icons.TOUCH_APP
            icon_color = Theme.ACCENT
            
            if action_display.startswith("set_color_"):
                try:
                    parts = action_display.split("_")
                    r, g, b = int(parts[2]), int(parts[3]), int(parts[4])
                    action_display = f"RGB({r},{g},{b})"
                    icon = ft.Icons.COLORIZE
                    icon_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
                except: pass

            card = ft.Container(
                content=ft.Row([
                    ft.Icon(icon, color=icon_color),
                    ft.Column([
                        ft.Text(cmd['phrases'], weight="bold"), 
                        ft.Text(f"→ {action_display}", size=12, color=Theme.TEXT_MUTED)
                    ], expand=True),
                    
                    # Botón EDITAR (NUEVO)
                    ft.IconButton(
                        ft.Icons.EDIT, icon_color=Theme.PRIMARY, tooltip="Editar",
                        on_click=lambda e, c=cmd: self._load_command_for_edit(c)
                    ),
                    # Botón ELIMINAR
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE, icon_color=Theme.ERROR, tooltip="Eliminar",
                        on_click=lambda e, uid=cmd['id']: self._delete_command(uid)
                    )
                ]),
                padding=10, bgcolor=Theme.BG_CARD, border_radius=10, border=ft.border.all(1, "#334155")
            )
            self.commands_list_view.controls.append(card)
        
        if self.page: self.commands_list_view.update()

    # --- RESTO DE MÉTODOS (Sin cambios) ---
    def _delete_command(self, uid):
        # Si borras el que estás editando, cancelamos la edición
        if self.editing_cmd_id == uid:
            self._cancel_edit_mode(None)
        self.voice.manager.remove_command(uid)
        self._refresh_commands_list()

    def _on_action_change(self, e):
        self.color_picker_container.visible = (self.cmd_action.value == "custom_color")
        self.update()

    def _update_color_preview(self, e):
        r, g, b = int(self.slider_r.value), int(self.slider_g.value), int(self.slider_b.value)
        self.custom_color_rgb = [r, g, b]
        self.color_preview.bgcolor = "#{:02x}{:02x}{:02x}".format(r, g, b)
        self.update()

    # (Métodos de Sugerencias y Monitor se mantienen igual que en la versión anterior)
    def _build_suggestions_tab(self):
        self.suggestions_list = ft.ListView(expand=True, spacing=10, padding=10)
        return ft.Container(content=ft.Column([ft.Container(bgcolor=ft.Colors.with_opacity(0.1, Theme.ACCENT), padding=15, border_radius=10, content=ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, color=Theme.ACCENT), ft.Text("Si repites una palabra y Wizz no la entiende, aparecerá aquí para que la asignes.", size=12, color="white", expand=True)])), ft.Text("PALABRAS FRECUENTES NO RECONOCIDAS", style=Theme.LABEL), self.suggestions_list]), padding=20)

    def _update_suggestions(self, unknown_words):
        self.suggestions_list.controls.clear()
        if not unknown_words: self.suggestions_list.controls.append(ft.Text("Todo en orden.", color="grey"))
        for word in unknown_words:
            self.suggestions_list.controls.append(ft.Container(bgcolor=Theme.CARD_BG, padding=15, border_radius=12, border=Theme.CARD_BORDER, content=ft.Row([ft.Column([ft.Text(f"'{word}'", weight="bold", size=16, color="white"), ft.Text("Detectado varias veces", size=10, color=Theme.ACCENT)], expand=True), ft.ElevatedButton("Es Activador", icon=ft.Icons.MIC, style=ft.ButtonStyle(color="white", bgcolor="#334155"), on_click=lambda e, w=word: self._add_as_wake_word(w)), ft.ElevatedButton("Es Comando", icon=ft.Icons.ADD_LINK, style=Theme.BUTTON_STYLE_PRIMARY, on_click=lambda e, w=word: self._prefill_command(w))])))
        if self.suggestions_list.page: self.suggestions_list.update()

    def _add_as_wake_word(self, word):
        current = self.voice.manager.get_wake_words()
        if word not in current:
            self.voice.manager.set_wake_words(", ".join(current + [word]))
            self.page.open(ft.SnackBar(ft.Text(f"¡Ahora '{word}' activará a Wizz!"), bgcolor=Theme.SUCCESS))
            self._sync_wake_word_ui()
            if word in self.voice.unknown_counts: del self.voice.unknown_counts[word]
            self._update_suggestions(self.voice.get_frequent_unknowns())

    def _prefill_command(self, word):
        self.cmd_phrase.value = word
        self.tabs.selected_index = 1 
        self.update()
        self.page.open(ft.SnackBar(ft.Text("Configura la acción para esta palabra"), bgcolor=Theme.PRIMARY))

    def _build_monitor_tab(self):
        self.status_icon = ft.Icon(ft.Icons.MIC_OFF, color="grey", size=24)
        self.status_text = ft.Text("Pausado", style=Theme.H2, size=16)
        self.dd_mics = ft.Dropdown(width=200, text_size=12, content_padding=10, bgcolor=Theme.BG_DARK, border_color="transparent", hint_text="Micrófono...", on_change=self._on_mic_change, border_radius=8)
        self.btn_toggle = ft.IconButton(icon=ft.Icons.PLAY_ARROW_ROUNDED, icon_color=Theme.SUCCESS, bgcolor=Theme.BG_DARK, tooltip="Iniciar/Pausar", on_click=lambda e: self.voice.toggle_listening())
        header = ft.Container(content=ft.Row([ft.Row([ft.Container(content=self.status_icon, padding=8, bgcolor=Theme.BG_CARD, border_radius=50), ft.Column([ft.Text("Estado", size=10, color="grey"), self.status_text], spacing=0)], spacing=10), ft.Row([self.dd_mics, self.btn_toggle], spacing=5)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=15, bgcolor=Theme.CARD_BG, border_radius=Theme.CARD_RADIUS, border=Theme.CARD_BORDER)
        self.switch_wake_word = ft.Switch(label="Wake Word", value=True, active_color=Theme.ACCENT, scale=0.8, on_change=self._on_wake_word_toggle)
        self.input_wake_word = ft.TextField(hint_text="Ej: wizz, jarvis", bgcolor=Theme.BG_DARK, border_color="transparent", height=30, text_size=12, content_padding=5, expand=True, on_submit=self._save_wake_word, on_blur=self._save_wake_word)
        config_bar = ft.Container(content=ft.Row([self.switch_wake_word, self.input_wake_word]), padding=10, bgcolor=Theme.BG_CARD, border_radius=10)
        self.log_list = ft.ListView(expand=True, spacing=8, padding=10, auto_scroll=True)
        btn_clear = ft.IconButton(ft.Icons.CLEANING_SERVICES, icon_size=16, icon_color="grey", tooltip="Limpiar", on_click=self._clear_log)
        log_panel = ft.Container(content=ft.Column([ft.Row([ft.Text("HISTORIAL EN VIVO", style=Theme.LABEL), btn_clear], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Divider(color="grey", opacity=0.1), self.log_list]), expand=True, bgcolor=Theme.CARD_BG, border_radius=Theme.CARD_RADIUS, padding=15, border=Theme.CARD_BORDER)
        return ft.Container(content=ft.Column([header, config_bar, log_panel], expand=True, spacing=15), padding=10, expand=True)

    def _load_microphones(self):
        try:
            devices = self.voice.get_input_devices()
            self.dd_mics.options = [ft.dropdown.Option(key=str(d['id']), text=d['name'][:25]) for d in devices]
            if not self.dd_mics.value and devices: self.dd_mics.value = str(devices[0]['id'])
            self.update()
        except: pass
    def _on_mic_change(self, e):
        if self.dd_mics.value:
            self.voice.change_device(int(self.dd_mics.value))
            self.page.open(ft.SnackBar(ft.Text("Micrófono cambiado"), bgcolor=Theme.SUCCESS))
    def _clear_log(self, e): self.log_list.controls.clear(); self.update()
    def _sync_wake_word_ui(self):
        ww = self.voice.manager.get_wake_words()
        self.switch_wake_word.value = bool(ww); self.input_wake_word.value = ", ".join(ww) if ww else ""; self.input_wake_word.visible = bool(ww); self.update()
    def _on_wake_word_toggle(self, e):
        if not self.switch_wake_word.value: self.voice.manager.set_wake_words("")
        else: self.input_wake_word.value = "computadora"; self._save_wake_word(None)
        self.input_wake_word.visible = self.switch_wake_word.value; self.update()
    def _save_wake_word(self, e): self.voice.manager.set_wake_words(self.input_wake_word.value); self._add_log_entry(f"🔧 Activadores: {self.input_wake_word.value}")
    def _add_log_entry(self, text):
        if not self.page: return
        self.log_list.controls.append(ft.Container(content=ft.Text(text, color="white", size=13), padding=10, bgcolor=Theme.BG_DARK, border_radius=10)); self.update()
    def _show_command_feedback(self, command, action):
        if not self.page: return
        self.log_list.controls.append(ft.Container(content=ft.Column([ft.Text(f"✅ {command}", color=Theme.SUCCESS, weight="bold"), ft.Text(action, size=11, color=Theme.TEXT_MUTED)]), padding=10, bgcolor=ft.Colors.with_opacity(0.1, Theme.SUCCESS), border=ft.border.all(1, Theme.SUCCESS), border_radius=10)); self.update()
    def _update_status_indicator(self, status):
        if not self.page: return
        if status == "listening": self.status_icon.color = Theme.SUCCESS; self.status_text.value = "Escuchando"; self.btn_toggle.icon = ft.Icons.PAUSE
        else: self.status_icon.color = "grey"; self.status_text.value = "Pausado"; self.btn_toggle.icon = ft.Icons.PLAY_ARROW_ROUNDED
        self.update()