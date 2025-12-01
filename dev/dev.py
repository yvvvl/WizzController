import sys
import time
import subprocess
import os
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

# CONFIGURACIÓN
TARGET_SCRIPT = "main.py" 
WATCH_DIRECTORY = "." 

class RestartHandler(PatternMatchingEventHandler):
    """
    Handler robusto que vigila cualquier cambio en archivos .py
    """
    def __init__(self):
        # patterns=["*.py"]: Solo reacciona a archivos Python
        # ignore_directories=True: Ignora cambios en carpetas (menos ruido)
        super().__init__(patterns=["*.py"], ignore_patterns=["*/.git/*", "*/__pycache__/*", "*/.venv/*"], ignore_directories=True)
        self.process = None
        self.last_restart = 0
        self.start_process()

    def start_process(self):
        """Mata y revive el proceso principal."""
        if self.process:
            try:
                self.process.kill()
            except:
                pass
        
        print(f"\n🔄 --- REINICIANDO APLICACIÓN ---")
        if os.path.exists(TARGET_SCRIPT):
            self.process = subprocess.Popen([sys.executable, TARGET_SCRIPT])
        else:
            print(f"❌ Error crítico: No encuentro {TARGET_SCRIPT} en {os.getcwd()}")

    def on_any_event(self, event):
        """
        Se ejecuta al detectar CUALQUIER evento (modificar, crear, mover, borrar)
        en un archivo .py que no esté ignorado.
        """
        # Debounce: Evita reinicios dobles si el editor guarda el archivo en dos pasos
        current_time = time.time()
        if current_time - self.last_restart < 1.0: # 1 segundo de espera mínima entre reinicios
            return

        print(f"📝 Detectado cambio en: {os.path.basename(event.src_path)}")
        self.last_restart = current_time
        self.start_process()

if __name__ == "__main__":
    # Autocorrección de ruta si ejecutas desde la carpeta dev/
    if not os.path.exists(TARGET_SCRIPT) and os.path.exists(f"../{TARGET_SCRIPT}"):
        os.chdir("..")
        print(f"📂 Ajustando directorio de trabajo a: {os.getcwd()}")

    event_handler = RestartHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_DIRECTORY, recursive=True)
    observer.start()

    print(f"👀 Bulldog activo. Vigilando archivos .py en {os.getcwd()}...")
    print("   (Presiona Ctrl+C para detener)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.kill()
    observer.join()