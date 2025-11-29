"""
WizZ Main Entry Point
Script principal para inicializar la aplicación WiZ, cargar configuración y lanzar la UI.
"""

import sys
from pathlib import Path
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Ensure the Wizz directory is in the Python path
sys.path.append(str(Path(__file__).parent))

from ui.main_window import MainWindow
from core.light_manager import LightManager
from config.bulbs_manager import BulbsManager
from config.hotkeys_manager import HotkeysManager

# --- main entry point ---

def main() -> None:
    """
    Inicializa los managers, selecciona la bombilla y lanza la UI principal.
    """
    light_manager: LightManager = LightManager()
    bulbs_manager: BulbsManager = BulbsManager()
    # hotkeys_manager se inicializa dentro de la UI cuando es necesario, 
    # pero podemos instanciarlo aquí si fuera necesario en el futuro.

    selected_bulb: dict | None = None
    saved_bulbs = bulbs_manager.get_bulbs()
    
    # Si hay bombilla guardada, selecciona y aplica directamente
    if saved_bulbs:
        if isinstance(saved_bulbs, dict):
            # Si hay varias, tomamos la última agregada (o lógica a preferencia)
            last_ip = list(saved_bulbs.keys())[-1]
            selected_bulb = saved_bulbs[last_ip]
        elif isinstance(saved_bulbs, list):
            selected_bulb = saved_bulbs[-1]
            
        if selected_bulb:
            light_manager.set_selected_bulb(selected_bulb)
            # Registramos la bombilla en el light_manager para que active_bulb_id funcione
            bulb_ip = selected_bulb.get("ip")
            if bulb_ip:
                light_manager.register_bulb(bulb_ip, bulb_ip)

    else:
        # Solo si no hay bombilla guardada, buscar en la red
        bulbs: list = light_manager.discover_bulbs()
        if bulbs:
            selected_bulb = bulbs[0]
            bulbs_manager.add_bulb(selected_bulb)
            light_manager.set_selected_bulb(selected_bulb)
            bulb_ip = selected_bulb.get("ip")
            if bulb_ip:
                light_manager.register_bulb(bulb_ip, bulb_ip)

    app: MainWindow = MainWindow(light_manager)
    if selected_bulb:
        app._show_selected_bulb()
    app.mainloop()

if __name__ == "__main__":
    main()