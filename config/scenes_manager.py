import os
import json

SCENES_DIR = os.path.join(os.path.dirname(__file__), "json")
SCENES_PATH = os.path.join(SCENES_DIR, "scenes.json")

class ScenesManager:
    def __init__(self):
        self.scenes = []
        self._load()

    def _load(self):
        if os.path.exists(SCENES_PATH):
            with open(SCENES_PATH, "r", encoding="utf-8") as f:
                self.scenes = json.load(f)
        else:
            self.scenes = []

    def save(self):
        os.makedirs(SCENES_DIR, exist_ok=True)
        with open(SCENES_PATH, "w", encoding="utf-8") as f:
            json.dump(self.scenes, f, indent=2, ensure_ascii=False)

    def add_scene(self, scene):
        self.scenes.append(scene)
        self.save()

    def get_scenes(self):
        return self.scenes
