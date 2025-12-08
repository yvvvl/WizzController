import flet as ft
from core.light_manager import LightManager  # Importación corregida
from ui.app import WizzApp
import sys

def main(page: ft.Page):
    page.title = "WizZ Desktop"
    
    # --- RESPONSIVIDAD INTELIGENTE ---
    # La app se adapta y permite comprimir hasta límites seguros
    page.window_min_width = 340  
    page.window_min_height = 520
    
    # Tamaño inicial óptimo
    page.window_width = 450
    page.window_height = 780
    page.window_resizable = True
    
    page.bgcolor = "#111827"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    
    page.update()

    print("Iniciando conexión WiZ...")
    wiz = LightManager()

    # --- INICIAR UI ---
    # IMPORTANTE: WizzApp ya se encarga de pintarse a sí misma.
    # No usamos 'page.add(app)' porque causaría el error que viste antes.
    app = WizzApp(page, wiz)
    
    # Callback para mantener la UI sincronizada con las luces reales
    def on_bulb_update(state):
        try:
            app.update_ui(state)
        except Exception as e:
            print(f"Error UI Sync: {e}")

    wiz.set_callback(on_bulb_update)
    
    # Arrancar descubrimiento de luces en segundo plano
    wiz.startup_sequence()

if __name__ == "__main__":
    try:
        ft.app(target=main)
    except KeyboardInterrupt:
        sys.exit()