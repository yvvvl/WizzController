"""
Transporte UDP nativo para WiZ (protocolo LOCAL, puerto 38899).

Cubre TODO el protocolo local sin bloquear:
  - Escritura  (setPilot): fire-and-forget, instantáneo.
  - Lectura    (getPilot / getSystemConfig / getModelConfig): request/response
                con Future + timeout. No frena el control.
  - Discovery  (registration broadcast).

Un solo socket reutilizable para todo. Las respuestas se correlacionan por
(ip, method) porque las bombillas WiZ devuelven el campo "method" en la respuesta.
"""
import asyncio
import json
import socket
import logging

WIZ_PORT = 38899
BROADCAST = "255.255.255.255"


class WizProtocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self._futures: dict[tuple[str, str], asyncio.Future] = {}
        self.discovered: dict[str, dict] = {}   # ip -> result de registration

    # --- ciclo asyncio ---
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        ip = addr[0]
        try:
            msg = json.loads(data.decode())
        except Exception:
            return
        method = msg.get("method")
        result = msg.get("result")

        if method == "registration" and isinstance(result, dict):
            self.discovered[ip] = result

        fut = self._futures.get((ip, method))
        if fut and not fut.done():
            fut.set_result(result if isinstance(result, dict) else {})

    def error_received(self, exc):
        logging.debug(f"[WiZ] error_received: {exc}")

    # --- envío base ---
    def _send(self, ip: str, obj: dict) -> None:
        if not self.transport:
            return
        try:
            self.transport.sendto(json.dumps(obj).encode(), (ip, WIZ_PORT))
        except Exception as e:
            logging.debug(f"[WiZ] send {ip}: {e}")

    # --- escritura (camino caliente, sin esperas) ---
    def send_pilot(self, ip: str, params: dict) -> None:
        self._send(ip, {"id": 1, "method": "setPilot", "params": params})

    # --- discovery ---
    def send_registration(self, local_ip: str) -> None:
        self._send(BROADCAST, {
            "method": "registration",
            "params": {"phoneMac": "AAAAAAAAAAAA", "register": False,
                       "phoneIp": local_ip, "id": "1"},
        })

    # --- lectura (con respuesta) ---
    async def query(self, ip: str, method: str, loop, timeout: float = 1.0) -> dict | None:
        key = (ip, method)
        fut = loop.create_future()
        self._futures[key] = fut
        self._send(ip, {"method": method, "params": {}})
        try:
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._futures.pop(key, None)


async def create_endpoint(loop: asyncio.AbstractEventLoop):
    transport, protocol = await loop.create_datagram_endpoint(
        WizProtocol, family=socket.AF_INET, allow_broadcast=True,
    )
    return transport, protocol


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "0.0.0.0"
    finally:
        s.close()
