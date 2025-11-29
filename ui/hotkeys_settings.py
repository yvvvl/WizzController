import customtkinter as ctk
import tkinter as tk # Solo para constantes
from config.hotkeys_manager import HotkeysManager
from core.actions import get_all_actions
from ui.color_picker import ColorPickerWidget

class EditDialog(ctk.CTkToplevel):
    """Ventana modal moderna para editar combinaciones."""
    def __init__(self, master, title, current_value, on_confirm):
        super().__init__(master)
        self.title(title)
        self.geometry("350x180")
        self.resizable(False, False)
        self.on_confirm = on_confirm
        
        # Centrar en pantalla
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - 175
        y = master.winfo_y() + (master.winfo_height() // 2) - 90
        self.geometry(f"+{x}+{y}")
        self.lift()
        self.focus_force()

        ctk.CTkLabel(self, text="Nueva combinación de teclas:", font=("Arial", 14)).pack(pady=(20, 10))
        
        self.entry = ctk.CTkEntry(self, width=200, justify="center")
        self.entry.insert(0, current_value)
        self.entry.pack(pady=10)
        self.entry.focus_set()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="transparent", border_width=1, width=100, command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Guardar", width=100, command=self._confirm).pack(side="left", padx=10)

    def _confirm(self):
        val = self.entry.get().strip()
        if val:
            self.on_confirm(val)
            self.destroy()

class HotkeysSettings(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk, hotkeys_manager: HotkeysManager, update_hotkeys: callable, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
        self.title("Configuración de Hotkeys")
        self.geometry("800x600")
        self.hotkeys_manager = hotkeys_manager
        self.update_hotkeys = update_hotkeys
        self.available_actions = get_all_actions()
        self._build_ui()
        self.lift()
        self.focus_force()

    def _build_ui(self) -> None:
        # --- LISTA ---
        self.table_frame = ctk.CTkScrollableFrame(self, label_text="Tus Atajos")
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=20)

        current_hotkeys = self.hotkeys_manager.get_hotkeys()
        
        if not current_hotkeys:
            ctk.CTkLabel(self.table_frame, text="No hay atajos configurados.", text_color="gray").pack(pady=20)

        for combo, data in current_hotkeys.items():
            self._create_row(combo, data)

        # --- AGREGAR ---
        self.add_frame = ctk.CTkFrame(self)
        self.add_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(self.add_frame, text="Nuevo Atajo:", font=("Arial", 12, "bold")).pack(side="left", padx=15)
        
        self.action_var = ctk.StringVar(value=list(self.available_actions.values())[0])
        self.action_menu = ctk.CTkOptionMenu(
            self.add_frame, 
            variable=self.action_var, 
            values=list(self.available_actions.values()),
            width=250
        )
        self.action_menu.pack(side="left", padx=10)

        self.new_hotkey_entry = ctk.CTkEntry(self.add_frame, placeholder_text="Ej: ctrl+alt+p", width=150)
        self.new_hotkey_entry.pack(side="left", padx=10)
        
        ctk.CTkButton(self.add_frame, text="+ Agregar", width=100, command=self._add_hotkey_flow).pack(side="left", padx=10)

    def _create_row(self, combo, data):
        """Crea una fila visual para un atajo."""
        row_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)

        action_id = data.get("action")
        is_enabled = data.get("enabled", True)
        color_data = data.get("color")
        
        # Nombre de la acción
        action_name = self.available_actions.get(action_id, action_id)
        if action_id == "set_color_custom" and color_data:
            # Mostramos un cuadradito de color
            hex_col = f"#{color_data[0]:02x}{color_data[1]:02x}{color_data[2]:02x}"
            color_indicator = ctk.CTkLabel(row_frame, text="  ", fg_color=hex_col, width=20, height=20, corner_radius=5)
            color_indicator.pack(side="left", padx=(10, 5))
            ctk.CTkLabel(row_frame, text="Color Personalizado", width=200, anchor="w").pack(side="left")
        else:
            ctk.CTkLabel(row_frame, text=action_name, width=230, anchor="w").pack(side="left", padx=10)

        # Combinación de teclas
        ctk.CTkLabel(row_frame, text=combo, width=150, anchor="center", text_color="#3daee9", font=("Consolas", 12, "bold")).pack(side="left", padx=10)

        # Controles
        controls_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        controls_frame.pack(side="right", padx=10)

        # 1. Switch Habilitar/Deshabilitar
        switch = ctk.CTkSwitch(
            controls_frame, 
            text="", 
            width=40,
            command=lambda c=combo, v=is_enabled: self._toggle_hotkey(c)
        )
        if is_enabled: switch.select()
        else: switch.deselect()
        switch.pack(side="left", padx=10)

        # 2. Editar (Lápiz)
        ctk.CTkButton(
            controls_frame, 
            text="✎", 
            width=40, 
            fg_color="#444", 
            command=lambda c=combo, aid=action_id: self._open_edit_modal(aid, c)
        ).pack(side="left", padx=5)

        # 3. Eliminar (Sin confirmación, directo)
        ctk.CTkButton(
            controls_frame, 
            text="🗑", 
            width=40, 
            fg_color="#c0392b", 
            hover_color="#e74c3c",
            command=lambda c=combo: self._delete_hotkey(c)
        ).pack(side="left", padx=5)

    def _add_hotkey_flow(self):
        label_selected = self.action_var.get()
        key_combo = self.new_hotkey_entry.get().strip().lower()
        
        if not key_combo: return

        action_id = next((k for k, v in self.available_actions.items() if v == label_selected), None)
        if not action_id: return

        if action_id == "set_color_custom":
            self._open_color_picker_modal(key_combo)
        else:
            self.hotkeys_manager.set_hotkey(key_combo, action_id)
            self._reload_ui()

    def _toggle_hotkey(self, combo):
        """Cambia el estado enabled/disabled y actualiza bindings."""
        current = self.hotkeys_manager.get_hotkeys().get(combo, {})
        new_state = not current.get("enabled", True)
        self.hotkeys_manager.set_enabled(combo, new_state)
        self.update_hotkeys() # Actualiza keyboard hooks inmediatamente
        # No recargamos toda la UI para que el switch no parpadee, 
        # pero idealmente el estado visual ya cambió al hacer click.

    def _open_edit_modal(self, action_id, current_combo):
        """Abre nuestro modal personalizado bonito."""
        def on_save(new_combo):
            current_data = self.hotkeys_manager.get_hotkeys().get(current_combo)
            color = current_data.get("color") if current_data else None
            
            self.hotkeys_manager.remove_hotkey(current_combo)
            self.hotkeys_manager.set_hotkey(new_combo.lower(), action_id, color=color)
            self._reload_ui()

        EditDialog(self, "Editar Atajo", current_combo, on_save)

    def _delete_hotkey(self, combo):
        # Eliminación directa sin preguntas
        self.hotkeys_manager.remove_hotkey(combo)
        self._reload_ui()

    def _reload_ui(self):
        self.update_hotkeys()
        self.destroy()
        HotkeysSettings(self.master, self.hotkeys_manager, self.update_hotkeys)

    def _open_color_picker_modal(self, key_combo):
        modal = ctk.CTkToplevel(self)
        modal.title("Color para atajo")
        modal.geometry("400x320")
        modal.lift()
        modal.focus_force()
        
        def on_color_picked(rgb):
            self.hotkeys_manager.set_hotkey(key_combo, "set_color_custom", color=rgb)
            modal.destroy()
            self._reload_ui()
            
        picker = ColorPickerWidget(modal, on_color_change=None)
        picker.pack(pady=20)
        picker.done_btn.configure(command=lambda: on_color_picked(tuple(int(picker.selected_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))))