"""
Detección de capacidades por modelo de bombilla.

Reemplaza la 'matriz tediosa' de pywizlight. WiZ codifica el tipo en el
moduleName que devuelve getSystemConfig, p.ej.:
  ESP01_SHRGB1C_31  -> RGB + blancos + regulable
  ESP56_SHTW3_01    -> blancos sintonizables + regulable
  ESP06_SHDW1_01    -> solo regulable
  ESP25_SOCKET_01   -> enchufe (solo on/off)

Heurística simple sobre el nombre. Cubre prácticamente todo el catálogo de consumo.
"""
from dataclasses import dataclass


@dataclass
class Capabilities:
    rgb: bool = False
    tunable_white: bool = False     # control de temperatura (Kelvin)
    dimmable: bool = True
    on_off: bool = True
    kelvin_min: int = 2700
    kelvin_max: int = 6500
    model: str | None = None

    @property
    def label(self) -> str:
        if self.rgb:
            return "RGB + Blancos"
        if self.tunable_white:
            return "Blancos"
        if self.dimmable:
            return "Regulable"
        return "On/Off"


def from_module_name(module_name: str | None) -> Capabilities:
    n = (module_name or "").upper()
    caps = Capabilities(model=module_name)

    if "SOCKET" in n or "PLUG" in n:
        caps.dimmable = False
        return caps

    if "RGB" in n:
        caps.rgb = True
        caps.tunable_white = True
        caps.dimmable = True
        caps.kelvin_min, caps.kelvin_max = 2200, 6500
    elif "TW" in n:
        caps.tunable_white = True
        caps.dimmable = True
        caps.kelvin_min, caps.kelvin_max = 2700, 6500
    elif "DW" in n:
        caps.dimmable = True
    # desconocido -> deja defaults (regulable + blancos), el bulbo aplica el modo más cercano
    elif n:
        caps.tunable_white = True

    return caps
