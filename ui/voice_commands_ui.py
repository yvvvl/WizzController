"""
voice_commands_ui.py
Interfaz gráfica para crear, editar y eliminar comandos de voz personalizados en español.
"""

import customtkinter as ctk
import tkinter as tk
from core.voice_commands import VoiceCommandManager
from typing import Callable

class VoiceCommandsUI(ctk.CTkToplevel):
    """
    Ventana para gestionar comandos de voz personalizados.
    """
    def __init__(self, master: ctk.CTk, voice_manager: VoiceCommandManager = None) -> None:
        super().__init__(master)
        self.voice_manager = None
        self.title("Gestión de Comandos de Voz")
        self.geometry("500x400")
        self._build_ui()
        self._init_voice_manager(voice_manager)

    def _init_voice_manager(self, voice_manager):
        from core.voice_model_downloader import download_and_extract_model, get_model_path
        model_path = get_model_path()
        if voice_manager:
            self.voice_manager = voice_manager
            self.status_label.configure(text="Estado: Listo para escuchar")
        elif model_path and os.path.exists(model_path):
            self._try_create_voice_manager(model_path)
        else:
            self.status_label.configure(text="Estado: Descargando modelo de voz...")
            def on_download(path):
                if path and os.path.exists(path):
                    self._try_create_voice_manager(path)
                else:
                    self.after(0, lambda: self.status_label.configure(text="Error: modelo no descargado"))
            download_and_extract_model(callback=on_download)

    def _try_create_voice_manager(self, model_path):
        import time
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                self.voice_manager = self._create_voice_manager(model_path)
                self.status_label.configure(text="Estado: Listo para escuchar")
                return
            except Exception as e:
                self.status_label.configure(text=f"Intento {attempt}: Error cargando modelo, reintentando...")
                time.sleep(5)
        self.status_label.configure(text=f"Error cargando modelo tras {max_attempts} intentos")
        self._show_toast("Error: No se pudo cargar el modelo de voz")

    def _show_toast(self, message, duration=3500):
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.geometry(f"300x40+{self.winfo_x()+50}+{self.winfo_y()+50}")
        label = ctk.CTkLabel(toast, text=message, font=("Helvetica", 12), fg_color="#222", text_color="white")
        label.pack(expand=True, fill="both")
        toast.after(duration, toast.destroy)

    def _create_voice_manager(self, model_path):
        import os
        import logging
        if not model_path or not os.path.exists(model_path):
            logging.error(f"Ruta de modelo inválida: {model_path}")
            self._show_toast(f"Error: ruta de modelo inválida: {model_path}")
            raise RuntimeError(f"Ruta de modelo inválida: {model_path}")
        files = os.listdir(model_path)
        logging.info(f"Inicializando vosk.Model con ruta: {model_path}")
        logging.info(f"Archivos en modelo: {files}")
        expected_files = ["model.conf", "am"]
        if not any(f in files for f in expected_files):
            logging.error(f"Modelo no contiene archivos esperados: {expected_files}")
            self._show_toast(f"Error: modelo no contiene archivos esperados: {expected_files}")
            raise RuntimeError(f"Modelo no contiene archivos esperados: {expected_files}")
        from core.voice_commands import VoiceCommandManager
        return VoiceCommandManager(model_path)

    def _build_ui(self) -> None:
        self.command_listbox = tk.Listbox(self, font=("Arial", 12))
        self.command_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._refresh_commands()

        frame = ctk.CTkFrame(self)
        frame.pack(fill=tk.X, padx=10, pady=5)

        self.phrase_entry = ctk.CTkEntry(frame, placeholder_text="Frase en español")
        self.phrase_entry.pack(side=tk.LEFT, padx=5)

        self.action_entry = ctk.CTkEntry(frame, placeholder_text="Función (ej: turn_on)")
        self.action_entry.pack(side=tk.LEFT, padx=5)

        add_btn = ctk.CTkButton(frame, text="Añadir", command=self._add_command)
        add_btn.pack(side=tk.LEFT, padx=5)

        edit_btn = ctk.CTkButton(frame, text="Editar", command=self._edit_command)
        edit_btn.pack(side=tk.LEFT, padx=5)

        del_btn = ctk.CTkButton(frame, text="Eliminar", command=self._delete_command)
        del_btn.pack(side=tk.LEFT, padx=5)

        # Botón para activar reconocimiento de voz
        self.listen_btn = ctk.CTkButton(self, text="Escuchar comando de voz", command=self._listen_voice_command)
        self.listen_btn.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="Estado: Esperando", font=("Arial", 11))
        self.status_label.pack(pady=5)

    def _listen_voice_command(self) -> None:
        if not self.voice_manager:
            self.status_label.configure(text="Estado: Modelo no listo")
            return
        self.status_label.configure(text="Estado: Escuchando...")
        def on_finish():
            self.status_label.configure(text="Estado: Esperando")
        import threading
        def listen_and_update():
            self.voice_manager.listen_and_execute()
            self.after(0, on_finish)
        threading.Thread(target=listen_and_update, daemon=True).start()

    def _refresh_commands(self) -> None:
        self.command_listbox.delete(0, tk.END)
        for phrase in self.voice_manager.list_commands().keys():
            self.command_listbox.insert(tk.END, phrase)

    def _add_command(self) -> None:
        from core.actions import get_action
        phrase = self.phrase_entry.get().strip()
        action_name = self.action_entry.get().strip()
        if phrase and action_name:
            action_func = get_action(action_name)
            self.voice_manager.add_command(phrase, action_func)
            self._refresh_commands()

    def _edit_command(self) -> None:
        from core.actions import get_action
        selected = self.command_listbox.curselection()
        if selected:
            old_phrase = self.command_listbox.get(selected[0])
            new_phrase = self.phrase_entry.get().strip()
            action_name = self.action_entry.get().strip()
            if new_phrase and action_name:
                action_func = get_action(action_name)
                self.voice_manager.edit_command(old_phrase, new_phrase, action_func)
                self._refresh_commands()

    def _delete_command(self) -> None:
        selected = self.command_listbox.curselection()
        if selected:
            phrase = self.command_listbox.get(selected[0])
            self.voice_manager.remove_command(phrase)
            self._refresh_commands()
