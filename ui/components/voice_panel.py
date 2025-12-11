import flet as ft

class VoicePanel(ft.Container):
    def __init__(self, manager, voice_service):
        super().__init__(padding=20, expand=True)
        self.voice_service = voice_service 
        # Aseguramos compatibilidad si pasan el servicio o el manager directo
        self.manager = manager if manager else voice_service.manager
        
        self.c_accent = "#38bdf8" # Azul cielo tipo Wizz
        self.c_bg_card = "#1f2937"
        
        # Lista scrolleable de logs
        self.log_list = ft.ListView(expand=True, spacing=5, auto_scroll=True)
        
        # Lista scrolleable de comandos
        self.commands_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10)
        
        # Botón flotante para agregar
        self.fab = ft.FloatingActionButton(
            icon=ft.Icons.ADD, 
            bgcolor=self.c_accent, 
            content=ft.Icon(ft.Icons.ADD, color="white"),
            on_click=lambda e: self._open_edit_dialog(is_new=True),
            tooltip="Crear nuevo comando"
        )

        # Estructura Principal
        self.content = ft.Column([
            self._build_header(),
            ft.Divider(color="transparent", height=10),
            ft.Row([
                # Columna Izquierda: Logs (Monitor)
                self._build_panel("MONITOR DE VOZ", self.log_list, expand_flex=2),
                
                # Columna Derecha: Gestión de Comandos
                self._build_panel("MIS COMANDOS", 
                                  ft.Container(content=self.commands_column, expand=True), 
                                  expand_flex=3, 
                                  extra_action=self.fab)
            ], expand=True, spacing=20)
        ])
        
        self._render_commands()

    def _build_header(self):
        # Obtenemos las palabras clave actuales
        wakes = self.manager.get_wake_words()
        wakes_str = ", ".join(wakes).upper() if wakes else "SIN ACTIVADOR"
        
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.KEYBOARD_VOICE, color=self.c_accent, size=30),
                    padding=10, bgcolor="#112244", border_radius=10
                ),
                ft.Column([
                    ft.Text("Configuración de Voz", size=20, weight="bold", color="white"),
                    ft.Text(f"Di '{wakes_str}' antes de tu comando", size=12, color="grey")
                ], spacing=2),
                ft.Container(expand=True),
                ft.OutlinedButton(
                    "Editar Activador", 
                    icon=ft.Icons.EDIT,
                    style=ft.ButtonStyle(color="white", side=ft.BorderSide(1, "grey")),
                    on_click=lambda e: self._open_config_wake()
                )
            ]), 
            padding=ft.padding.only(bottom=10)
        )

    def _build_panel(self, title, content, expand_flex=1, extra_action=None):
        header_controls = [ft.Text(title, size=12, weight="bold", color=self.c_accent)]
        if extra_action:
            # Si hay un botón flotante (FAB), lo ponemos en una esquina relativa o lo integramos visualmente
            pass 

        return ft.Container(
            content=ft.Column([
                ft.Row(header_controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color="#374151", height=10),
                content,
                # Si hay acción extra (como el FAB), lo ponemos abajo a la derecha
                ft.Row([ft.Container(expand=True), extra_action]) if extra_action else ft.Container()
            ]),
            bgcolor=self.c_bg_card, 
            padding=20, 
            border_radius=15, 
            expand=expand_flex,
            border=ft.border.all(1, "#374151")
        )

    def _render_commands(self):
        self.commands_column.controls.clear()
        commands = self.manager.get_commands()
        
        if not commands:
            self.commands_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.VOICE_OVER_OFF, size=40, color="grey"),
                        ft.Text("No hay comandos creados", color="grey")
                    ], horizontal_alignment="center"),
                    alignment=ft.alignment.center,
                    padding=40
                )
            )
        else:
            for cmd in commands:
                self.commands_column.controls.append(self._build_command_card(cmd))
        
        if self.page: self.update()

    def _build_command_card(self, cmd):
        phrases = cmd.get("phrases", "")
        # Mostramos solo las primeras 2 frases para no saturar
        preview_phrases = phrases.split(",")[:2]
        more_count = len(phrases.split(",")) - 2
        
        chips = [
            ft.Container(
                content=ft.Text(p.strip(), size=10, color="black", weight="bold"),
                bgcolor="#7dd3fc", padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=15
            ) for p in preview_phrases if p.strip()
        ]
        if more_count > 0:
            chips.append(ft.Text(f"+{more_count} más...", size=10, color="grey"))

        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.BOLT, color="#fbbf24"), # Icono rayo amarillo
                ft.Column([
                    ft.Text(cmd.get("desc", "Sin Nombre"), weight="bold", color="white", size=14),
                    ft.Row(chips, wrap=True, spacing=5)
                ], expand=True, spacing=2),
                
                ft.IconButton(ft.Icons.EDIT, icon_color="white", tooltip="Editar", 
                            on_click=lambda e: self._open_edit_dialog(False, cmd)),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="#ef4444", tooltip="Eliminar", 
                            on_click=lambda e: self._delete_cmd(cmd.get("id")))
            ]),
            bgcolor="#111827", padding=15, border_radius=10,
            border=ft.border.all(1, "#374151")
        )

    # --- DIÁLOGOS DE EDICIÓN ---

    def _open_config_wake(self):
        # Obtener valor actual como string para editar
        current = ", ".join(self.manager.get_wake_words())
        tf = ft.TextField(
            label="Palabra de Activación", 
            value=current,
            helper_text="Separa con comas si quieres varias (Ej: wizz, computadora)",
            color="white", bgcolor="#111827", border_color="#374151"
        )
        
        def save(e):
            self.manager.set_wake_words(tf.value)
            # Actualizar header
            self.content.controls[0] = self._build_header()
            self.update()
            self.page.close(dlg)
        
        dlg = ft.AlertDialog(
            title=ft.Text("Configurar Activador", color="white"), 
            bgcolor="#1f2937",
            content=tf, 
            actions=[ft.TextButton("Cancelar", on_click=lambda e: self.page.close(dlg)),
                     ft.ElevatedButton("Guardar", bgcolor=self.c_accent, color="black", on_click=save)]
        )
        self.page.open(dlg)

    def _open_edit_dialog(self, is_new=False, data=None):
        d = data or {}
        
        # Campos
        tf_desc = ft.TextField(
            label="Nombre del Comando", 
            value=d.get("desc", ""), 
            hint_text="Ej: Modo Cine",
            color="white", bgcolor="#111827", border_color="#374151"
        )
        
        tf_phrases = ft.TextField(
            label="Frases de Activación", 
            value=d.get("phrases", ""), 
            multiline=True, min_lines=2, max_lines=4,
            hint_text="Ej: activar cine, poner modo película, vamos al cine",
            helper_text="Escribe todas las formas de decirlo, separadas por coma.",
            color="white", bgcolor="#111827", border_color="#374151"
        )
        
        # Opciones de Acciones Inteligentes
        actions_options = [
            ft.dropdown.Option("turn_on", "Encender Luces"),
            ft.dropdown.Option("turn_off", "Apagar Luces"),
            ft.dropdown.Option("toggle", "Alternar (Toggle)"),
            ft.dropdown.Option("brightness_up", "Subir Brillo (+25%)"),
            ft.dropdown.Option("brightness_down", "Bajar Brillo (-25%)"),
            ft.dropdown.Option("set_scene_cinema", "Escena: Cine"),  # Ejemplos, puedes agregar más
            ft.dropdown.Option("set_scene_relax", "Escena: Relax"),
            ft.dropdown.Option("set_white_warm", "Luz Cálida"),
            ft.dropdown.Option("set_white_cold", "Luz Fría"),
        ]
        
        dd_action = ft.Dropdown(
            label="Acción a Ejecutar",
            value=d.get("action"),
            options=actions_options,
            color="white", bgcolor="#111827", border_color="#374151",
            border_radius=10
        )
        
        def save(e):
            if not tf_desc.value or not tf_phrases.value or not dd_action.value:
                # Validación básica visual
                tf_desc.error_text = "Requerido" if not tf_desc.value else None
                tf_phrases.error_text = "Requerido" if not tf_phrases.value else None
                dd_action.error_text = "Selecciona una acción" if not dd_action.value else None
                tf_desc.update()
                tf_phrases.update()
                dd_action.update()
                return

            if is_new:
                self.manager.add_command(tf_phrases.value, dd_action.value, tf_desc.value)
            else:
                self.manager.update_command(d.get("id"), tf_phrases.value, dd_action.value, tf_desc.value)
            
            self._render_commands()
            self.page.close(dlg)
            
        dlg = ft.AlertDialog(
            title=ft.Text("Nuevo Comando" if is_new else "Editar Comando", color="white", weight="bold"), 
            bgcolor="#1f2937",
            content=ft.Column([
                tf_desc, 
                ft.Container(height=10),
                dd_action,
                ft.Container(height=10),
                tf_phrases
            ], tight=True, width=400), 
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.close(dlg)),
                ft.ElevatedButton("Guardar Cambios", bgcolor=self.c_accent, color="black", on_click=save)
            ]
        )
        self.page.open(dlg)

    def _delete_cmd(self, uid):
        if uid:
            self.manager.remove_command(uid)
            self._render_commands()
        
    def add_voice_log(self, text):
        # Agregamos al principio para que lo nuevo salga arriba si quisieramos, 
        # pero ListView autoscroll prefiere al final.
        self.log_list.controls.append(
            ft.Text(f"» {text}", color="white", size=14, font_family="Consolas")
        )
        if self.page: self.update()