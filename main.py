import sys
import logging
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from core.light_manager import LightManager
from config.config_manager import ConfigManager
from config.logs_manager import setup_logging
from ui.main_window import MainWindow 

def main():
    # 1. Configuración inicial
    setup_logging()
    logging.info("Iniciando WizzController (PyQt6 Edition)...")
    
    ConfigManager()
    
    # 2. Inicializar Managers
    light_manager = LightManager()
    
    # 3. Preparar Interfaz Gráfica
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Ventana Principal
    window = MainWindow(light_manager)
    window.show()

    # 4. Servicios en segundo plano
    # IMPORTANTE: Ahora llamamos a 'startup_sequence'
    logging.info("Iniciando servicio de conexión...")
    threading.Thread(target=light_manager.startup_sequence, daemon=True).start()

    # 5. Ejecutar Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()