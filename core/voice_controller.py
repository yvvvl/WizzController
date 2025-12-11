import os
import threading
import queue
import sounddevice as sd
import numpy as np
import re
import time
from collections import Counter
from faster_whisper import WhisperModel
import webrtcvad 

from config.voice_manager import VoiceManager
from core.voice_vocab import COLOR_MAP, TEMP_MAP, SCENE_KEYWORDS

class VoiceController:
    def __init__(self, light_controller):
        self.light = light_controller
        self.manager = VoiceManager()
        
        self.running = False
        self.listening = False
        self.thread = None
        
        # Rastreador de palabras desconocidas
        self.unknown_counts = Counter()
        
        print("[Voice] Cargando cerebro Whisper (Modelo BASE)...")
        try:
            self.model = WhisperModel("base", device="cpu", compute_type="int8")
        except:
            self.model = WhisperModel("base", device="cpu", compute_type="float32")

        # --- CAMBIO CRÍTICO AQUÍ ---
        # Nivel 1: Muy sensible. Detecta voz baja, rápida y modismos.
        # Antes estaba en 3 (que filtra demasiado).
        self.vad = webrtcvad.Vad(1) 
        
        # Contexto expandido para español chileno/latino
        self.vocab_prompt = (
            "Wizz, computadora, enciende, apaga, luz, brillo, intensidad, "
            "sube, baja, cambia, pon, color, rojo, azul, verde, blanco, "
            "escena, oceano, cine, fiesta, relax, al tiro, po, cachai, wea, bájale, súbele."
        )
        
        self.samplerate = 16000
        self.frame_duration = 30
        self.chunk_size = int(self.samplerate * self.frame_duration / 1000)
        
        self.on_status_change = None
        self.on_raw_text = None
        self.on_command_recognized = None
        self.on_unknown_detected = None
        self.device = None 

    def get_input_devices(self):
        try:
            devices = sd.query_devices()
            return [{"id": i, "name": f"{i}: {d['name']}"} for i, d in enumerate(devices) if d['max_input_channels'] > 0]
        except: return []

    def change_device(self, device_id):
        self.device = device_id
        if self.running:
            self.running = False
            self.start()

    def set_callbacks(self, on_status=None, on_text=None, on_command=None, on_unknown=None):
        if on_status: self.on_status_change = on_status
        if on_text: self.on_raw_text = on_text
        if on_command: self.on_command_recognized = on_command
        if on_unknown: self.on_unknown_detected = on_unknown

    def _notify_status(self, status): 
        if self.on_status_change: self.on_status_change(status)

    def toggle_listening(self):
        if not self.running: self.start()
        else:
            self.listening = not self.listening
            self._notify_status("listening" if self.listening else "paused")

    def start(self):
        if self.running: return
        self.running = True
        self.listening = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        self._notify_status("listening")

    def _process_loop(self):
        buffer = []
        is_speech = False
        silence_frames = 0
        pre_buffer = [] 
        
        with sd.InputStream(samplerate=self.samplerate, blocksize=self.chunk_size, 
                          device=self.device, dtype='int16', channels=1) as stream:
            while self.running:
                if not self.listening:
                    time.sleep(0.1)
                    continue
                
                read_data, _ = stream.read(self.chunk_size)
                audio_frame = read_data.tobytes()
                
                try: 
                    active = self.vad.is_speech(audio_frame, self.samplerate)
                except: 
                    active = False

                if active:
                    if not is_speech:
                        is_speech = True
                        buffer = pre_buffer[:]
                        pre_buffer = []
                    buffer.append(audio_frame)
                    silence_frames = 0
                else:
                    if is_speech:
                        buffer.append(audio_frame)
                        silence_frames += 1
                        # Esperamos un poco más (30 frames ~900ms) para no cortar si haces una pausa al hablar
                        if silence_frames > 30: 
                            self._transcribe_and_execute(b''.join(buffer))
                            buffer = []
                            is_speech = False
                            silence_frames = 0
                    else:
                        pre_buffer.append(audio_frame)
                        if len(pre_buffer) > 15: pre_buffer.pop(0)

    def _transcribe_and_execute(self, audio_data):
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        segments, _ = self.model.transcribe(
            audio_np, 
            beam_size=5, 
            language="es", 
            initial_prompt=self.vocab_prompt,
            condition_on_previous_text=False
        )
        full_text = " ".join([s.text for s in segments]).strip().lower()
        
        if not full_text: return
        full_text = re.sub(r'[.,¡!¿?;:]', '', full_text).strip()
        
        print(f"[Whisper] Oído: '{full_text}'")
        
        # Corrección fonética manual
        corrected_text = self._phonetic_correction(full_text)
        if corrected_text != full_text:
            if self.on_raw_text: self.on_raw_text(f"{full_text} -> {corrected_text}")
        else:
            if self.on_raw_text: self.on_raw_text(full_text)
        
        executed = self._analyze_smart_command(corrected_text)
        
        if not executed:
            if len(full_text.split()) <= 6: 
                self.unknown_counts[full_text] += 1
                if self.on_unknown_detected:
                    self.on_unknown_detected(self.get_frequent_unknowns())

    def get_frequent_unknowns(self):
        return [w for w, c in self.unknown_counts.most_common(10) if c >= 2]

    def _phonetic_correction(self, text):
        replacements = {
            "encién de": "enciende", "escendrá": "enciende la", "escendra": "enciende la",
            "camel": "cambia el", "kamel": "cambia el", "su albrío": "sube el brillo",
            "paja": "baja", "pasa": "baja", "bájale": "baja el brillo", "súbele": "sube el brillo",
            "wise": "wizz", "wish": "wizz", "huesa": "wizz", "juice": "wizz", "güis": "wizz"
        }
        for error, fix in replacements.items():
            if error in text: text = text.replace(error, fix)
        return text

    def _analyze_smart_command(self, text):
        # 1. Wake Word
        wake_words = self.manager.get_wake_words()
        triggered = False
        if not wake_words: triggered = True
        else:
            for ww in wake_words:
                if ww in text:
                    triggered = True
                    text = text.replace(ww, "").strip()
                    break
        
        if not triggered: return False

        # 2. Multicomandos
        sub_commands = re.split(r'\s+(?:y|luego|despues|entonces)\s+', text)
        any_executed = False
        
        for sub_cmd in sub_commands:
            if self._execute_single_instruction(sub_cmd.strip()):
                any_executed = True
                
        return any_executed

    def _execute_single_instruction(self, text):
        if not text: return False
        
        # A. Comandos de Usuario
        user_cmds = self.manager.get_commands()
        for cmd in user_cmds:
            phrases = [p.strip() for p in cmd["phrases"].split(",")]
            for p in phrases:
                if p in text:
                    self._execute_action(cmd["action"])
                    self._notify_action(text, f"Personal: {cmd['desc']}")
                    return True

        # B. Brillo (Soporte para "bájale", "súbele")
        if any(w in text for w in ["sube", "aumenta", "mas", "más", "súbele"]):
            self._execute_action("brightness_up"); return True
        if any(w in text for w in ["baja", "disminuye", "menos", "bájale"]):
            self._execute_action("brightness_down"); return True
        
        bri_match = re.search(r"(\d+)\s*%", text)
        if bri_match:
            self.light.set_brightness(int(bri_match.group(1))); return True

        # C. Colores/Temps/Escenas
        for c, rgb in COLOR_MAP.items():
            if c in text: self.light.set_rgb(*rgb); return True
        for t, k in TEMP_MAP.items():
            if t in text: self.light.set_white(k); return True
        for s_name, s_id in SCENE_KEYWORDS.items():
            if s_name in text: self.light.set_scene(s_id); return True

        # D. Power
        if any(w in text for w in ["enciende", "prende", "on"]):
            self.light.turn_on(); return True
        if any(w in text for w in ["apaga", "off"]):
            self.light.turn_off(); return True
            
        return False

    def _notify_action(self, cmd, action):
        if self.on_command_recognized: self.on_command_recognized(cmd, action)

    def _execute_action(self, action_id):
        try:
            curr = self.light.get_state().get("brightness", 100)
            if action_id == "turn_on": self.light.turn_on()
            elif action_id == "turn_off": self.light.turn_off()
            elif action_id == "toggle": self.light.toggle()
            elif action_id == "brightness_up": self.light.set_brightness(min(100, curr + 25))
            elif action_id == "brightness_down": self.light.set_brightness(max(10, curr - 25))
            elif action_id.startswith("set_color_"):
                parts = action_id.split("_")
                if len(parts) >= 5: self.light.set_rgb(int(parts[2]), int(parts[3]), int(parts[4]))
        except: pass