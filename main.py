import flet as ft
from core.light_manager import LightManager
from ui.app import WizzApp
import sys

def main(page: ft.Page):
    page.title = "WizZ Desktop"
    
    # 1. Configuración de Ventana (Estricta)
    page.window_width = 400
    page.window_height = 700
    page.window_min_width = 300
    page.window_min_height = 500
    page.window_max_width = 600
    page.window_max_height = 900
    page.window_resizable = True
    page.window_always_on_top = False
    
    page.bgcolor = "#111827"
    page.padding = 0
    
    # 2. ¡ACTUALIZAR YA! (Antes de conectar nada)
    page.update()

    # Iniciar Backend
    print("Iniciando conexión WiZ...")
    wiz = LightManager()

    # Iniciar UI
    app = WizzApp(page, wiz)
    
    # Callback Backend -> UI
    def on_bulb_update(state):
        try:
            app.update_ui(state)
        except Exception as e:
            print(f"Error UI Sync: {e}")

    wiz.set_callback(on_bulb_update)
    
    # Iniciar secuencia de conexión
    wiz.startup_sequence()
    
    # Refresco final
    page.update()

if __name__ == "__main__":
    try:
        ft.app(target=main)
    except KeyboardInterrupt:
        sys.exit()