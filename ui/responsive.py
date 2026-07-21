from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Breakpoints pensados para el ancho REAL del panel (después del NavigationRail),
# no para una página web completa. Los defaults de Bootstrap hacen que una app
# desktop angosta siga usando layouts demasiado anchos.
PANEL_BREAKPOINTS: dict[str, int] = {
    "xs": 0,
    "sm": 420,
    "md": 640,
    "lg": 900,
    "xl": 1180,
    "xxl": 1400,
}


@dataclass(frozen=True)
class Viewport:
    width: float
    height: float

    @property
    def compact(self) -> bool:
        return self.width < 620

    @property
    def medium(self) -> bool:
        return 620 <= self.width < 900

    @property
    def wide(self) -> bool:
        return self.width >= 900

    @property
    def mode(self) -> str:
        if self.compact:
            return "compact"
        if self.medium:
            return "medium"
        return "wide"


def safe_number(value: Any, default: float) -> float:
    try:
        out = float(value)
        if out > 0:
            return out
    except Exception:
        pass
    return float(default)


def quantize(value: float, step: int = 8) -> int:
    """Cuantiza medidas para no repintar en cada píxel durante un resize."""
    step = max(1, int(step))
    return int(round(float(value) / step) * step)


def quantize_down(value: float, step: int = 8) -> int:
    """Cuantiza hacia abajo para que una medida nunca exceda su contenedor."""
    step = max(1, int(step))
    return int(float(value) // step) * step


def clamp_size(value: float, minimum: float, maximum: float) -> float:
    return max(float(minimum), min(float(maximum), float(value)))


def page_dimensions(control: Any, *, fallback_width: float = 1080, fallback_height: float = 720) -> tuple[float, float]:
    page = getattr(control, "page", None)
    width = safe_number(getattr(page, "width", None), fallback_width)
    height = safe_number(getattr(page, "height", None), fallback_height)
    return width, height


def dialog_dimensions(
    control: Any,
    preferred_width: float,
    preferred_height: float | None = None,
    *,
    horizontal_margin: float = 72,
    vertical_margin: float = 132,
    min_width: float = 280,
    min_height: float = 260,
) -> tuple[float, float | None]:
    """Devuelve dimensiones de diálogo que nunca desbordan el viewport actual."""
    page_w, page_h = page_dimensions(control)
    width = clamp_size(min(float(preferred_width), page_w - horizontal_margin), min_width, preferred_width)
    if preferred_height is None:
        return width, None
    height = clamp_size(min(float(preferred_height), page_h - vertical_margin), min_height, preferred_height)
    return width, height
