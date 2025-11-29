"""
voice_model_downloader.py
Descarga el modelo de voz de vosk en español si no está presente.
"""
import os
import urllib.request
import zipfile
from typing import Optional

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
MODEL_DIR = os.path.join("config", "voz", "vosk-model-small-es-0.42")
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), MODEL_DIR))


def get_model_path() -> Optional[str]:
    """
    Busca recursivamente la carpeta del modelo vosk dentro de config/voz y devuelve la ruta válida, incluso si está anidada varios niveles.
    """
    voz_root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "voz"))
    expected_files = ["model.conf", "am", "README", "LICENSE"]
    for root, dirs, files in os.walk(voz_root):
        # Considera válida si hay al menos uno de los archivos esperados y archivos .conf o .bin
        if any(f in files for f in expected_files) or any(f.endswith('.conf') or f.endswith('.bin') for f in files):
            return root
    return None

def download_and_extract_model(callback=None):
    import threading
    def _download():
        model_path = get_model_path()
        if model_path:
            print("Modelo de voz en español ya descargado y válido.")
            if callback:
                callback(model_path)
            return model_path
        print("Descargando modelo de voz en español para vosk...")
        voz_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "voz"))
        os.makedirs(voz_dir, exist_ok=True)
        zip_path = os.path.join(voz_dir, "vosk-model-es.zip")
        urllib.request.urlretrieve(MODEL_URL, zip_path)
        print("Extrayendo modelo...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Extrae normalmente
            zip_ref.extractall(voz_dir)
            # Si el zip contiene una carpeta raíz, mover su contenido a voz_dir
            root_items = zip_ref.namelist()
            if root_items:
                root_folder = root_items[0].split('/')[0]
                extracted_root = os.path.join(voz_dir, root_folder)
                if os.path.isdir(extracted_root):
                    # Mueve todo lo de la carpeta raíz al destino
                    for item in os.listdir(extracted_root):
                        src = os.path.join(extracted_root, item)
                        dst = os.path.join(voz_dir, item)
                        if os.path.isdir(src):
                            import shutil
                            shutil.move(src, dst)
                        else:
                            os.replace(src, dst)
                    # Elimina la carpeta raíz vacía
                    os.rmdir(extracted_root)
        os.remove(zip_path)
        print("Modelo descargado y extraído en config/voz.")
        # Busca la ruta válida después de extraer
        model_path = get_model_path()
        if model_path:
            if callback:
                callback(model_path)
            return model_path
        else:
            print("Error: modelo descargado pero no válido.")
            if callback:
                callback(None)
            return None
    threading.Thread(target=_download, daemon=True).start()

if __name__ == "__main__":
    download_and_extract_model()
