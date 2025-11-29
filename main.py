# WizZ Main Entry Point

import sys
from pathlib import Path

# Ensure the Wizz directory is in the Python path
sys.path.append(str(Path(__file__).parent))

from ui.main_window import MainWindow
import customtkinter as ctk
from core.light_manager import LightManager
from config.config_manager import ConfigManager
from config.bulbs_manager import BulbsManager

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")

    config_manager = ConfigManager()
    bulbs_manager = BulbsManager()

    # Buscar ampolletas automáticamente si no hay IP guardada
    selected_ip = config_manager.get("selected_bulb_ip")
    if not selected_ip:
        from core.light_manager import LightManager
        lm = LightManager()
        bulbs = lm.discover_bulbs()
        if bulbs:
            first_bulb = bulbs[0]
            config_manager.set("selected_bulb_ip", first_bulb.get("ip"))
            bulbs_manager.add_bulb(first_bulb)
            selected_ip = first_bulb.get("ip")
        else:
            app = MainWindow(light_manager=lm)
            app.after(500, lambda: app.notify_no_bulb_found())
            app.mainloop()
            exit()
    else:
        from core.light_manager import LightManager
        lm = LightManager()
        lm.set_selected_bulb({"ip": selected_ip})

    app = MainWindow(light_manager=lm)
    app.mainloop()