from __future__ import annotations

import colorsys
from typing import Any

import flet as ft

from config.favorites_manager import FavoritesManager
from core import wiz_scenes
from localization import (
    LocalizationManager,
    translated_favorite_name,
    translated_scene_name,
)
from ui.scene_visuals import scene_color, scene_icon
from ui.responsive import PANEL_BREAKPOINTS, Viewport, dialog_dimensions
from ui.theme import Theme, mounted, supdate


RGB_SWATCHES = [
    ("color.name.red", "#ff0000"), ("color.name.orange", "#ff7f00"), ("color.name.yellow", "#ffd000"),
    ("color.name.green", "#00ff40"), ("color.name.cyan", "#00d5ff"), ("color.name.blue", "#0055ff"),
    ("color.name.violet", "#7f00ff"), ("color.name.magenta", "#ff00cc"), ("color.name.pink", "#ff4fa3"),
]

WHITE_PRESETS = [
    (2200, "white.name.candle"),
    (2700, "white.name.warm"),
    (4000, "white.name.neutral"),
    (5000, "white.name.daylight"),
    (6500, "white.name.cool"),
]


def _parse_rgb(hex_color: str) -> tuple[int, int, int] | None:
    h = str(hex_color or "").strip().lstrip("#")
    if len(h) != 6:
        return None
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


def _hex_from_hsv(h: int, s: int, v: int) -> str:
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, max(0, min(100, s)) / 100.0, max(0, min(100, v)) / 100.0)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def _hsv_from_hex(hex_color: str) -> tuple[int, int, int]:
    rgb = _parse_rgb(hex_color) or (255, 0, 0)
    h, s, v = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    return round(h * 360), round(s * 100), round(v * 100)


class FavoritesPanel(ft.Column):
    def __init__(self, wiz, i18n=None):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.i18n = i18n or LocalizationManager(preference="es")
        self.manager = FavoritesManager()
        self._viewport = Viewport(900, 720)
        self._cards: list[ft.Container] = []
        self._build()

    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def set_language(self, language: str | None = None) -> None:
        self._build()
        if mounted(self):
            supdate(self)

    def _build(self):
        self.manager.seed_defaults()
        new_btn = ft.OutlinedButton(
            self._t("favorites.new"),
            icon=ft.Icons.ADD_ROUNDED,
            style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
            on_click=lambda e: self._new_dialog(),
        )
        self.header = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(self._t("favorites.title"), style=Theme.H1),
                            ft.Text(self._t("favorites.subtitle"), color=Theme.MUTED, size=13),
                        ],
                        spacing=2,
                    ),
                    col={"xs": 12, "sm": 8},
                ),
                ft.Container(content=new_btn, col={"xs": 12, "sm": 4}, alignment=ft.Alignment.CENTER_RIGHT),
            ],
        )
        self.grid = ft.ResponsiveRow(breakpoints=PANEL_BREAKPOINTS, spacing=12, run_spacing=12)
        self.controls = [self.header, self.grid]
        self._render()

    def _render(self):
        self.manager = FavoritesManager()
        favs = self.manager.get_favorites()
        self.grid.controls.clear()
        self._cards.clear()
        if not favs:
            self.grid.controls.append(
                ft.Container(
                    col={"xs": 12},
                    padding=32,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        [ft.Icon(ft.Icons.STAR_BORDER_ROUNDED, color=Theme.MUTED, size=38), ft.Text(self._t("favorites.empty"), color=Theme.MUTED)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        else:
            for fav in favs:
                self.grid.controls.append(self._card(fav))
        supdate(self.grid)

    def _fav_visual(self, fav: dict[str, Any]) -> tuple[str, Any, str]:
        ftype = fav.get("type")
        value = fav.get("value")
        if ftype == "rgb":
            return str(value), ft.Icons.PALETTE_ROUNDED, str(value).upper()
        if ftype == "white":
            return "#fbbf24", ft.Icons.LIGHT_MODE_ROUNDED, f"{value}K"
        if ftype == "scene":
            sid = int(value.get("sceneId", 18) if isinstance(value, dict) else value)
            sc = wiz_scenes.get(sid)
            fallback = f"{self._t('favorites.scene')} {sid}"
            return scene_color(sid, "#8b5cf6"), scene_icon(sid), translated_scene_name(self.i18n, sid, sc.name if sc else fallback)
        if ftype == "brightness":
            return Theme.ACCENT, ft.Icons.BRIGHTNESS_6_ROUNDED, f"{value}%"
        return Theme.PRIMARY, ft.Icons.STAR_ROUNDED, str(value)

    def _card(self, fav: dict):
        color, icon, subtitle = self._fav_visual(fav)
        card = ft.Container(
            col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
            padding=14,
            height=136,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
            on_click=lambda e, f=fav: self._apply(f),
            ink=True,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(icon, color="white", size=20),
                                width=42,
                                height=42,
                                border_radius=13,
                                bgcolor=color,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Container(expand=True),
                            ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Theme.PRIMARY, tooltip=self._t("favorites.edit"), icon_size=18, on_click=lambda e, f=fav: self._edit_dialog(f)),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, tooltip=self._t("favorites.delete"), icon_size=18, on_click=lambda e, uid=fav.get("id"): self._delete(uid)),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(translated_favorite_name(self.i18n, fav) or self._t("color_studio.favorite_default"), color=Theme.TEXT, weight=ft.FontWeight.W_600, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(subtitle, color=Theme.MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=2,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )
        self._cards.append(card)
        return card

    def _apply(self, fav: dict):
        if hasattr(self.wiz, "apply_favorite"):
            self.wiz.apply_favorite(fav)
            return
        ftype = fav.get("type")
        value = fav.get("value")
        if ftype == "rgb":
            rgb = _parse_rgb(value)
            if rgb:
                self.wiz.set_rgb(*rgb)
        elif ftype == "white":
            self.wiz.set_white(int(value))
        elif ftype == "brightness":
            self.wiz.set_brightness(int(value))
        elif ftype == "scene":
            self.wiz.set_scene(int(value.get("sceneId", 1)), value.get("speed") if isinstance(value, dict) else None)

    def _delete(self, uid: str):
        self.manager.remove_favorite(uid)
        self._render()

    def _new_dialog(self):
        self._favorite_dialog()

    def _edit_dialog(self, fav: dict):
        self._favorite_dialog(fav)

    def _kelvin_range(self) -> tuple[int, int]:
        try:
            lo, hi = self.wiz.get_kelvin_range()
            return int(lo), int(hi)
        except Exception:
            return 2200, 6500

    def _kelvin_from_pct(self, pct: int) -> int:
        lo, hi = self._kelvin_range()
        return round(lo + (hi - lo) * max(0, min(100, int(pct))) / 100)

    def _pct_from_kelvin(self, kelvin: int) -> int:
        lo, hi = self._kelvin_range()
        if hi <= lo:
            return 50
        return round((max(lo, min(hi, int(kelvin))) - lo) * 100 / (hi - lo))

    def _favorite_dialog(self, fav: dict | None = None):
        if not mounted(self):
            return

        editing = fav is not None
        fav = fav or {"name": self._t("favorites.default_name"), "type": "rgb", "value": "#ff0000"}
        state = {
            "type": fav.get("type", "rgb"),
            "rgb": str(fav.get("value", "#ff0000")) if fav.get("type") == "rgb" else "#ff0000",
            "white": int(fav.get("value", 4000)) if fav.get("type") == "white" else 4000,
            "brightness": int(fav.get("value", 80)) if fav.get("type") == "brightness" else 80,
            "scene": int((fav.get("value") or {}).get("sceneId", 18)) if isinstance(fav.get("value"), dict) else int(fav.get("value", 18) if fav.get("type") == "scene" else 18),
            "speed": int((fav.get("value") or {}).get("speed", 100)) if isinstance(fav.get("value"), dict) else 100,
        }
        h, s, v = _hsv_from_hex(state["rgb"])
        state.update({"h": h, "s": s, "v": v})

        name = ft.TextField(label=self._t("favorites.name"), value=translated_favorite_name(self.i18n, fav) or self._t("favorites.default_name"), color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        kind = ft.Dropdown(
            label=self._t("favorites.type"),
            value=state["type"],
            options=[
                ft.DropdownOption(key="rgb", text=self._t("light.color")),
                ft.DropdownOption(key="white", text=self._t("light.white")),
                ft.DropdownOption(key="scene", text=self._t("favorites.wiz_scene")),
                ft.DropdownOption(key="brightness", text=self._t("light.brightness")),
            ],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
        preview = ft.Container(width=58, height=58, border_radius=18, bgcolor="#ff0000", border=ft.Border.all(1, Theme.STROKE), alignment=ft.Alignment.CENTER)
        summary = ft.Text("", color=Theme.MUTED, size=12)
        editor = ft.Column(spacing=10)

        def update_preview():
            ftype = kind.value or "rgb"
            if ftype == "rgb":
                state["rgb"] = _hex_from_hsv(int(state["h"]), int(state["s"]), int(state["v"]))
                preview.bgcolor = state["rgb"]
                preview.content = ft.Icon(ft.Icons.PALETTE_ROUNDED, color="white")
                summary.value = state["rgb"].upper()
            elif ftype == "white":
                preview.bgcolor = "#fbbf24"
                preview.content = ft.Icon(ft.Icons.LIGHT_MODE_ROUNDED, color="white")
                summary.value = f"{int(state['white'])}K · {self._pct_from_kelvin(int(state['white']))}%"
            elif ftype == "brightness":
                preview.bgcolor = Theme.ACCENT
                preview.content = ft.Icon(ft.Icons.BRIGHTNESS_6_ROUNDED, color="white")
                summary.value = self._t("favorites.brightness_value", value=int(state["brightness"]))
            else:
                sid = int(state["scene"])
                preview.bgcolor = scene_color(sid, "#8b5cf6")
                preview.content = ft.Icon(scene_icon(sid), color="white")
                sc = wiz_scenes.get(sid)
                scene_name = translated_scene_name(self.i18n, sid, sc.name if sc else self._t("favorites.scene"))
                summary.value = self._t(
                    "favorites.scene_summary",
                    scene=scene_name,
                    speed=int(state["speed"]),
                )
            supdate(preview)
            supdate(summary)

        def render_editor(e=None):
            state["type"] = kind.value or "rgb"
            editor.controls.clear()
            ftype = state["type"]

            if ftype == "rgb":
                hex_field = ft.TextField(label=self._t("favorites.hex"), value=state["rgb"], color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE, dense=True)
                hue = ft.Slider(min=0, max=359, value=state["h"], divisions=36, active_color=Theme.PRIMARY, thumb_color="white", expand=True)
                sat = ft.Slider(min=0, max=100, value=state["s"], divisions=20, active_color=Theme.ACCENT, thumb_color="white", expand=True)
                val = ft.Slider(min=10, max=100, value=max(10, state["v"]), divisions=18, active_color=Theme.WARNING, thumb_color="white", expand=True)

                def from_sliders(ev=None):
                    state["h"], state["s"], state["v"] = int(hue.value), int(sat.value), int(val.value)
                    hex_field.value = _hex_from_hsv(state["h"], state["s"], state["v"])
                    update_preview()
                    supdate(hex_field)

                def from_hex(ev=None):
                    rgb = _parse_rgb(hex_field.value)
                    if not rgb:
                        return
                    state["rgb"] = hex_field.value if str(hex_field.value).startswith("#") else "#" + str(hex_field.value)
                    state["h"], state["s"], state["v"] = _hsv_from_hex(state["rgb"])
                    hue.value, sat.value, val.value = state["h"], state["s"], state["v"]
                    update_preview()
                    supdate(hue); supdate(sat); supdate(val)

                hue.on_change = sat.on_change = val.on_change = from_sliders
                hex_field.on_submit = from_hex
                swatches = ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[
                    ft.Container(width=32, height=32, border_radius=16, bgcolor=c, tooltip=self._t(key), border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white")), on_click=lambda ev, col=c, hf=hex_field: (setattr(hf, "value", col), from_hex()))
                    for key, c in RGB_SWATCHES
                ])
                editor.controls.extend([swatches, hex_field, ft.Text(self._t("favorites.hue"), style=Theme.LABEL), hue, ft.Text(self._t("favorites.saturation"), style=Theme.LABEL), sat, ft.Text(self._t("favorites.lightness"), style=Theme.LABEL), val])

            elif ftype == "white":
                pct = self._pct_from_kelvin(int(state["white"]))
                label = ft.Text("", color=Theme.TEXT, weight=ft.FontWeight.W_600)
                slider = ft.Slider(min=0, max=100, value=pct, divisions=100, active_color=Theme.WARNING, thumb_color="white", expand=True)

                def set_white_from_pct(ev=None):
                    state["white"] = self._kelvin_from_pct(int(slider.value))
                    label.value = f"{int(slider.value)}% · {state['white']}K"
                    update_preview()
                    supdate(label)

                slider.on_change = set_white_from_pct
                def preset_white(k: int, sl=slider):
                    state["white"] = int(k)
                    sl.value = self._pct_from_kelvin(int(k))
                    set_white_from_pct()
                    supdate(sl)

                buttons = ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[
                    ft.OutlinedButton(self._t(key), style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)), on_click=lambda ev, k=k: preset_white(k))
                    for k, key in WHITE_PRESETS
                ])
                set_white_from_pct()
                editor.controls.extend([label, slider, buttons])

            elif ftype == "scene":
                dd = ft.Dropdown(
                    label=self._t("favorites.scene"),
                    value=str(state["scene"]),
                    options=[ft.DropdownOption(key=str(sid), text=f"{sid} · {translated_scene_name(self.i18n, sid, sc.name)}") for sid, sc in wiz_scenes.CATALOG.items()],
                    color=Theme.TEXT,
                    bgcolor=Theme.BG,
                    border_color=Theme.STROKE,
                )
                speed_label = ft.Text(
                    self._t("favorites.speed_value", value=state["speed"]),
                    color=Theme.TEXT,
                    weight=ft.FontWeight.W_600,
                )
                speed = ft.Slider(min=20, max=200, value=state["speed"], divisions=18, active_color=Theme.ACCENT, thumb_color="white", expand=True)

                def scene_changed(ev=None):
                    state["scene"] = int(dd.value or 18)
                    update_preview()

                def speed_changed(ev=None):
                    state["speed"] = int(speed.value)
                    speed_label.value = self._t("favorites.speed_value", value=state["speed"])
                    update_preview()
                    supdate(speed_label)

                dd.on_change = scene_changed
                speed.on_change = speed_changed
                editor.controls.extend([dd, speed_label, speed])

            else:
                label = ft.Text(
                    self._t("favorites.brightness_value", value=state["brightness"]),
                    color=Theme.TEXT,
                    weight=ft.FontWeight.W_600,
                )
                slider = ft.Slider(min=10, max=100, value=state["brightness"], divisions=18, active_color=Theme.ACCENT, thumb_color="white", expand=True)

                def bri_changed(ev=None):
                    state["brightness"] = int(slider.value)
                    label.value = self._t("favorites.brightness_value", value=state["brightness"])
                    update_preview()
                    supdate(label)

                slider.on_change = bri_changed
                editor.controls.extend([label, slider])

            update_preview()
            supdate(editor)

        kind.on_change = render_editor
        render_editor()

        def save(e):
            ftype = kind.value or "rgb"
            if ftype == "rgb":
                val: object = state["rgb"]
                icon = "PALETTE"
            elif ftype == "white":
                val = int(state["white"])
                icon = "LIGHT_MODE"
            elif ftype == "brightness":
                val = int(state["brightness"])
                icon = "BRIGHTNESS_6"
            else:
                val = {"sceneId": int(state["scene"]), "speed": int(state["speed"])}
                icon = "AUTO_AWESOME"
            if editing:
                self.manager.update_favorite(fav.get("id"), name.value, ftype, val, fav.get("icon", icon))
            else:
                self.manager.add_favorite(name.value, ftype, val, icon)
            self.page.pop_dialog()
            self._render()

        dialog_w, dialog_h = dialog_dimensions(self, 560, 560)
        identity = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=preview, col={"xs": 12, "sm": 2}, alignment=ft.Alignment.CENTER),
                ft.Container(content=ft.Column([name, summary], spacing=6), col={"xs": 12, "sm": 10}),
            ],
        )
        dlg = ft.AlertDialog(
            title=ft.Text(self._t("favorites.edit_title") if editing else self._t("favorites.new_title"), color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=ft.Container(
                width=dialog_w,
                height=dialog_h,
                content=ft.Column(
                    [
                        identity,
                        kind,
                        ft.Divider(height=8, color=Theme.STROKE),
                        ft.Container(content=editor, expand=True),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[
                ft.TextButton(self._t("favorites.cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton(self._t("favorites.save"), bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        viewport = Viewport(max(280.0, float(width)), max(320.0, float(height)))
        mode_changed = viewport.mode != self._viewport.mode
        self._viewport = viewport
        if mode_changed:
            self.spacing = 14 if viewport.compact else 18
            padding = 12 if viewport.compact else 14
            for card in self._cards:
                card.padding = padding
            if update:
                supdate(self)

    def sync_state(self, state: dict):
        # No necesita refrescar en cada tick de slider; evita CPU extra.
        pass
