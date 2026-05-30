"""
Transporte UDP local para WiZ.

Objetivo:
- camino caliente (setPilot) fire-and-forget, sin esperar ACK;
- lectura/probing con timeout corto y retry controlado;
- discovery por broadcast global + broadcast por interfaz;
- utilidades para escaneo LAN sin depender obligatoriamente de psutil.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import socket
import time
from itertools import count
from typing import Any, Iterable

WIZ_PORT = 38899
BROADCAST = "255.255.255.255"

_LOG = logging.getLogger(__name__)


def _dump(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class WizProtocol(asyncio.DatagramProtocol):
    """Un solo socket UDP reutilizable para discovery, control y lectura."""

    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self._futures: dict[tuple[str, str], asyncio.Future] = {}
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._ids = count(1)

        # ip -> datos reportados por registration / syncPilot
        self.discovered: dict[str, dict[str, Any]] = {}
        self.last_pilot: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------ #
    # asyncio.DatagramProtocol
    # ------------------------------------------------------------------ #
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        ip = addr[0]
        try:
            msg = json.loads(data.decode("utf-8", errors="ignore"))
        except Exception:
            return

        method = msg.get("method")
        result = msg.get("result")
        params = msg.get("params")

        if method == "registration" and isinstance(result, dict):
            self.discovered[ip] = {
                **result,
                "ip": ip,
                "source": "native-registration",
                "seen_at": time.time(),
            }
        elif method in ("syncPilot", "syncBroadcastPilot") and isinstance(params, dict):
            self.last_pilot[ip] = params
            mac = params.get("mac")
            if mac:
                prev = self.discovered.get(ip, {})
                self.discovered[ip] = {
                    **prev,
                    "ip": ip,
                    "mac": mac,
                    "source": "native-sync",
                    "seen_at": time.time(),
                }

        if isinstance(method, str):
            fut = self._futures.get((ip, method))
            if fut and not fut.done():
                if "error" in msg:
                    fut.set_result(None)
                else:
                    fut.set_result(result if isinstance(result, dict) else {})

    def error_received(self, exc):
        _LOG.debug("[WiZ] UDP error: %s", exc)

    # ------------------------------------------------------------------ #
    # Envío
    # ------------------------------------------------------------------ #
    def _send(self, ip: str, obj: dict[str, Any], port: int = WIZ_PORT) -> None:
        if not self.transport:
            return
        try:
            self.transport.sendto(_dump(obj), (ip, port))
        except Exception as e:
            _LOG.debug("[WiZ] send %s:%s failed: %s", ip, port, e)

    def send_pilot(self, ip: str, params: dict[str, Any]) -> None:
        """Camino caliente: no espera respuesta."""
        self._send(ip, {"id": next(self._ids), "method": "setPilot", "params": params})

    def send_registration(
        self,
        local_ip: str,
        broadcast_ip: str = BROADCAST,
        *,
        register: bool = False,
    ) -> None:
        self._send(
            broadcast_ip,
            {
                "id": next(self._ids),
                "method": "registration",
                "params": {
                    "phoneMac": "AAAAAAAAAAAA",
                    "register": bool(register),
                    "phoneIp": local_ip,
                    "id": "1",
                },
            },
        )

    async def query(
        self,
        ip: str,
        method: str,
        loop: asyncio.AbstractEventLoop | None = None,  # compat con firma antigua
        timeout: float = 0.9,
        params: dict[str, Any] | None = None,
        retries: int = 1,
        retry_delay: float = 0.08,
    ) -> dict[str, Any] | None:
        """Request/response con timeout corto y retry.

        WiZ a veces responde lento al primer paquete UDP. pywizlight resuelve esto
        con backoff largo; aquí hacemos solo 1 retry por defecto para no matar la UI.
        """
        if not self.transport:
            return None

        key = (ip, method)
        lock = self._locks.get(key)
        if lock is None:
            lock = self._locks[key] = asyncio.Lock()

        async with lock:
            for attempt in range(max(0, retries) + 1):
                fut = asyncio.get_running_loop().create_future()
                self._futures[key] = fut
                self._send(
                    ip,
                    {
                        "id": next(self._ids),
                        "method": method,
                        "params": params or {},
                    },
                )
                try:
                    return await asyncio.wait_for(fut, timeout=timeout)
                except asyncio.TimeoutError:
                    if attempt >= retries:
                        return None
                    await asyncio.sleep(retry_delay)
                finally:
                    # Solo borramos si el future sigue siendo el nuestro.
                    if self._futures.get(key) is fut:
                        self._futures.pop(key, None)
        return None


async def create_endpoint(loop: asyncio.AbstractEventLoop):
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: WizProtocol(),
        local_addr=("0.0.0.0", 0),
        family=socket.AF_INET,
        allow_broadcast=True,
    )
    return transport, protocol


# ---------------------------------------------------------------------- #
# Red / discovery helpers
# ---------------------------------------------------------------------- #
def _usable_ipv4(value: str | None) -> bool:
    if not value:
        return False
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return bool(ip.version == 4 and not ip.is_loopback and not ip.is_link_local and not ip.is_multicast)


def get_local_ip(target_ip: str = "8.8.8.8") -> str:
    """IP local que usaría el SO para llegar a internet/LAN.

    UDP connect no manda paquetes; solo deja que el SO elija interfaz.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((target_ip, 80))
        return s.getsockname()[0]
    except Exception:
        return "0.0.0.0"
    finally:
        s.close()


def _iter_ipv4_networks() -> Iterable[tuple[ipaddress.IPv4Network, str]]:
    """Devuelve redes IPv4 activas. psutil es opcional; hay fallback /24."""
    yielded = False

    try:
        import psutil  # type: ignore

        for addrs in psutil.net_if_addrs().values():
            for addr in addrs:
                if addr.family != socket.AF_INET:
                    continue
                ip = getattr(addr, "address", None)
                mask = getattr(addr, "netmask", None)
                if not _usable_ipv4(ip) or not mask:
                    continue
                try:
                    net = ipaddress.ip_network(f"{ip}/{mask}", strict=False)
                except ValueError:
                    continue
                if net.version == 4 and not net.is_loopback:
                    yielded = True
                    yield net, str(ip)
    except Exception:
        pass

    if not yielded:
        ip = get_local_ip()
        if _usable_ipv4(ip):
            yield ipaddress.ip_network(f"{ip}/24", strict=False), ip


def get_broadcast_addresses() -> list[str]:
    """Broadcast global + directed broadcast por interfaz."""
    out = {BROADCAST}
    for net, _ip in _iter_ipv4_networks():
        out.add(str(net.broadcast_address))
    return sorted(out)


def _ip_sort_key(ip: str) -> tuple[int, int, int, int]:
    return tuple(int(part) for part in ip.split("."))  # type: ignore[return-value]


def get_lan_scan_ips(limit: int = 512) -> list[str]:
    """IPs candidatas para escaneo UDP.

    Nunca escanea una /16 completa. Si la red es grande, usa el /24 del IP local.
    """
    seen: set[str] = set()
    local_ips: set[str] = set()

    for net, local_ip in _iter_ipv4_networks():
        local_ips.add(local_ip)
        if net.num_addresses <= limit + 2:
            hosts = net.hosts()
        else:
            hosts = ipaddress.ip_network(f"{local_ip}/24", strict=False).hosts()

        for host in hosts:
            ip = str(host)
            if ip not in local_ips:
                seen.add(ip)
            if len(seen) >= limit:
                break

    return sorted(seen, key=_ip_sort_key)
