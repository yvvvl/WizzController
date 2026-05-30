"""Adaptador opcional a pywizlight.

Uso intencional:
- discovery/capabilities/fallback, fuera del hot path;
- NO usar para cada tick de slider, porque pywizlight espera respuesta y reintenta.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable

_LOG = logging.getLogger(__name__)


async def discover_with_pywizlight(
    broadcast_addresses: Iterable[str],
    *,
    wait_time: float = 1.25,
) -> list[dict[str, Any]]:
    try:
        from pywizlight import discovery  # type: ignore
    except Exception as exc:
        _LOG.debug("pywizlight no disponible: %s", exc)
        return []

    found: dict[str, dict[str, Any]] = {}

    async def one(addr: str) -> None:
        try:
            bulbs = await asyncio.wait_for(
                discovery.find_wizlights(wait_time=wait_time, broadcast_address=addr),
                timeout=wait_time + 0.75,
            )
        except Exception as exc:
            _LOG.debug("pywizlight discovery %s falló: %s", addr, exc)
            return

        for bulb in bulbs:
            ip = getattr(bulb, "ip_address", None)
            mac = getattr(bulb, "mac_address", None)
            if ip:
                found[str(ip)] = {"ip": str(ip), "mac": mac, "source": "pywizlight"}

    await asyncio.gather(*(one(addr) for addr in set(broadcast_addresses)), return_exceptions=True)
    return list(found.values())


async def read_pywizlight_features(ip: str, *, timeout: float = 1.5) -> dict[str, Any] | None:
    """Lee capacidades vía pywizlight bajo timeout externo.

    Útil como fallback/manual. No lo metas en sliders ni cambios continuos.
    """
    try:
        from pywizlight import wizlight  # type: ignore
    except Exception:
        return None

    light = wizlight(ip)
    try:
        bulb_type = await asyncio.wait_for(light.get_bulbtype(), timeout=timeout)
        features = getattr(bulb_type, "features", None)
        kelvin = getattr(bulb_type, "kelvin_range", None)
        return {
            "name": getattr(bulb_type, "name", None),
            "brightness": getattr(features, "brightness", None) if features else None,
            "color": getattr(features, "color", None) if features else None,
            "color_tmp": getattr(features, "color_tmp", None) if features else None,
            "effect": getattr(features, "effect", None) if features else None,
            "kelvin_min": getattr(kelvin, "min", None) if kelvin else None,
            "kelvin_max": getattr(kelvin, "max", None) if kelvin else None,
        }
    except Exception as exc:
        _LOG.debug("pywizlight features %s falló: %s", ip, exc)
        return None
    finally:
        try:
            await light.async_close()
        except Exception:
            pass
