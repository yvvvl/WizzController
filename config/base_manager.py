import json
import os
import threading


class JsonManager:
    def __init__(self, filename, default_data=None):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.json_dir = os.path.join(self.base_dir, "json")
        self.filepath = os.path.join(self.json_dir, filename)
        self.lock = threading.Lock()
        os.makedirs(self.json_dir, exist_ok=True)
        self.data = self._load_data(default_data)

    def _load_data(self, default_data):
        if not os.path.exists(self.filepath):
            return default_data if default_data is not None else {}
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default_data if default_data is not None else {}

    def save(self):
        with self.lock:
            try:
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Error guardando {self.filepath}: {e}")

    def get(self, key, default=None):
        if isinstance(self.data, dict):
            return self.data.get(key, default)
        return default
