from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QComboBox, QScrollArea, 
                             QCheckBox, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette

from config.hotkeys_manager import HotkeysManager
from core.actions import get_all_actions
# Asumimos que migraremos el selector de color pequeño después, 
# o usamos el nativo QColorDialog si prefieres simplificar.
from PyQt6.QtWidgets import QColorDialog 

class EditDialog(QDialog):
    """Diálogo modal para editar una combinación"""
    def __init__(self, parent, title, current_value):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(350, 150)
        self.result_value = None

        layout = QVBoxLayout(self)
        
        lbl = QLabel("Nueva combinación de teclas:")
        layout.addWidget(lbl)
        
        self.entry = QLineEdit()
        self.entry.setText(current_value)
        self.entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.entry)
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self._confirm)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _confirm(self):
        val = self.entry.text().strip()
        if val:
            self.result_value = val
            self.accept()

class HotkeysSettings(QDialog):
    def __init__(self, parent, hotkeys_manager: HotkeysManager, update_hotkeys_callback):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Hotkeys")
        self.resize(800, 600)
        
        self.hotkeys_manager = hotkeys_manager
        self.update_hotkeys = update_hotkeys_callback
        self.available_actions = get_all_actions()
        
        # Layout Principal
        self.main_layout = QVBoxLayout(self)
        
        # 1. Área de Scroll (La lista)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        # 2. Área de Agregar (Abajo)
        self.add_frame = QFrame()
        self.add_frame.setStyleSheet("background-color: #333; border-radius: 5px;")
        add_layout = QHBoxLayout(self.add_frame)
        
        add_layout.addWidget(QLabel("Nuevo Atajo:"))
        
        self.combo_actions = QComboBox()
        # Llenar con nombres legibles
        self.action_map = {v: k for k, v in self.available_actions.items()} # Nombre -> ID
        self.combo_actions.addItems(list(self.available_actions.values()))
        add_layout.addWidget(self.combo_actions, 1) # Stretch
        
        self.entry_new_key = QLineEdit()
        self.entry_new_key.setPlaceholderText("Ej: ctrl+alt+p")
        add_layout.addWidget(self.entry_new_key)
        
        btn_add = QPushButton("+ Agregar")
        btn_add.clicked.connect(self._add_hotkey_flow)
        add_layout.addWidget(btn_add)
        
        self.main_layout.addWidget(self.add_frame)

        self._refresh_list()

    def _refresh_list(self):
        # Limpiar lista anterior
        for i in reversed(range(self.scroll_layout.count())): 
            self.scroll_layout.itemAt(i).widget().setParent(None)

        current_hotkeys = self.hotkeys_manager.get_hotkeys()
        
        if not current_hotkeys:
            self.scroll_layout.addWidget(QLabel("No hay atajos configurados.", alignment=Qt.AlignmentFlag.AlignCenter))
            return

        for combo, data in current_hotkeys.items():
            self._create_row(combo, data)

    def _create_row(self, combo, data):
        row_frame = QFrame()
        row_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 5px; margin-bottom: 2px;")
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(10, 5, 10, 5)

        action_id = data.get("action")
        is_enabled = data.get("enabled", True)
        color_data = data.get("color")
        
        # Nombre acción
        action_name = self.available_actions.get(action_id, action_id)
        
        if action_id == "set_color_custom" and color_data:
            # Indicador de color
            lbl_color = QLabel()
            lbl_color.setFixedSize(20, 20)
            hex_col = f"#{color_data[0]:02x}{color_data[1]:02x}{color_data[2]:02x}"
            lbl_color.setStyleSheet(f"background-color: {hex_col}; border-radius: 3px;")
            row_layout.addWidget(lbl_color)
            row_layout.addWidget(QLabel("Color Personalizado"))
        else:
            row_layout.addWidget(QLabel(str(action_name)))

        row_layout.addStretch()

        # Teclas
        lbl_combo = QLabel(combo)
        lbl_combo.setStyleSheet("color: #3daee9; font-weight: bold; font-family: Consolas;")
        row_layout.addWidget(lbl_combo)

        row_layout.addSpacing(20)

        # Checkbox Habilitar
        chk_enable = QCheckBox("Activo")
        chk_enable.setChecked(is_enabled)
        chk_enable.toggled.connect(lambda state, c=combo: self._toggle_hotkey(c, state))
        row_layout.addWidget(chk_enable)

        # Botón Editar
        btn_edit = QPushButton("✎")
        btn_edit.setFixedSize(30, 30)
        btn_edit.clicked.connect(lambda _, c=combo, aid=action_id: self._open_edit_modal(aid, c))
        row_layout.addWidget(btn_edit)

        # Botón Borrar
        btn_del = QPushButton("🗑")
        btn_del.setFixedSize(30, 30)
        btn_del.setStyleSheet("background-color: #c0392b; border: none;")
        btn_del.clicked.connect(lambda _, c=combo: self._delete_hotkey(c))
        row_layout.addWidget(btn_del)

        self.scroll_layout.addWidget(row_frame)

    def _add_hotkey_flow(self):
        label_selected = self.combo_actions.currentText()
        key_combo = self.entry_new_key.text().strip().lower()
        
        if not key_combo: return

        action_id = self.action_map.get(label_selected)
        if not action_id: return

        if action_id == "set_color_custom":
            self._open_color_picker_modal(key_combo)
        else:
            self.hotkeys_manager.set_hotkey(key_combo, action_id)
            self._refresh_list()
            self.update_hotkeys() # Actualizar hooks globales

    def _toggle_hotkey(self, combo, state):
        self.hotkeys_manager.set_enabled(combo, state)
        self.update_hotkeys()

    def _open_edit_modal(self, action_id, current_combo):
        dlg = EditDialog(self, "Editar Atajo", current_combo)
        if dlg.exec():
            new_combo = dlg.result_value
            # Preservar color si existía
            current_data = self.hotkeys_manager.get_hotkeys().get(current_combo)
            color = current_data.get("color") if current_data else None
            
            self.hotkeys_manager.remove_hotkey(current_combo)
            self.hotkeys_manager.set_hotkey(new_combo.lower(), action_id, color=color)
            self._refresh_list()
            self.update_hotkeys()

    def _delete_hotkey(self, combo):
        self.hotkeys_manager.remove_hotkey(combo)
        self._refresh_list()
        self.update_hotkeys()

    def _open_color_picker_modal(self, key_combo):
        # Usamos el color dialog nativo de Qt por simplicidad y potencia
        color = QColorDialog.getColor(title="Elige color para el atajo", parent=self)
        
        if color.isValid():
            rgb = (color.red(), color.green(), color.blue())
            self.hotkeys_manager.set_hotkey(key_combo, "set_color_custom", color=rgb)
            self._refresh_list()
            self.update_hotkeys()