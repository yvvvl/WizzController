import os
import json

PRESETS_DIR = os.path.join(os.path.dirname(__file__), "json")
PRESETS_PATH = os.path.join(PRESETS_DIR, "presets.json")

class PresetsManager:
    def __init__(self):
        self.presets = []
        self._load()

    def _load(self):
        if os.path.exists(PRESETS_PATH):
            with open(PRESETS_PATH, "r", encoding="utf-8") as f:
                self.presets = json.load(f)
        else:
            self.presets = []

    def save(self):
        os.makedirs(PRESETS_DIR, exist_ok=True)
        with open(PRESETS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.presets, f, indent=2, ensure_ascii=False)

    def add_preset(self, preset):
        self.presets.append(preset)
        self.save()

    def get_presets(self):
        return self.presets
