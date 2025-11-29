import os
import json

LOGS_DIR = os.path.join(os.path.dirname(__file__), "json")
LOGS_PATH = os.path.join(LOGS_DIR, "logs.json")

class LogsManager:
    def __init__(self):
        self.logs = []
        self._load()

    def _load(self):
        if os.path.exists(LOGS_PATH):
            with open(LOGS_PATH, "r", encoding="utf-8") as f:
                self.logs = json.load(f)
        else:
            self.logs = []

    def save(self):
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(LOGS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)

    def add_log(self, log):
        self.logs.append(log)
        self.save()

    def get_logs(self):
        return self.logs
