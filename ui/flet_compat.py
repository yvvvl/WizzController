"""Compatibilidad entre versiones de Flet.

Este proyecto usa muchos accesos a iconos vía `ft.icons.X`. En Flet 0.80+
los iconos están disponibles como `ft.Icons.X` y el módulo `ft.icons` ya no
expone todos los atributos directamente.

Este parche crea un puente para que `ft.icons.<NOMBRE>` funcione, delegando
la resolución a `ft.Icons` cuando sea necesario.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any


def patch_flet(ft_module: Any) -> None:
    """Aplica parches de compatibilidad a un módulo `flet` ya importado."""

    try:
        icons_module: ModuleType | None = getattr(ft_module, "icons", None)
        icons_proxy: Any = getattr(ft_module, "Icons", None)
    except Exception:
        return

    if icons_module is None or icons_proxy is None:
        return

    # Si la versión ya expone iconos en ft.icons, no tocamos nada.
    try:
        if hasattr(icons_module, "LIGHTBULB"):
            return
    except Exception:
        pass

    # Añadimos __getattr__ al módulo para resolver iconos dinámicamente.
    def __getattr__(name: str) -> Any:  # noqa: D401
        try:
            return getattr(icons_proxy, name)
        except AttributeError as e:
            raise AttributeError(
                f"module 'flet.icons' has no attribute {name!r} (compat patch)"
            ) from e

    def __dir__() -> list[str]:
        try:
            base = set(dir(icons_module))
        except Exception:
            base = set()
        try:
            base.update([n for n in dir(icons_proxy) if n.isupper()])
        except Exception:
            pass
        return sorted(base)

    try:
        setattr(icons_module, "__getattr__", __getattr__)
        setattr(icons_module, "__dir__", __dir__)
    except Exception:
        # Si no se puede parchear por cualquier motivo, no rompemos el arranque.
        return
