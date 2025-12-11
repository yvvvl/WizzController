import sys
import logging
import flet as ft

# Controladores
from core.light_controller import LightController
from core.voice_controller import VoiceController
from ui.app import WizzApp

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

def main(page: ft.Page):
    # --- 1. CONFIGURACIÓN DE VENTANA ---
    page.title = "WizZ Desktop AI"
    page.bgcolor = "#0f172a"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK

    # Tamaño inicial
    page.window.width = 1100
    page.window.height = 700
    page.window.min_width = 800
    page.window.min_height = 600
    
    print("[MAIN] Iniciando servicios...")

    # --- 2. INICIALIZAR BACKEND ---
    wiz = LightController()
    
    # Inicializamos voz PERO NO LA ARRANCAMOS AÚN
    voice = VoiceController(wiz)

    # --- 3. INICIALIZAR FRONTEND ---
    # La App crea los componentes (Dashboard, etc.)
    app = WizzApp(page, wiz, voice)

    # Callbacks de sincronización Backend -> Frontend
    def on_bulb_update(state):
        try: app.update_ui(state)
        except: pass

    wiz.set_callback(on_bulb_update)

    # --- 4. ARRANQUE FINAL ---
    # Primero renderizamos la página para que los controles existan ("se monten")
    page.update()
    
    print("[MAIN] Interfaz lista. Arrancando motores...")
    
    # AHORA es seguro arrancar los hilos de fondo
    wiz.start()   # Busca luces
    voice.start() # Escucha audio (Si descarga modelo, la UI ya lo mostrará)

if __name__ == "__main__":
    try:
        ft.app(target=main)
    except KeyboardInterrupt:
        sys.exit()