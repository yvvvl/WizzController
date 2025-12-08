import keyboard
import json
import os
import time

class HotkeysManager:
    def __init__(self, wiz_manager, config_dir="Wizz/config/json"):
        self.wiz = wiz_manager
        self.config_dir = config_dir
        self.hotkeys_file = os.path.join(config_dir, "hotkeys.json")
        self.custom_file = os.path.join(config_dir, "custom_actions.json")
        
        self.hotkeys = {}       
        self.custom_actions = {} 
        
        self.base_actions = {
            # --- CONTROL BÁSICO ---
            "toggle": lambda: self._toggle_lights(),
            "on": lambda: self.wiz.turn_on(),
            "off": lambda: self.wiz.turn_off(),
            
            # --- BRILLO ---
            "bri_up": lambda: self._adjust_brightness(10),
            "bri_down": lambda: self._adjust_brightness(-10),
            "bri_max": lambda: self.wiz.set_brightness(100),
            "bri_min": lambda: self.wiz.set_brightness(10),

            # --- TEMPERATURA (NUEVO: Ajuste Fino) ---
            "temp_warm": lambda: self.wiz.set_white(2700),
            "temp_neutral": lambda: self.wiz.set_white(4000),
            "temp_cold": lambda: self.wiz.set_white(6500),
            "temp_up": lambda: self._adjust_temp(500),    # + Frío
            "temp_down": lambda: self._adjust_temp(-500), # + Cálido

            # --- VELOCIDAD DE EFECTOS (NUEVO) ---
            "speed_up": lambda: self._adjust_speed(20),   # Más rápido
            "speed_down": lambda: self._adjust_speed(-20),# Más lento
            "speed_max": lambda: self.wiz.set_speed(200),
            "speed_min": lambda: self.wiz.set_speed(10),

            # --- ESCENAS ---
            "scene_ocean": lambda: self.wiz.set_scene(1),
            "scene_sunset": lambda: self.wiz.set_scene(3),
            "scene_party": lambda: self.wiz.set_scene(4),
            "scene_fireplace": lambda: self.wiz.set_scene(5),
            "scene_focus": lambda: self.wiz.set_scene(15),
            "scene_relax": lambda: self.wiz.set_scene(16),
            "scene_tv": lambda: self.wiz.set_scene(18),
            "scene_plant": lambda: self.wiz.set_scene(19),
            "scene_christmas": lambda: self.wiz.set_scene(27),
            "scene_halloween": lambda: self.wiz.set_scene(28),
            "scene_candlelight": lambda: self.wiz.set_scene(29),
            "scene_romance": lambda: self.wiz.set_scene(2),
            
            # --- COLORES BASE ---
            "color_red": lambda: self.wiz.set_rgb(255, 0, 0),
            "color_green": lambda: self.wiz.set_rgb(0, 255, 0),
            "color_blue": lambda: self.wiz.set_rgb(0, 0, 255),
        }
        
        self.actions_map = {}
        self.load_data()

    # ... (El código de carga/guardado es igual al anterior) ...
    # ... COPIA LOS MÉTODOS load_data, rebuild_actions_map, add_custom_color, etc. DEL CÓDIGO ANTERIOR ...
    # ... O simplemente mantén los que ya tenías y añade estos helpers abajo: ...

    def load_data(self):
        os.makedirs(self.config_dir, exist_ok=True)
        if os.path.exists(self.custom_file):
            try:
                with open(self.custom_file, 'r') as f:
                    self.custom_actions = json.load(f)
            except: self.custom_actions = {}
        if os.path.exists(self.hotkeys_file):
            try:
                with open(self.hotkeys_file, 'r') as f:
                    self.hotkeys = json.load(f)
            except: self.hotkeys = {}
        self.rebuild_actions_map()
        self.apply_hotkeys()

    def rebuild_actions_map(self):
        self.actions_map = self.base_actions.copy()
        for aid, data in self.custom_actions.items():
            if data.get('type') == 'rgb':
                r, g, b = data['value']
                self.actions_map[aid] = lambda r=r, g=g, b=b: self.wiz.set_rgb(r, g, b)

    def add_custom_color(self, r, g, b):
        r = int(r) if r is not None else 0
        g = int(g) if g is not None else 0
        b = int(b) if b is not None else 0
        timestamp = int(time.time())
        aid = f"custom_color_{timestamp}"
        name = f"Color Personalizado (#{r:02x}{g:02x}{b:02x})"
        self.custom_actions[aid] = {
            "type": "rgb", "value": [r, g, b], "name": name
        }
        self.save_custom()
        self.rebuild_actions_map()
        return aid, name

    def remove_custom_action(self, aid):
        if aid in self.custom_actions:
            del self.custom_actions[aid]
            self.save_custom()
            if aid in self.hotkeys:
                del self.hotkeys[aid]
                self.save_hotkeys()
            self.rebuild_actions_map()
            self.apply_hotkeys()

    def save_custom(self):
        try:
            with open(self.custom_file, 'w') as f: json.dump(self.custom_actions, f, indent=4)
        except: pass
    def save_hotkeys(self):
        try:
            with open(self.hotkeys_file, 'w') as f: json.dump(self.hotkeys, f, indent=4)
        except: pass
    def apply_hotkeys(self):
        try:
            keyboard.unhook_all()
            for name, combo in self.hotkeys.items():
                if name in self.actions_map and combo:
                    try: keyboard.add_hotkey(combo, self.actions_map[name], suppress=False)
                    except: pass
        except: pass
    def set_hotkey(self, name, combo):
        self.hotkeys[name] = combo; self.save_hotkeys(); self.apply_hotkeys()
    def remove_hotkey(self, name):
        if name in self.hotkeys: del self.hotkeys[name]; self.save_hotkeys(); self.apply_hotkeys()

    # --- HELPERS DE AJUSTE ---

    def _toggle_lights(self):
        state = self.wiz.get_state()
        if state["state"]: self.wiz.turn_off()
        else: self.wiz.turn_on()

    def _adjust_brightness(self, delta):
        state = self.wiz.get_state()
        current = state.get("brightness", 50)
        self.wiz.set_brightness(max(10, min(100, current + delta)))

    def _adjust_temp(self, delta):
        state = self.wiz.get_state()
        current = state.get("temp", 4000)
        # Wiz rango: 2200k a 6500k
        self.wiz.set_white(max(2200, min(6500, current + delta)))

    def _adjust_speed(self, delta):
        state = self.wiz.get_state()
        # La velocidad por defecto es 100
        current = state.get("speed", 100) 
        # Wiz rango velocidad: 10 (lento) a 200 (rápido)
        new_speed = max(10, min(200, current + delta))
        self.wiz.set_speed(new_speed)