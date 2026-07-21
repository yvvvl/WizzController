from __future__ import annotations

from PIL import Image, ImageDraw

from core.background.tray_service import TrayService


def test_tray_icon_uses_brand_asset():
    tray = TrayService.__new__(TrayService)
    tray._Image = Image
    tray._ImageDraw = ImageDraw

    icon = tray._make_icon()

    assert icon.mode == "RGBA"
    assert icon.size == (64, 64)
    assert icon.getbbox() is not None
