import keyboard
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QSlider, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette, QKeySequence, QShortcut

# Widgets y Ventanas Migradas
from ui.widgets.modern_color_picker import ModernColorPicker 
from ui.scenes_ui import ScenesUI
from ui.hotkeys_settings import HotkeysSettings
from ui.voice_commands_ui import VoiceCommandsUI

# Managers Lógicos
from config.hotkeys_manager import HotkeysManager
from core.actions import get_action_func

class MainWindow(QMainWindow):
    def __init__(self, light_manager):
        super().__init__()
        self.light_manager = light_manager
        
        # Inicializar Managers UI
        self.hotkeys_manager = HotkeysManager()
        
        # Configuración Ventana
        self.setWindowTitle("WizZ Controller Pro (PyQt6)")
        self.resize(950, 600)
        self.setMinimumSize(850, 550)
        
        # Aplicar Tema Oscuro
        self._apply_dark_theme()

        # --- UI PRINCIPAL ---
        central = QWidget()
        self.setCentralWidget(central)
        
        # Layout horizontal (Splitter: Izq | Der)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25)

        # ==========================================
        # PANEL IZQUIERDO: COLOR
        # ==========================================
        left_panel = QFrame()
        left_panel.setStyleSheet(".QFrame { background-color: #2b2b2b; border-radius: 15px; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_color = QLabel("Cromaticidad")
        lbl_color.setStyleSheet("color: #888; font-weight: bold; font-size: 14px;")
        lbl_color.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(lbl_color)

        # Widget de Color Magnífico
        self.color_picker = ModernColorPicker()
        self.color_picker.colorChanged.connect(self._on_color_changed)
        left_layout.addWidget(self.color_picker)
        
        main_layout.addWidget(left_panel, 1)

        # ==========================================
        # PANEL DERECHO: CONTROLES
        # ==========================================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)

        # 1. Header
        header = QHBoxLayout()
        title = QLabel("WizZ Control Center")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header.addWidget(title)
        header.addStretch()
        
        btn_search = QPushButton("🔍 Buscar")
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.setFixedSize(100, 35)
        btn_search.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; border-radius: 5px; border: none; }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        btn_search.clicked.connect(self._search_bulbs)
        header.addWidget(btn_search)
        right_layout.addLayout(header)

        # 2. Información Estado
        self.info_box = QFrame()
        self.info_box.setStyleSheet("background-color: #2b2b2b; border-radius: 10px;")
        info_layout = QVBoxLayout(self.info_box)
        
        self.lbl_status = QLabel("Estado: Desconectado")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #e74c3c;")
        
        self.lbl_ip = QLabel("IP: --")
        self.lbl_ip.setStyleSheet("color: #aaa;")
        
        info_layout.addWidget(self.lbl_status)
        info_layout.addWidget(self.lbl_ip)
        right_layout.addWidget(self.info_box)

        right_layout.addSpacing(20)

        # 3. Sliders Principales
        # Brillo
        right_layout.addWidget(QLabel("Brillo Maestro"))
        self.slider_bri = QSlider(Qt.Orientation.Horizontal)
        self.slider_bri.setRange(10, 100)
        self.slider_bri.setValue(100)
        self.slider_bri.valueChanged.connect(self._on_brightness_change)
        right_layout.addWidget(self.slider_bri)

        # Temperatura
        right_layout.addWidget(QLabel("Temperatura (Kelvin)"))
        self.slider_temp = QSlider(Qt.Orientation.Horizontal)
        self.slider_temp.setRange(2200, 6500)
        self.slider_temp.setValue(4000)
        self.slider_temp.setInvertedAppearance(True) 
        self.slider_temp.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #aaddff, stop:1 #ffaa55);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: white; width: 16px; margin: -5px 0; border-radius: 8px;
            }
        """)
        self.slider_temp.valueChanged.connect(self._on_temp_change)
        right_layout.addWidget(self.slider_temp)

        right_layout.addStretch()

        # 4. Botones Grandes (ON/OFF)
        actions_layout = QHBoxLayout()
        
        btn_on = QPushButton("ENCENDER")
        btn_on.setFixedHeight(50)
        btn_on.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_on.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; border-radius: 8px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:pressed { background-color: #1e8449; }
        """)
        btn_on.clicked.connect(self._turn_on)
        
        btn_off = QPushButton("APAGAR")
        btn_off.setFixedHeight(50)
        btn_off.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_off.setStyleSheet("""
            QPushButton { background-color: #c0392b; color: white; border-radius: 8px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #e74c3c; }
            QPushButton:pressed { background-color: #922b21; }
        """)
        btn_off.clicked.connect(self._turn_off)

        actions_layout.addWidget(btn_on)
        actions_layout.addWidget(btn_off)
        right_layout.addLayout(actions_layout)

        # 5. Barra Inferior (Menú Secundario)
        bottom_menu = QHBoxLayout()
        
        # Estilo botones secundarios
        sec_style = """
            QPushButton { background: transparent; color: #ccc; border: 1px solid #555; border-radius: 4px; padding: 8px; } 
            QPushButton:hover { color: white; border-color: #888; background-color: #333; }
        """
        
        btn_scenes = QPushButton("🎨 Galería de Escenas")
        btn_scenes.setStyleSheet(sec_style)
        btn_scenes.clicked.connect(self._open_scenes)

        btn_hotkeys = QPushButton("⌨ Config. Teclas")
        btn_hotkeys.setStyleSheet(sec_style)
        btn_hotkeys.clicked.connect(self._open_hotkeys)
        
        btn_voice = QPushButton("🎤 Comandos de Voz")
        btn_voice.setStyleSheet(sec_style)
        btn_voice.clicked.connect(self._open_voice)

        bottom_menu.addWidget(btn_scenes)
        bottom_menu.addWidget(btn_hotkeys)
        bottom_menu.addWidget(btn_voice)
        right_layout.addLayout(bottom_menu)

        main_layout.addWidget(right_panel, 1)

        # Inicialización lógica
        self._init_shortcuts()
        self._check_connection_status()
        self._apply_global_hotkeys() # Cargar hooks iniciales

    def _apply_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(palette)

    def _init_shortcuts(self):
        self.shortcut_on = QShortcut(QKeySequence("Ctrl+E"), self)
        self.shortcut_on.activated.connect(self._turn_on)

        self.shortcut_off = QShortcut(QKeySequence("Ctrl+A"), self)
        self.shortcut_off.activated.connect(self._turn_off)

    # --- VENTANAS SECUNDARIAS ---

    def _open_scenes(self):
        # Pasamos el light_manager para que la ventana pueda ejecutar acciones
        dlg = ScenesUI(self, self.light_manager)
        dlg.exec()

    def _open_hotkeys(self):
        # Pasamos el callback para recargar los hooks si el usuario cambia algo
        dlg = HotkeysSettings(self, self.hotkeys_manager, self._apply_global_hotkeys)
        dlg.exec()

    def _open_voice(self):
        # Abrimos la ventana de voz. El manager se crea dentro si no existe.
        dlg = VoiceCommandsUI(self)
        dlg.exec()

    # --- LOGICA HOTKEYS GLOBALES ---
    
    def _apply_global_hotkeys(self):
        """Lee la configuración y 'engancha' las teclas globales"""
        try:
            keyboard.unhook_all()
            hotkeys = self.hotkeys_manager.get_hotkeys()
            
            for combo, data in hotkeys.items():
                if data.get("enabled", True):
                    action_id = data.get("action")
                    # Obtenemos la función pura (ej: turn_on)
                    func_base = get_action_func(action_id)
                    
                    # Verificamos si tiene color guardado
                    color_arg = data.get("color")
                    
                    # Creamos el ejecutor final
                    if action_id == "set_color_custom" and color_arg:
                         # Lambda que pasa el manager y el color
                        def executor(c=color_arg):
                            try:
                                func_base(self.light_manager, c)
                            except: pass
                    else:
                        # Lambda que pasa solo el manager
                        def executor():
                            try:
                                func_base(self.light_manager)
                            except: pass

                    # Registrar en libreria keyboard
                    keyboard.add_hotkey(combo, executor)
                    
            print(f"Hotkeys globales recargados: {len(hotkeys)} activos")
        except Exception as e:
            print(f"Error cargando hotkeys: {e}")

    # --- LÓGICA DE CONTROL ---
    
    def _turn_on(self):
        self.light_manager.turn_on()
        self._update_status(True)

    def _turn_off(self):
        self.light_manager.turn_off()
        self._update_status(False)

    def _on_brightness_change(self, val):
        self.light_manager.set_brightness(val)

    def _on_temp_change(self, val):
        self.light_manager.set_temperature(val)

    def _on_color_changed(self, rgb_tuple):
        self.light_manager.set_color(rgb_tuple)

    def _update_status(self, is_on):
        if is_on:
            self.lbl_status.setText("Estado: ENCENDIDO")
            self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #2ecc71;") 
        else:
            self.lbl_status.setText("Estado: APAGADO")
            self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #e74c3c;")

    def _check_connection_status(self):
        if hasattr(self.light_manager, 'selected_bulb') and self.light_manager.selected_bulb:
            ip = self.light_manager.selected_bulb.get('ip', 'Desconocida')
            self.lbl_ip.setText(f"IP Conectada: {ip}")
        else:
            self.lbl_ip.setText("IP: No seleccionada")
        
        QTimer.singleShot(2000, self._check_connection_status)

    def _search_bulbs(self):
        bulbs = self.light_manager.discover_bulbs()
        if bulbs:
            bulb = bulbs[0]
            self.light_manager.set_selected_bulb(bulb)
            if bulb.get("ip"):
                self.light_manager.register_bulb(bulb.get("ip"), bulb.get("ip"))
                # Guardar para la próxima
                self.light_manager.bulbs_manager.add_bulb(bulb)
            QMessageBox.information(self, "Éxito", f"Ampolleta encontrada: {bulb.get('ip')}")
            self._check_connection_status()
        else:
            QMessageBox.warning(self, "Error", "No se encontraron ampolletas WiZ en la red.")