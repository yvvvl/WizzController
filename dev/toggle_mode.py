import json
import os
import sys

# Rutas relativas asumiendo que el script está en WizzController/dev/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config", "json")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"dev_mode": False}
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return {"dev_mode": False}

def save_settings(settings):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

def main():
    settings = load_settings()
    current_mode = settings.get("dev_mode", False)
    
    # Invertir modo
    new_mode = not current_mode
    settings["dev_mode"] = new_mode
    
    save_settings(settings)
    
    print("\n" + "="*40)
    if new_mode:
        print("🟢 MODO DESARROLLADOR ACTIVADO")
        print("   - La app buscará el simulador (127.0.0.1)")
        print("   - No olvides ejecutar: python dev/mock_bulb.py")
    else:
        print("🔴 MODO PRODUCCIÓN ACTIVADO")
        print("   - La app ignorará el simulador")
        print("   - Solo buscará bombillas reales en la red")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()