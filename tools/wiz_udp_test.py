r"""Test directo UDP para WiZ local.

Uso:
  python tools\wiz_udp_test.py 192.168.1.4 on
  python tools\wiz_udp_test.py 192.168.1.4 off
  python tools\wiz_udp_test.py 192.168.1.4 bri 80
  python tools\wiz_udp_test.py 192.168.1.4 white 2700
  python tools\wiz_udp_test.py 192.168.1.4 rgb 255 0 0
  python tools\wiz_udp_test.py 192.168.1.4 pilot
  python tools\wiz_udp_test.py 192.168.1.4 config

No depende de Flet ni pywizlight.
"""
from __future__ import annotations

import json
import socket
import sys
import time

PORT = 38899


def send(ip: str, method: str, params: dict, wait: float = 0.8) -> None:
    msg = {"id": 1, "method": method, "params": params}
    data = json.dumps(msg, separators=(",", ":")).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(wait)
    try:
        print(f">> {ip}:{PORT} {data.decode()}")
        sock.sendto(data, (ip, PORT))
        try:
            resp, addr = sock.recvfrom(4096)
            print(f"<< {addr} {resp.decode(errors='replace')}")
        except socket.timeout:
            print("<< timeout esperando respuesta; mira físicamente si cambió")
    finally:
        sock.close()


def query(ip: str, method: str, wait: float = 1.0) -> None:
    send(ip, method, {}, wait=wait)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2

    ip = argv[1]
    cmd = argv[2].lower()

    if cmd == "on":
        send(ip, "setPilot", {"state": True})
    elif cmd == "off":
        send(ip, "setPilot", {"state": False})
    elif cmd == "bri":
        pct = max(10, min(100, int(argv[3])))
        send(ip, "setPilot", {"state": True, "dimming": pct})
    elif cmd == "white":
        kelvin = max(1000, min(10000, int(argv[3])))
        send(ip, "setPilot", {"state": True, "temp": kelvin})
    elif cmd == "rgb":
        if len(argv) < 6:
            print("Uso: rgb R G B")
            return 2
        r, g, b = [max(0, min(255, int(x))) for x in argv[3:6]]
        send(ip, "setPilot", {"state": True, "r": r, "g": g, "b": b})
    elif cmd == "pilot":
        query(ip, "getPilot")
    elif cmd == "config":
        query(ip, "getSystemConfig")
    else:
        print(f"Comando desconocido: {cmd}")
        print(__doc__)
        return 2

    time.sleep(0.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
