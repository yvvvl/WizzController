import asyncio
import logging
import socket
import json
import time
from typing import Dict, Optional, Any
import threading
from concurrent.futures import ThreadPoolExecutor
from core.discovery import BulbDiscovery
from config.bulbs_manager import BulbsManager

class LightManager:
    def __init__(self) -> None:
        self.bulbs_manager = BulbsManager()
        self.selected_bulb: Optional[Dict[str, Any]] = None
        
        # Callbacks para actualizar la UI
        self.on_state_update = None 
        
        # Socket 1: PARA ENVIAR COMANDOS (Rápido, Fire & Forget)
        self.sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_cmd.setblocking(False)

        # Loop de envío
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="wizz_bg")
        self._loop = asyncio.new_event_loop()
        self._start_background_loop()
        
        # Loop de Monitoreo (Sync)
        self._monitor_running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _start_background_loop(self):
        def run_loop():
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        threading.Thread(target=run_loop, daemon=True).start()

    # --- MONITOR DE SINCRONIZACIÓN ---
    def _monitor_loop(self):
        """
        Consulta el estado usando un SOCKET INDEPENDIENTE.
        Esto evita que las respuestas de 'setPilot' (comandos) se mezclen
        con las de 'getPilot' (estado).
        """
        # Socket 2: EXCLUSIVO PARA ESCUCHAR (Con timeout)
        monitor_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        monitor_sock.settimeout(1.0) # Esperar máx 1s la respuesta

        while self._monitor_running:
            ip = self._get_ip()
            if ip and self.on_state_update:
                try:
                    # 1. Preguntar estado
                    msg = json.dumps({"method": "getPilot", "params": {}}).encode()
                    monitor_sock.sendto(msg, (ip, 38899))
                    
                    # 2. Esperar respuesta (Bloqueante pero seguro en este hilo)
                    data, _ = monitor_sock.recvfrom(4096)
                    resp = json.loads(data.decode())
                    
                    if "result" in resp:
                        state = resp["result"]
                        # Validar que sea un estado real y no un "success: true"
                        if "dimming" in state or "temp" in state or "r" in state:
                            self.on_state_update(state)
                            
                except socket.timeout:
                    pass # La bombilla no respondió a tiempo, normal.
                except Exception as e:
                    # Errores puntuales de red se ignoran para mantener el loop vivo
                    pass
            
            # Frecuencia de actualización (1.0s es buen balance fluidez/red)
            time.sleep(1.0)

    def set_callback(self, func):
        self.on_state_update = func

    # --- SETUP ---
    def startup_sequence(self) -> None:
        saved = self.bulbs_manager.get_bulbs()
        if saved:
            ip = next(iter(saved))
            self.selected_bulb = saved[ip]
        else:
            self.scan_and_register()

    def scan_and_register(self):
        asyncio.run_coroutine_threadsafe(self._async_scan(), self._loop)

    async def _async_scan(self):
        try:
            bulbs = await BulbDiscovery.discover_bulbs()
            if bulbs:
                self.selected_bulb = bulbs[0]
                self.bulbs_manager.add_bulb(bulbs[0])
        except Exception: pass

    def _get_ip(self):
        if self.selected_bulb: return self.selected_bulb.get("ip")
        return None

    # --- COMANDOS UDP (Usan sock_cmd) ---
    def _send_raw_udp(self, params: dict):
        ip = self._get_ip()
        if not ip: return
        payload = {"method": "setPilot", "params": params}
        try:
            msg = json.dumps(payload).encode('utf-8')
            self.sock_cmd.sendto(msg, (ip, 38899))
        except Exception: pass

    def turn_on(self): self._send_raw_udp({"state": True})
    def turn_off(self): self._send_raw_udp({"state": False})
    
    def set_color(self, rgb: tuple[int, int, int], warm_white: int = 0):
        r, g, b = rgb
        params = {"r": r, "g": g, "b": b, "state": True}
        if warm_white > 0: params["w"] = warm_white
        self._send_raw_udp(params)

    def set_brightness(self, val: int):
        self._send_raw_udp({"dimming": max(10, val), "state": True})

    def set_temperature(self, kelvin: int):
        self._send_raw_udp({"temp": int(kelvin), "state": True})

    # Compatibilidad
    def get_bulb_details_sync(self, ip=None): return {}
    def list_bulbs(self): return self.bulbs_manager.get_bulbs()
    def select_bulb_by_ip(self, ip):
        if ip in self.bulbs_manager.get_bulbs():
            self.selected_bulb = self.bulbs_manager.get_bulbs()[ip]
            return True
        return False
    def set_bulb_name(self, ip, name): self.bulbs_manager.set_bulb_name(ip, name)
    def get_bulb_name(self, ip): return self.bulbs_manager.get_bulb_name(ip)
    def discover_and_register_all(self, timeout=3): return []
    def start_state_monitor(self, interval_sec=2.0): pass 
    def get_cached_state(self): return None