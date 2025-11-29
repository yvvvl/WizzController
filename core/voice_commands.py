"""
voice_commands.py
Sistema de reconocimiento y gestión de comandos de voz en español para WiZ.
"""

import vosk
import sounddevice as sd
import json
import logging
import os
from typing import Callable, Dict, Any

class VoiceCommandManager:
    """
    Gestor de comandos de voz personalizados en español usando vosk y sounddevice.
    """
    def __init__(self, model_path: str) -> None:
        if not model_path or not os.path.exists(model_path):
             raise FileNotFoundError(f"No se encontró el modelo en la ruta: {model_path}")
             
        self.commands: Dict[str, Callable] = {}
        
        # Inicializamos el modelo con la ruta segura
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
        if old_phrase.lower() in self.commands:
            del self.commands[old_phrase.lower()]
            self.commands[new_phrase.lower()] = new_action
            logging.info(f"Comando de voz editado: '{old_phrase}' -> '{new_phrase}'")
        else:
            logging.warning(f"Comando de voz no encontrado: '{old_phrase}'")

    def remove_command(self, phrase: str) -> None:
        if phrase.lower() in self.commands:
            del self.commands[phrase.lower()]
            logging.info(f"Comando de voz eliminado: '{phrase}'")
        else:
            logging.warning(f"Comando de voz no encontrado: '{phrase}'")

    def listen_and_execute(self) -> None:
        import threading
        threading.Thread(target=self._listen_and_execute_thread, daemon=True).start()

    def _listen_and_execute_thread(self) -> None:
        import time
        logging.info("Escuchando comando de voz (vosk)...")
        try:
            rec = vosk.KaldiRecognizer(self.model, self.samplerate)
            # blocksize=8000 es un buen tamaño para latencia baja
            with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000, dtype='int16', channels=1) as stream:
                start_time = time.time()
                while time.time() - start_time < 10:  # 10 segundos de escucha
                    data_chunk = stream.read(4000)[0]
                    
                    # --- CORRECCIÓN AQUÍ: Convertimos el buffer a bytes ---
                    data_bytes = bytes(data_chunk)
                    
                    if rec.AcceptWaveform(data_bytes):
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
        return self.commands