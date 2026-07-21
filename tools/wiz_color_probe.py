from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    
    
from core.wiz_color import display_rgb_to_wiz_channels


def parse_hex(value: str) -> tuple[int, int, int]:
    raw = value.strip().lstrip("#")
    if len(raw) != 6:
        raise ValueError("Usa un HEX de seis dígitos, por ejemplo FFAD9E")
    return tuple(int(raw[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(description="Muestra el payload WiZ RGBTW para un color sRGB.")
    parser.add_argument("--hex", default="FFAD9E", help="Color sRGB de seis dígitos")
    args = parser.parse_args()
    rgb = parse_hex(args.hex)
    mapped = display_rgb_to_wiz_channels(rgb)
    print(f"Objetivo de pantalla: #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}")
    print("setPilot RGB crudo anterior:", json.dumps({"r": rgb[0], "g": rgb[1], "b": rgb[2]}))
    print("setPilot WiZ RGBTW:", json.dumps(mapped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
