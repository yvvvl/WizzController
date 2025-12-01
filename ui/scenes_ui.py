from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QGridLayout, 
                             QTabWidget, QInputDialog, QMessageBox)
from PyQt6.QtCore import Qt
from core.wiz_scenes_data import SCENES_DATA
from config.presets_manager import PresetsManager

class ScenesUI(QDialog):
    def __init__(self, parent, light_manager):
        super().__init__(parent)
        self.setWindowTitle("Galería de Luz")
        self.resize(750, 600)
        self.light_manager = light_manager
        self.presets_manager = PresetsManager()

        layout = QVBoxLayout(self)
        
        # Pestañas
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Pestaña 1: Escenas WiZ
        self.tab_scenes = QWidget()
        self._build_scenes_tab()
        self.tabs.addTab(self.tab_scenes, "Escenas WiZ")
        
        # Pestaña 2: Mis Colores
        self.tab_colors = QWidget()
        self._build_colors_tab()
        self.tabs.addTab(self.tab_colors, "Mis Colores")

    def _build_scenes_tab(self):
        layout = QVBoxLayout(self.tab_scenes)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        for category, scenes in SCENES_DATA.items():
            # Título Categoría
            lbl_cat = QLabel(category)
            lbl_cat.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 15px; color: #ddd;")
            content_layout.addWidget(lbl_cat)
            
            # Grid de botones
            grid_frame = QWidget()
            grid = QGridLayout(grid_frame)
            grid.setSpacing(10)
            
            columns = 3
            for i, (name, scene_id, icon) in enumerate(scenes):
                btn = QPushButton(f"{icon}  {name}")
                btn.setFixedHeight(45)
                # Estilo tarjeta
                btn.setStyleSheet("""
                    QPushButton { background-color: #333; border: 1px solid #444; border-radius: 5px; text-align: left; padding-left: 10px; }
                    QPushButton:hover { background-color: #444; border-color: #666; }
                """)
                # Usamos lambda con default arg para capturar el valor
                btn.clicked.connect(lambda _, sid=scene_id: self.light_manager.activate_scene(sid))
                
                grid.addWidget(btn, i // columns, i % columns)
            
            content_layout.addWidget(grid_frame)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _build_colors_tab(self):
        layout = QVBoxLayout(self.tab_colors)
        
        # Panel Superior
        top_frame = QFrame()
        top_layout = QHBoxLayout(top_frame)
        btn_save = QPushButton("💾 Guardar Color Actual")
        btn_save.setStyleSheet("background-color: #1f6aa5; color: white; padding: 8px;")
        btn_save.clicked.connect(self._save_current_color)
        top_layout.addWidget(btn_save)
        layout.addWidget(top_frame)
        
        # Área de Scroll para colores
        self.colors_scroll = QScrollArea()
        self.colors_scroll.setWidgetResizable(True)
        self.colors_scroll_content = QWidget()
        self.colors_grid = QGridLayout(self.colors_scroll_content)
        self.colors_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.colors_scroll.setWidget(self.colors_scroll_content)
        layout.addWidget(self.colors_scroll)
        
        self._refresh_colors_grid()

    def _refresh_colors_grid(self):
        # Limpiar grid
        # Truco para borrar widgets en Qt Layouts
        for i in reversed(range(self.colors_grid.count())): 
            widget = self.colors_grid.itemAt(i).widget()
            if widget: widget.setParent(None)

        presets = self.presets_manager.get_presets()
        if not presets:
            self.colors_grid.addWidget(QLabel("No hay colores guardados."), 0, 0)
            return

        columns = 4
        i = 0
        for name, rgb in presets.items():
            hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            
            card = QFrame()
            card.setFixedSize(100, 120)
            card.setStyleSheet("background-color: #2b2b2b; border-radius: 8px;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(5,5,5,5)
            
            # Botón de Color
            btn_col = QPushButton()
            btn_col.setFixedSize(80, 60)
            btn_col.setStyleSheet(f"background-color: {hex_color}; border: none; border-radius: 5px;")
            btn_col.clicked.connect(lambda _, r=rgb: self.light_manager.set_color(tuple(r)))
            
            # Etiqueta
            lbl_name = QLabel(name)
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Cortar texto largo
            lbl_name.setStyleSheet("font-size: 10px; color: #ccc;")
            
            # Botón Borrar pequeño
            btn_del = QPushButton("×")
            btn_del.setFixedSize(20, 20)
            btn_del.setStyleSheet("background-color: #c0392b; border-radius: 10px; padding: 0px;")
            btn_del.clicked.connect(lambda _, n=name: self._delete_color(n))
            
            card_layout.addWidget(btn_col, 0, Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(lbl_name)
            card_layout.addWidget(btn_del, 0, Qt.AlignmentFlag.AlignCenter)
            
            self.colors_grid.addWidget(card, i // columns, i % columns)
            i += 1

    def _save_current_color(self):
        # Intentamos obtener el último color (el manager debe tener esta prop)
        last_rgb = getattr(self.light_manager, 'last_rgb', (255, 255, 255))
        
        name, ok = QInputDialog.getText(self, "Guardar Color", "Nombre para este color:")
        if ok and name:
            self.presets_manager.add_preset(name, list(last_rgb))
            self._refresh_colors_grid()

    def _delete_color(self, name):
        reply = QMessageBox.question(self, "Confirmar", f"¿Eliminar '{name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.presets_manager.delete_preset(name)
            self._refresh_colors_grid()