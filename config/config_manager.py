import os
import json

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "json")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

class ConfigManager:
    def __init__(self):
        self.config = {}
        self._load()

    def _load(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

# Example usage
if __name__ == "__main__":
    config = ConfigManager()
    config.set("last_brightness", 75)
    config.save_config()
    print(config.get("last_brightness"))