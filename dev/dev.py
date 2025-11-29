import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# CONFIGURACIÓN
# Cambia esto por la ruta a tu archivo principal
TARGET_SCRIPT = "Wizz/main.py" 
# Carpetas a vigilar
WATCH_DIRECTORY = "Wizz"

class RestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.start_process()

    def start_process(self):
        if self.process:
            self.process.kill() # Mata el proceso anterior
        print(f"🔄 Reiniciando {TARGET_SCRIPT}...")
        # Lanza tu aplicación como un subproceso
        self.process = subprocess.Popen([sys.executable, TARGET_SCRIPT])

    def on_modified(self, event):
        # Si el archivo modificado es un .py, reinicia
        if event.src_path.endswith(".py"):
            self.start_process()

if __name__ == "__main__":
    event_handler = RestartHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_DIRECTORY, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()