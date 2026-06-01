import uuid
from .base_manager import JsonManager

class VoiceManager(JsonManager):
    def __init__(self):
        super().__init__("voice_commands.json", default_data={
            "wake_words": ["computadora"],
            "commands": []
        })

    # --- Lógica de Palabras Clave (Wake Word) ---
    def get_wake_words(self):
        data = self.data.get("wake_words", ["computadora"])
        if isinstance(data, str): return [data]
        return data

    def set_wake_words(self, text_input):
        if not text_input: 
            words = []
        else:
            words = [w.strip().lower() for w in text_input.split(",") if w.strip()]
        
        self.data["wake_words"] = words
        self.save()

    # --- Lógica de Comandos ---
    def get_commands(self):
        raw = self.data.get("commands", [])
        if not isinstance(raw, list): return []
        return [c for c in raw if isinstance(c, dict)]

    def add_command(self, phrases, action, desc):
        """Crea un nuevo comando."""
        new_cmd = {
            "id": str(uuid.uuid4()),
            "phrases": phrases,
            "action": action,
            "desc": desc
        }
        if not isinstance(self.data.get("commands"), list):
            self.data["commands"] = []
        self.data["commands"].append(new_cmd)
        self.save()

    def update_command(self, uid, phrases, action, desc):
        """Actualiza un comando existente por su ID."""
        cmds = self.get_commands()
        for cmd in cmds:
            if cmd.get("id") == uid:
                cmd["phrases"] = phrases
                cmd["action"] = action
                cmd["desc"] = desc
                self.save()
                return True
        return False

    def remove_command(self, uid):
        self.data["commands"] = [x for x in self.get_commands() if x.get("id") != uid]
        self.save()