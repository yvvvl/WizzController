import keyboard
import logging
from .base_manager import JsonManager
from .favorites_manager import FavoritesManager

class HotkeysManager(JsonManager):
    def __init__(self, wiz_controller):
        super().__init__("hotkeys.json", default_data={"hotkeys": {}})
        self.wiz = wiz_controller
        self.fav_manager = FavoritesManager()
        self._apply_hooks()

    def set_hotkey(self, action_id, key_combination):
        current = self.data.get("hotkeys", {})
        # Eliminar si ya existe
        for aid, key in list(current.items()):
            if key == key_combination: del current[aid]
            
        current[action_id] = key_combination
        self.data["hotkeys"] = current
        self.save()
        self._apply_hooks()

    def get_hotkey(self, action_id):
        return self.data.get("hotkeys", {}).get(action_id)
        
    def get(self, key, default=None):
        return self.data.get(key, default)

    def _apply_hooks(self):
        try: keyboard.unhook_all()
        except: pass
        
        hotkeys = self.data.get("hotkeys", {})
        for action_id, key in hotkeys.items():
            if not key: continue
            cb = self._create_callback(action_id)
            if cb:
                try: keyboard.add_hotkey(key, cb, suppress=True)
                except: pass

    def _create_callback(self, action_id):
        if action_id == "toggle": return lambda: self.wiz.toggle()
        if action_id == "on": return lambda: self.wiz.turn_on()
        if action_id == "off": return lambda: self.wiz.turn_off()
        if action_id == "bri_up": return lambda: self.wiz.set_brightness(min(100, self.wiz.get_state().get("brightness",50)+10))
        if action_id == "bri_down": return lambda: self.wiz.set_brightness(max(10, self.wiz.get_state().get("brightness",50)-10))
        
        if action_id.startswith("color_"):
            cols = {"color_red": (255,0,0), "color_blue": (0,0,255), "color_green": (0,255,0)}
            if action_id in cols: return lambda: self.wiz.set_rgb(*cols[action_id])
            
        if action_id.startswith("fav_"):
            return lambda: self._exec_fav(action_id)
            
        return None

    def _exec_fav(self, aid):
        self.fav_manager = FavoritesManager() # Recargar
        parts = aid.split("_", 2)
        if len(parts) < 3: return
        ftype, fname = parts[1], parts[2]
        
        favs = self.fav_manager.get_favorites()
        for f in favs:
            if f["name"] == fname and f["type"] == ftype:
                if ftype == "rgb":
                    h = f["value"].lstrip('#')
                    self.wiz.set_rgb(*tuple(int(h[i:i+2], 16) for i in (0, 2, 4)))
                elif ftype == "white":
                    self.wiz.set_white(int(f["value"]))