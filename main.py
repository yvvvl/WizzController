import sys
import logging
import traceback
import flet as ft

# Importamos los módulos
from core.light_controller import LightController
from ui.app import WizzApp

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

def main(page: ft.Page):
    print("DEBUG: Entrando en main()...")
    try:
        # --- 1. CONFIGURACIÓN DE VENTANA ---
        page.title = "WizZ Desktop (Lite)"
        page.bgcolor = "#0f172a"
        page.padding = 0
        page.theme_mode = ft.ThemeMode.DARK

        page.window.width = 1100
        page.window.height = 700
        page.window.min_width = 800
        page.window.min_height = 600
        
        print("DEBUG: Configuración de ventana lista.")

        # --- 2. INICIALIZAR BACKEND ---
        wiz = LightController()
        print("DEBUG: LightController inicializado.")
        
        # --- 3. INICIALIZAR FRONTEND ---
        # Pasamos page y wiz
        app = WizzApp(page, wiz)
        print("DEBUG: Interfaz (WizzApp) creada.")

        # Callback para actualizaciones
        def on_bulb_update(state):
            try: app.update_ui(state)
            except: pass

        wiz.set_callback(on_bulb_update)

        # --- 4. MONTAR LA UI ---
        page.add(app)
        page.update()
        
        print("DEBUG: Interfaz montada. Arrancando búsqueda de luces...")
        wiz.start() 
        print("DEBUG: Todo listo.")

    except Exception as e:
        print("!!! ERROR FATAL EN MAIN !!!")
        traceback.print_exc()

if __name__ == "__main__":
    print("DEBUG: Iniciando script...")
    try:
        # Usamos ft.app target=main
        ft.app(target=main)
    except KeyboardInterrupt:
        print("Cierre por usuario.")
        sys.exit()
    except Exception as e:
        print(f"Error al lanzar la app: {e}")
        input("Presiona Enter para salir...") # Pausa para leer error