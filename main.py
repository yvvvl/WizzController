import flet as ft
import threading
from core.light_manager import LightManager
from ui.app import WizzApp

def main(page: ft.Page):
    # 1. Configuración de Ventana
    page.title = "WizZ Controller Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = "#0f172a" 
    
    # --- TAMAÑO Y LÍMITES ---
    page.window_width = 1100
    page.window_height = 750
    
    # Restricciones Nativas
    page.window_min_width = 900  
    page.window_min_height = 680
    
    # Centrado (Manual para evitar errores de versión)
    page.window_alignment = ft.MainAxisAlignment.CENTER

    # Fuentes
    page.fonts = {"Roboto": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"}

    # --- PROTECCIÓN EXTRA: EVENTO DE RESIZE ---
    # Si el sistema operativo ignora min_width, esto lo fuerza.
    def on_window_resize(e):
        corrected = False
        if page.window_width < 900:
            page.window_width = 900
            corrected = True
        if page.window_height < 680:
            page.window_height = 680
            corrected = True
        if corrected:
            page.update()
            
    page.on_resize = on_window_resize

    # ¡IMPORTANTE! Aplicar configuración a la ventana AHORA
    page.update()

    # 2. Instanciar Lógica
    wiz = LightManager()
    threading.Thread(target=wiz.startup_sequence, daemon=True).start()

    # 3. Iniciar UI
    app = WizzApp(page, wiz)

    # 4. Conectar Sincronización
    def on_bulb_update(state):
        try:
            # Sincronizar UI desde la bombilla
            app._raw_controls.sync_state(state)
        except Exception:
            pass

    wiz.set_callback(on_bulb_update)

if __name__ == "__main__":
    ft.app(target=main)