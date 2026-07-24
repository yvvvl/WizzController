from __future__ import annotations

from .en import CATALOG as EN
from .es import CATALOG as ES

CATALOGS: dict[str, dict[str, str]] = {
    "en": EN,
    "es": ES,
}

__all__ = ["CATALOGS", "EN", "ES"]
