import customtkinter as ctk
import tkinter as tk
import logging
import threading
import keyboard
from typing import Callable, Any
from config.hotkeys_manager import HotkeysManager
from core.actions import action_registry
from ui.color_picker import ColorPickerWidget
 # Las dependencias se pasan por argumento desde main_window.py

ACTION_LABELS = {
    "toggle_light": "Encender/Apagar (Automático)",
    "turn_on": "Encender",
    "turn_off": "Apagar",
    "brightness_increase": "Subir brillo (+10%)",
    "brightness_decrease": "Bajar brillo (-10%)",
    "brightness_max": "Brillo máximo",
    "brightness_min": "Brillo mínimo",
    "temp_warmer": "Más cálido (+200K)",
    "temp_cooler": "Más frío (-200K)",
    "set_color_red": "Color rojo",
    "set_color_blue": "Color azul",
    "set_color_custom": "Color personalizado",
    "set_color_green": "Color verde",
    "set_color_yellow": "Color amarillo",
    "set_color_white": "Color blanco",
    "set_scene_x": "Activar escena guardada",
    "search_bulbs": "Buscar ampolletas",
    "show_settings": "Abrir configuración",
    "show_hotkeys": "Configurar atajos de teclado",
}

class HotkeysSettings(ctk.CTkToplevel):
    """
    Ventana de configuración de hotkeys. Permite editar, limpiar y agregar atajos de teclado.
    """
    def __init__(self, master: ctk.CTk, hotkeys_manager: HotkeysManager, update_hotkeys: callable, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
        self.title("Configuración de Hotkeys")
        self.geometry("600x500")
        self.hotkeys_manager = hotkeys_manager
        self.update_hotkeys = update_hotkeys
        # Ya no depende de importaciones globales, todo se pasa por argumento
        self._build_ui()
        self.lift()
        self.focus_force()

    def _build_ui(self) -> None:
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.table_frame, text="Acción", font=("Helvetica", 12, "bold")).grid(row=0, column=0, padx=5)
        ctk.CTkLabel(self.table_frame, text="Atajo", font=("Helvetica", 12, "bold")).grid(row=0, column=1, padx=5)
        ctk.CTkLabel(self.table_frame, text="Editar", font=("Helvetica", 12, "bold")).grid(row=0, column=2, padx=5)
        ctk.CTkLabel(self.table_frame, text="Limpiar", font=("Helvetica", 12, "bold")).grid(row=0, column=3, padx=5)
        ctk.CTkLabel(self.table_frame, text="Eliminar", font=("Helvetica", 12, "bold")).grid(row=0, column=4, padx=5)

        self.rows = []
        for idx, action_id in enumerate(action_registry.keys()):
            action_name = ACTION_LABELS.get(action_id, action_id.replace('_', ' ').capitalize())
            hotkey = self.hotkeys_manager.get_hotkeys()
            key_combo = next((k for k, v in hotkey.items() if isinstance(v, dict) and v.get('action') == action_id), "Ninguno")
            lbl_action = ctk.CTkLabel(self.table_frame, text=action_name)
            lbl_action.grid(row=idx+1, column=0, padx=5, pady=2)
            lbl_hotkey = ctk.CTkLabel(self.table_frame, text=key_combo)
            lbl_hotkey.grid(row=idx+1, column=1, padx=5, pady=2)
            btn_edit = ctk.CTkButton(self.table_frame, text="Editar", command=lambda aid=action_id, row=idx+1: self._edit_hotkey(aid, row))
            btn_edit.grid(row=idx+1, column=2, padx=5, pady=2)
            btn_clear = ctk.CTkButton(self.table_frame, text="Limpiar", command=lambda aid=action_id: self._clear_hotkey(aid))
            btn_clear.grid(row=idx+1, column=3, padx=5, pady=2)
            btn_delete = ctk.CTkButton(self.table_frame, text="Eliminar", command=lambda aid=action_id: self._delete_action(aid))
            btn_delete.grid(row=idx+1, column=4, padx=5, pady=2)
            self.rows.append((lbl_action, lbl_hotkey, btn_edit, btn_clear, btn_delete))

        # Agregar nueva hotkey con lista seleccionable de acciones
        self.add_frame = ctk.CTkFrame(self)
        self.add_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(self.add_frame, text="Agregar nueva hotkey:").pack(side="left", padx=5)
        self.action_var = tk.StringVar()
        self.action_menu = ctk.CTkOptionMenu(self.add_frame, variable=self.action_var, values=[ACTION_LABELS.get(a, a.replace('_', ' ').capitalize()) for a in action_registry.keys()])
        self.action_menu.pack(side="left", padx=5)
        self.new_hotkey_entry = ctk.CTkEntry(self.add_frame, placeholder_text="Combinación (ej: ctrl+g)")
        self.new_hotkey_entry.pack(side="left", padx=5)
        self.add_btn = ctk.CTkButton(self.add_frame, text="Agregar", command=self._add_hotkey)
        self.add_btn.pack(side="left", padx=5)

    def _add_hotkey(self) -> None:
        action_label = self.action_var.get().strip()
        key_combo = self.new_hotkey_entry.get().strip()
        action_id = next((aid for aid, label in ACTION_LABELS.items() if label == action_label), None)
        if action_id and key_combo:
            if key_combo in self.hotkeys_manager.get_hotkeys():
                ctk.CTkLabel(self, text="Atajo duplicado!", text_color="red").pack()
                return
            # Si es acción de color personalizado, mostrar color picker
            if action_id in ["set_color_custom", "set_color_red", "set_color_blue", "set_color_green", "set_color_yellow", "set_color_white"]:
                def on_color(rgb):
                    self.hotkeys_manager.set_hotkey(key_combo, action_id)
                    self.hotkeys_manager.set_hotkey("color_value", rgb)
                    self.destroy()
                    HotkeysSettings(self.master, self.hotkeys_manager, self.update_hotkeys)
                picker = ColorPickerWidget(self, on_color_change=on_color)
                picker.pack(pady=10)
            else:
                self.hotkeys_manager.set_hotkey(key_combo, action_id)
                self.destroy()
                HotkeysSettings(self.master, self.hotkeys_manager, self.update_hotkeys)

    def _edit_hotkey(self, action_id: str, row: int) -> None:
        modal = ctk.CTkToplevel(self)
        modal.title("Grabar atajo")
        modal.geometry("340x220")
        modal.lift()
        modal.focus_force()
        ctk.CTkLabel(modal, text="Presiona tu combinación y haz clic en 'Aceptar'", font=("Helvetica", 12)).pack(pady=10)
        key_var = tk.StringVar()
        entry = ctk.CTkEntry(modal, textvariable=key_var)
        entry.pack(pady=5)
        entry.focus_set()
        combo_captured = {'value': None}
        feedback_label = ctk.CTkLabel(modal, text="", text_color="red")
        feedback_label.pack(pady=2)
        ctk.CTkLabel(modal, text="Ejemplo: ctrl+shift+L", font=("Helvetica", 10, "italic"), text_color="#aaa").pack()
        color_value = [255, 255, 255]  # Valor por defecto
        color_picker_widget = None

        def listen_keys():
            import keyboard
            try:
                # Captura solo la última combinación pulsada, limpia el estado
                combo = keyboard.read_hotkey(suppress=False)
                combo_captured['value'] = combo
                self.after(0, lambda: key_var.set(combo))
            except Exception as exc:
                def show_error(err=exc):
                    feedback_label.configure(text=f"Error: {err}")
                self.after(0, show_error)
        threading.Thread(target=listen_keys, daemon=True).start()

        def is_modifier_only(combo: str) -> bool:
            mods = {"ctrl", "alt", "shift", "windows"}
            keys = set(combo.replace("+", " ").split())
            return keys.issubset(mods)

        def on_color_change(rgb):
            nonlocal color_value
            color_value = rgb

        if action_id == "set_color_custom":
            ctk.CTkLabel(modal, text="Selecciona el color para este atajo:").pack(pady=5)
            color_picker_widget = ColorPickerWidget(modal, on_color_change=on_color_change)
            color_picker_widget.pack(pady=5)

        def accept_hotkey():
            combo = key_var.get().strip()
            if not combo:
                feedback_label.configure(text="No se capturó ninguna combinación")
                return
            if is_modifier_only(combo):
                feedback_label.configure(text="No puedes usar solo modificadores")
                return
            if combo in self.hotkeys_manager.get_hotkeys():
                confirm = tk.messagebox.askyesno("Duplicado", f"El atajo '{combo}' ya está en uso. ¿Deseas reemplazarlo?")
                if not confirm:
                    return
            try:
                if action_id == "set_color_custom":
                    self.hotkeys_manager.set_hotkey(combo, action_id, color=color_value)
                else:
                    self.hotkeys_manager.set_hotkey(combo, action_id)
                self.update_hotkeys()
                modal.destroy()
                tk.messagebox.showinfo("Hotkey", f"Hotkey '{combo}' asignado correctamente.")
            except Exception as e:
                logging.error(f"Error registrando hotkey: {e}")
                feedback_label.configure(text=f"Error: {e}")
        btn_accept = ctk.CTkButton(modal, text="Aceptar", command=accept_hotkey)
        btn_accept.pack(pady=5)
        btn_cancel = ctk.CTkButton(modal, text="Cancelar", command=modal.destroy)
        btn_cancel.pack(pady=2)

        # Si es acción de color personalizado, mostrar color picker
        if action_id in ["set_color_custom", "set_color_red", "set_color_blue", "set_color_green", "set_color_yellow", "set_color_white"]:
            def on_color(rgb):
                combo = key_var.get().strip()
                if combo:
                    self.hotkeys_manager.set_hotkey(combo, action_id)
                    self.hotkeys_manager.set_hotkey("color_value", rgb)
                    modal.destroy()
                    self.destroy()
                    HotkeysSettings(self.master, self.hotkeys_manager, self.update_hotkeys)
            picker = ColorPickerWidget(modal, on_color_change=on_color)
            picker.pack(pady=10)

    def _clear_hotkey(self, action_id: str) -> None:
        hotkeys = self.hotkeys_manager.get_hotkeys()
        for k, v in list(hotkeys.items()):
            if isinstance(v, dict) and v.get('action') == action_id:
                self.hotkeys_manager.remove_hotkey(k)
                self.update_hotkeys()
                self.destroy()
                break

    def _delete_action(self, action_id: str) -> None:
        # Elimina la acción del registro y su hotkey
        hotkeys = self.hotkeys_manager.get_hotkeys()
        for k, v in list(hotkeys.items()):
            if v == action_id:
                self.hotkeys_manager.remove_hotkey(k)
        if action_id in action_registry:
            del action_registry[action_id]
        self.destroy()
