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
from core.actions import get_action_func

class VoiceCommandManager:
    """
    Gestor de comandos de voz personalizados en español usando vosk y sounddevice.
    """
    def __init__(self, model_path: str) -> None:
        if not model_path or not os.path.exists(model_path):
             raise FileNotFoundError(f"No se encontró el modelo en la ruta: {model_path}")
             
        self.commands: Dict[str, Callable] = {}
        self._phrase_to_action_id: Dict[str, str] = {}
        
        # Inicializamos el modelo con la ruta segura
        self.model = vosk.Model(model_path)
        self.samplerate = 16000
        self._load_default_spanish_phrases()

    def add_command(self, phrase: str, action: Callable) -> None:
        """
        Añade un comando de voz personalizado.
        Args:
            phrase (str): Frase en español que activa el comando.
            action (Callable): Función a ejecutar.
        """
        self.commands[phrase.lower()] = action
        logging.info(f"Comando de voz añadido: '{phrase}'")

    def add_action_phrase(self, phrase: str, action_id: str) -> None:
        """Mapa frase en español -> action_id del backend de acciones."""
        self._phrase_to_action_id[phrase.lower()] = action_id
        logging.info(f"Frase añadida: '{phrase}' -> {action_id}")

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

    def execute_phrase(self, light_manager, phrase: str) -> bool:
        """Ejecuta acción si la frase está mapeada. Devuelve True si se ejecutó."""
        key = (phrase or '').strip().lower()
        aid = self._phrase_to_action_id.get(key)
        if not aid:
            return False
        func = get_action_func(aid)
        func(light_manager)
        return True

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
                                logging.info(f"Comando ejecutado (custom): '{phrase}'")
                            else:
                                # Intentar frase por catálogo simple
                                if self.execute_phrase(getattr(self, 'light_manager', None), phrase):
                                    logging.info(f"Acción por frase ejecutada: '{phrase}'")
                                else:
                                    logging.warning(f"Comando de voz no registrado: '{phrase}'")
                            break
        except Exception as e:
            logging.error(f"Error en reconocimiento de voz: {e}")

    def list_commands(self) -> Dict[str, Callable]:
        return self.commands

    def attach_light_manager(self, light_manager):
        """Adjunta el LightManager para ejecutar acciones directas por frase."""
        self.light_manager = light_manager

    def _load_default_spanish_phrases(self) -> None:
        """Frases sencillas en español mapeadas a acciones comunes."""
        defaults = {
            # Encendido/Apagado
            "enciende": "turn_on",
            "apaga": "turn_off",
            "alternar": "toggle_power",
            # Brillo
            "sube brillo": "brightness_up_10",
            "baja brillo": "brightness_down_10",
            "brillo 10": "brightness_10",
            "brillo 25": "brightness_25",
            "brillo 50": "brightness_50",
            "brillo 75": "brightness_75",
            "brillo 100": "brightness_100",
            # Temperatura
            "luz cálida": "temp_2700",
            "luz neutra": "temp_4000",
            "luz fría": "temp_6500",
            "sube temperatura": "temp_up_300",
            "baja temperatura": "temp_down_300",
            # Colores
            "rojo": "color_red",
            "verde": "color_green",
            "azul": "color_blue",
            "amarillo": "color_yellow",
            "cian": "color_cyan",
            "magenta": "color_magenta",
            "blanco": "color_white",
            # Escenas
            "océano": "scene_ocean",
            "romance": "scene_romance",
            "atardecer": "scene_sunset",
            "fiesta": "scene_party",
            "chimenea": "scene_fireplace",
            "bosque": "scene_forest",
            "pastel": "scene_pastel",
            "despertar": "scene_wakeup",
            "a dormir": "scene_bedtime",
            "navidad": "scene_christmas",
            "halloween": "scene_halloween",
            "vela": "scene_candle",
            "pulso": "scene_pulse",
            "steampunk": "scene_steampunk",
            # Blancos/funcionales
            "blanco cálido": "scene_warm_white",
            "luz de día": "scene_daylight",
            "blanco frío": "scene_cool_white",
            "luz nocturna": "scene_night_light",
            "relax": "scene_relax",
            "concentración": "scene_focus",
            "tv": "scene_tv",
        }
        for phrase, aid in defaults.items():
            self._phrase_to_action_id[phrase] = aid