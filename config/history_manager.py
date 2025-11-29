import os
import json

HISTORY_DIR = os.path.join(os.path.dirname(__file__), "json")
HISTORY_PATH = os.path.join(HISTORY_DIR, "history.json")

class HistoryManager:
    def __init__(self):
        self.history = []
        self._load()

    def _load(self):
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                self.history = json.load(f)
        else:
            self.history = []

    def save(self):
        os.makedirs(HISTORY_DIR, exist_ok=True)
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def add_entry(self, entry):
        self.history.append(entry)
        self.save()

    def get_history(self):
        return self.history
