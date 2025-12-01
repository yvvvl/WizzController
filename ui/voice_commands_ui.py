import os
import logging
import threading
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

class VoiceWorker(QObject):
    """Worker para manejar la señalización desde el thread"""
    finished = pyqtSignal()
    status_update = pyqtSignal(str)

class VoiceCommandsUI(QDialog):
    def __init__(self, parent, voice_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Comandos de Voz")
        self.resize(600, 450)
        
        self.voice_manager = None
        self.worker = VoiceWorker()
        self.worker.status_update.connect(self._update_status)
        self.worker.finished.connect(self._on_listen_finished)

        self._build_ui()
        
        # Inicialización diferida para no bloquear UI
        self._init_voice_manager(voice_manager)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Lista de comandos
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.list_widget)
        
        # Inputs
        input_layout = QHBoxLayout()
        self.entry_phrase = QLineEdit()
        self.entry_phrase.setPlaceholderText("Frase en español")
        
        self.entry_action = QLineEdit()
        self.entry_action.setPlaceholderText("ID Función (ej: turn_on)")
        
        input_layout.addWidget(self.entry_phrase)
        input_layout.addWidget(self.entry_action)
        layout.addLayout(input_layout)
        
        # Botones CRUD
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Añadir")
        btn_add.clicked.connect(self._add_command)
        
        btn_edit = QPushButton("Editar Seleccionado")
        btn_edit.clicked.connect(self._edit_command)
        
        btn_del = QPushButton("Eliminar")
        btn_del.clicked.connect(self._delete_command)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_del)
        layout.addLayout(btn_layout)
        
        layout.addSpacing(20)
        
        # Botón Escuchar
        self.btn_listen = QPushButton("🎤 Escuchar comando de voz")
        self.btn_listen.setFixedHeight(40)
        self.btn_listen.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_listen.clicked.connect(self._listen_voice_command)
        layout.addWidget(self.btn_listen)
        
        self.lbl_status = QLabel("Estado: Esperando")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

    def _init_voice_manager(self, voice_manager):
        # Lógica igual a la original, pero adaptada a no bloquear
        from core.voice_model_downloader import download_and_extract_model, get_model_path
        
        if voice_manager:
            self.voice_manager = voice_manager
            self._update_status("Estado: Listo para escuchar")
            self._refresh_commands()
            return

        model_path = get_model_path()
        if model_path and os.path.exists(model_path):
            self._try_load_model(model_path)
        else:
            self._update_status("Descargando modelo de voz...")
            # En un caso real, esto también debería ir en un thread aparte
            threading.Thread(target=lambda: download_and_extract_model(callback=self._on_download_complete), daemon=True).start()

    def _on_download_complete(self, path):
        if path and os.path.exists(path):
            self._try_load_model(path)
        else:
            self.worker.status_update.emit("Error: Modelo no descargado")

    def _try_load_model(self, model_path):
        # Ejecutar carga pesada en thread
        threading.Thread(target=self._load_model_thread, args=(model_path,), daemon=True).start()

    def _load_model_thread(self, model_path):
        try:
            from core.voice_commands import VoiceCommandManager
            # Crear manager
            self.voice_manager = VoiceCommandManager(model_path)
            
            # Guardar referencia en main window (hacky pero compatible con tu lógica anterior)
            if self.parent():
                self.parent()._voice_manager = self.voice_manager
                
            self.worker.status_update.emit("Estado: Listo para escuchar")
            # Refrescar lista en hilo principal no se puede directo,
            # pero como es solo lectura de datos, lo haremos al terminar o mediante señal
            # Simplificación: El usuario verá la lista vacía hasta interactuar o reabrir, 
            # idealmente usaríamos otra señal para 'data_ready'.
        except Exception as e:
            logging.error(f"Error cargando voz: {e}")
            self.worker.status_update.emit("Error cargando modelo")

    def _update_status(self, text):
        self.lbl_status.setText(text)
        if "Listo" in text and self.voice_manager:
            self._refresh_commands()

    def _refresh_commands(self):
        if not self.voice_manager: return
        self.list_widget.clear()
        for phrase in self.voice_manager.list_commands().keys():
            self.list_widget.addItem(phrase)

    def _add_command(self):
        if not self.voice_manager: return
        phrase = self.entry_phrase.text().strip()
        action = self.entry_action.text().strip()
        
        if phrase and action:
            # Obtener wrapper
            func = self._get_wrapped_action(action)
            self.voice_manager.add_command(phrase, func)
            self._refresh_commands()
            self.entry_phrase.clear()
            self.entry_action.clear()

    def _edit_command(self):
        item = self.list_widget.currentItem()
        if not item or not self.voice_manager: return
        
        old_phrase = item.text()
        new_phrase = self.entry_phrase.text().strip()
        action = self.entry_action.text().strip()
        
        if new_phrase and action:
            func = self._get_wrapped_action(action)
            self.voice_manager.edit_command(old_phrase, new_phrase, func)
            self._refresh_commands()

    def _delete_command(self):
        item = self.list_widget.currentItem()
        if not item or not self.voice_manager: return
        
        self.voice_manager.remove_command(item.text())
        self._refresh_commands()

    def _listen_voice_command(self):
        if not self.voice_manager: return
        
        self.btn_listen.setEnabled(False)
        self._update_status("Escuchando... Hable ahora")
        
        # Ejecutar escucha en background para no congelar GUI
        threading.Thread(target=self._listen_thread, daemon=True).start()

    def _listen_thread(self):
        if self.voice_manager:
            self.voice_manager.listen_and_execute()
        self.worker.finished.emit()

    def _on_listen_finished(self):
        self.btn_listen.setEnabled(True)
        self._update_status("Estado: Listo (Último comando procesado)")

    def _get_wrapped_action(self, action_id):
        from core.actions import get_action_func
        raw_action = get_action_func(action_id)
        
        def wrapped():
            # Intentamos acceder al light_manager del padre
            main_win = self.parent()
            if hasattr(main_win, 'light_manager'):
                try:
                    raw_action(main_win.light_manager)
                except:
                    pass
        return wrapped