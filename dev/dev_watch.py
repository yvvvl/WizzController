"""
Sistema de desarrollo con hot reload avanzado usando watchdog
Detecta cambios en archivos Python y recarga la aplicación automáticamente
"""
import sys
import time
import subprocess
import threading
import psutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console

console = Console()

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self, script_path):
        self.script_path = script_path
        self.process = None
        self.output_thread = None
        self._stop_output = threading.Event()
        self.restart_app()
        self.last_restart = time.time()
        
    def on_modified(self, event):
        # Ignorar cambios en __pycache__, archivos .pyc, y archivos JSON de configuración
        if event.src_path.endswith('.pyc') or '__pycache__' in event.src_path:
            return
        
        # Solo recargar para archivos Python
        if not event.src_path.endswith('.py'):
            return
            
        # Evitar múltiples recargas rápidas
        current_time = time.time()
        if current_time - self.last_restart < 1.0:  # Cooldown de 1 segundo
            return
            
        console.print(f"\n[yellow]🔄 Cambio detectado en: {event.src_path}[/yellow]")
        self.restart_app()
        self.last_restart = current_time
    
    def kill_process_tree(self, pid):
        """Mata el proceso y todos sus hijos"""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # Terminar todos los procesos hijos primero
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            
            # Terminar el proceso padre
            parent.terminate()
            
            # Esperar a que terminen
            gone, alive = psutil.wait_procs(children + [parent], timeout=3)
            
            # Forzar kill si aún están vivos
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            console.print(f"[red]Error al matar proceso: {e}[/red]")
    
    def restart_app(self):
        if self.process:
            console.print("[red]⏹️  Deteniendo aplicación y todos sus procesos...[/red]")
            self.kill_process_tree(self.process.pid)
            time.sleep(0.5)  # Pequeña pausa para asegurar que todo se limpió
        
        # Reiniciar lector de salida
        if self.output_thread and self.output_thread.is_alive():
            self._stop_output.set()
            try:
                self.output_thread.join(timeout=1)
            except Exception:
                pass
        self._stop_output.clear()

        console.print("[green]▶️  Iniciando aplicación...[/green]")
        # Ejecutar Python en modo no bufferizado para que los logs salgan en tiempo real
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(self.script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # Hilo para retransmitir stdout/stderr en tiempo real
        def _stream_output(proc, stop_event):
            try:
                for line in proc.stdout:
                    if stop_event.is_set():
                        break
                    if line:
                        # Imprimir tal cual, como si se ejecutara normalmente
                        console.print(line.rstrip())
            except Exception as e:
                console.print(f"[red]⚠️ Error leyendo salida: {e}[/red]")
        self.output_thread = threading.Thread(target=_stream_output, args=(self.process, self._stop_output), daemon=True)
        self.output_thread.start()

def main():
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   🔥 WizZ Hot Reload Development Mode 🔥[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")
    
    # Obtener el directorio raíz del proyecto (padre de dev/)
    root_dir = Path(__file__).parent.parent if "dev" in Path(__file__).parts else Path(__file__).parent
    script_path = root_dir / "main.py"
    watch_paths = [
        root_dir / "ui",
        root_dir / "core",
        root_dir / "config",
    ]
    
    console.print(f"[cyan]📝 Script principal: {script_path}[/cyan]")
    console.print(f"[cyan]👀 Monitoreando cambios en:[/cyan]")
    for path in watch_paths:
        console.print(f"   • {path}")
    console.print("\n[yellow]Presiona Ctrl+C para detener[/yellow]\n")
    
    handler = CodeChangeHandler(str(script_path))
    observer = Observer()
    
    for path in watch_paths:
        if path.exists():
            observer.schedule(handler, str(path), recursive=True)
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[red]🛑 Deteniendo hot reload...[/red]")
        observer.stop()
        if handler.process:
            console.print("[red]⏹️  Cerrando aplicación...[/red]")
            handler.kill_process_tree(handler.process.pid)
        if handler.output_thread and handler.output_thread.is_alive():
            handler._stop_output.set()
            try:
                handler.output_thread.join(timeout=1)
            except Exception:
                pass
    
    observer.join()
    console.print("[green]✅ Hot reload detenido[/green]")

if __name__ == "__main__":
    main()
