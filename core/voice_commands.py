"""
voice_commands.py
Sistema de reconocimiento y gestión de comandos de voz en español para WiZ.
"""

import vosk
import sounddevice as sd
import json
import logging
from typing import Callable, Dict, Any

class VoiceCommandManager:
    """
    Gestor de comandos de voz personalizados en español usando vosk y sounddevice.
    Permite crear, editar, eliminar y ejecutar comandos de voz.
    """
    def __init__(self, model_path: str = None) -> None:
        from core.voice_model_downloader import download_and_extract_model, get_model_path
        self.commands: Dict[str, Callable] = {}
        if not model_path:
            model_path = get_model_path()
            if not model_path:
                model_path = download_and_extract_model()
        # Solo pasar la ruta absoluta al modelo, nunca lang
        self.model = vosk.Model(model_path)
        self.samplerate = 16000

    def add_command(self, phrase: str, action: Callable) -> None:
        """
        Añade un comando de voz personalizado.
        Args:
            phrase (str): Frase en español que activa el comando.
            action (Callable): Función a ejecutar.
        """
        self.commands[phrase.lower()] = action
        logging.info(f"Comando de voz añadido: '{phrase}'")

    def edit_command(self, old_phrase: str, new_phrase: str, new_action: Callable) -> None:
        """
        Edita un comando de voz existente.
        """
        if old_phrase.lower() in self.commands:
            del self.commands[old_phrase.lower()]
            self.commands[new_phrase.lower()] = new_action
            logging.info(f"Comando de voz editado: '{old_phrase}' -> '{new_phrase}'")
        else:
            logging.warning(f"Comando de voz no encontrado: '{old_phrase}'")

    def remove_command(self, phrase: str) -> None:
        """
        Elimina un comando de voz.
        """
        if phrase.lower() in self.commands:
            del self.commands[phrase.lower()]
            logging.info(f"Comando de voz eliminado: '{phrase}'")
        else:
            logging.warning(f"Comando de voz no encontrado: '{phrase}'")

    def listen_and_execute(self) -> None:
        """
        Escucha el micrófono y ejecuta el comando si la frase coincide (offline, español).
        Ejecuta en un hilo para no bloquear la UI.
        """
        import threading
        threading.Thread(target=self._listen_and_execute_thread, daemon=True).start()

    def _listen_and_execute_thread(self) -> None:
        import time
        logging.info("Escuchando comando de voz (vosk)...")
        rec = vosk.KaldiRecognizer(self.model, self.samplerate)
        try:
            with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000, dtype='int16', channels=1) as stream:
                start_time = time.time()
                while time.time() - start_time < 10:  # 10 segundos de escucha
                    data = stream.read(4000)[0]
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        phrase = result.get('text', '').strip().lower()
                        if phrase:
                            logging.info(f"Frase reconocida: '{phrase}'")
                            action = self.commands.get(phrase)
                            if action:
                                action()
                                logging.info(f"Comando ejecutado: '{phrase}'")
                            else:
                                logging.warning(f"Comando de voz no registrado: '{phrase}'")
                            break
        except Exception as e:
            logging.error(f"Error en reconocimiento de voz: {e}")

    def list_commands(self) -> Dict[str, Callable]:
        """
        Devuelve todos los comandos de voz registrados.
        """
        return self.commands
