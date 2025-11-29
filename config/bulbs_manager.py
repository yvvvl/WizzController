import os
import json

BULBS_DIR = os.path.join(os.path.dirname(__file__), "json")
BULBS_PATH = os.path.join(BULBS_DIR, "bulbs.json")

class BulbsManager:
    def __init__(self):
        self.bulbs = []
        self._load()

    def _load(self):
        if os.path.exists(BULBS_PATH):
            with open(BULBS_PATH, "r", encoding="utf-8") as f:
                self.bulbs = json.load(f)
        else:
            self.bulbs = []

    def save(self):
        os.makedirs(BULBS_DIR, exist_ok=True)
        with open(BULBS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.bulbs, f, indent=2, ensure_ascii=False)

    def add_bulb(self, bulb):
        self.bulbs.append(bulb)
        self.save()

    def get_bulbs(self):
        return self.bulbs

# Example usage
if __name__ == "__main__":
    manager = BulbsManager()
    manager.add_bulb({"id": "1", "ip": "192.168.1.100", "name": "Living Room"})
    print(manager.get_bulbs())