from __future__ import annotations

import re
import time
from typing import Iterable

import flet as ft

from config.custom_scenes_manager import CustomScenesManager
from core import wiz_scenes
from localization import LocalizationManager, translated_scene_group, translated_scene_name
from ui.theme import Theme, mounted, supdate
from ui.interaction import LocalEditGuard
from ui.responsive import PANEL_BREAKPOINTS, Viewport, dialog_dimensions
from ui.scene_visuals import scene_icon, scene_color

EO = ft.AnimationCurve.EASE_OUT


def _chunks(items: Iterable, size: int):
    row = []
    for item in items:
        row.append(item)
        if len(row) >= size:
            yield row
            row = []
    if row:
        yield row


class _Throttle:
    def __init__(self, interval: float = 0.08):
        self.interval = interval
        self.last = 0.0

    def ready(self, final: bool = False) -> bool:
        now = time.monotonic()
        if final or now - self.last >= self.interval:
            self.last = now
            return True
        return False


class ScenesPanel(ft.Column):
    """Escenas WiZ + escenas personalizadas.

    La grilla principal usa filas manuales de tarjetas con ancho calculado.
    Esto conserva el workaround estable frente al ErrorWidget gris de
    GridView/filas expandibles, mientras header y controles auxiliares sí se
    adaptan con ResponsiveRow.
    """

    CARD_W = 126
    CARD_H = 104
    CARDS_PER_ROW = 5

    def __init__(self, wiz, i18n=None):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=14, expand=True)
        self.wiz = wiz
        self.i18n = i18n or LocalizationManager(preference="es")
        self.custom = CustomScenesManager()
        self.selected_id: int | None = None
        self.selected_custom_id: str | None = None
        self.speed = 100
        self._speed_throttle = _Throttle(0.08)
        self._speed_guard = LocalEditGuard(0.90)
        self._builtin_cards: dict[int, ft.Container] = {}
        self._custom_cards: dict[str, ft.Container] = {}
        self._viewport = Viewport(900, 720)
        self._cards_per_row = self.CARDS_PER_ROW
        self._card_width = float(self.CARD_W)
        self._build()

    # ------------------------------------------------------------------ #
    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def set_language(self, language: str | None = None) -> None:
        self._build()
        self._highlight()
        if mounted(self):
            supdate(self)

    def _build(self):
        self.speed_label = ft.Text(str(self.speed), size=12, color=Theme.TEXT, text_align=ft.TextAlign.RIGHT)
        self.speed_slider = ft.Slider(
            min=20,
            max=200,
            value=self.speed,
            divisions=18,
            active_color=Theme.ACCENT,
            thumb_color="white",
            on_change=self._on_speed,
            on_change_end=self._on_speed_end,
            expand=True,
        )
        self.custom_block = ft.Column(spacing=10)
        self.builtin_block = ft.Column(spacing=10)

        self.controls = [
            self._header(),
            self._speed_card(),
            self._section_title(self._t("scenes.my_section")),
            self.custom_block,
            self._section_title(self._t("scenes.wiz_section")),
            self.builtin_block,
        ]
        self._render_custom()
        self._render_builtin_sections()

    def _header(self):
        buttons = ft.Row(
            [
                ft.OutlinedButton(
                    self._t("scenes.save_current"),
                    icon=ft.Icons.ADD_PHOTO_ALTERNATE_ROUNDED,
                    style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
                    on_click=self._capture_current_dialog,
                ),
                ft.ElevatedButton(
                    self._t("scenes.new"),
                    icon=ft.Icons.ADD_ROUNDED,
                    bgcolor=Theme.PRIMARY,
                    color="white",
                    on_click=lambda e: self._custom_dialog(),
                ),
            ],
            spacing=8,
            run_spacing=8,
            wrap=True,
            alignment=ft.MainAxisAlignment.END,
        )
        return ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(self._t("scenes.title"), style=Theme.H1),
                            ft.Text(self._t("scenes.subtitle"), color=Theme.MUTED, size=13),
                        ],
                        spacing=2,
                    ),
                    col={"xs": 12, "md": 7},
                ),
                ft.Container(content=buttons, col={"xs": 12, "md": 5}, alignment=ft.Alignment.CENTER_RIGHT),
            ],
        )

    def _speed_card(self):
        reset = ft.IconButton(
            ft.Icons.RESTART_ALT_ROUNDED,
            icon_color=Theme.MUTED,
            tooltip=self._t("scenes.reset_speed"),
            on_click=self._reset_speed,
        )
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.ResponsiveRow(
                breakpoints=PANEL_BREAKPOINTS,
                spacing=10,
                run_spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        content=ft.Row(
                            [ft.Icon(ft.Icons.SPEED_ROUNDED, color=Theme.ACCENT, size=18), ft.Text(self._t("scenes.speed_section"), style=Theme.LABEL)],
                            spacing=8,
                        ),
                        col={"xs": 12, "sm": 4},
                    ),
                    ft.Container(content=self.speed_slider, col={"xs": 9, "sm": 6}),
                    ft.Container(
                        content=ft.Row([self.speed_label, reset], spacing=2, alignment=ft.MainAxisAlignment.END),
                        col={"xs": 3, "sm": 2},
                        alignment=ft.Alignment.CENTER_RIGHT,
                    ),
                ],
            ),
        )

    def _section_title(self, text: str):
        return ft.Container(content=ft.Text(text, style=Theme.LABEL), padding=ft.Padding.only(top=4, bottom=1))

    # ------------------------------------------------------------------ #
    def _render_builtin_sections(self):
        self._builtin_cards.clear()
        self.builtin_block.controls.clear()
        for group_name, ids in wiz_scenes.GROUPS.items():
            self.builtin_block.controls.append(
                self._section_title(translated_scene_group(self.i18n, group_name).upper())
            )
            for row_ids in _chunks(ids, self._cards_per_row):
                self.builtin_block.controls.append(
                    ft.Row(spacing=10, controls=[self._scene_card(sid) for sid in row_ids])
                )
        supdate(self.builtin_block)

    def _scene_card(self, scene_id: int):
        sc = wiz_scenes.get(scene_id)
        if not sc:
            return ft.Container(width=1, height=1)
        card = ft.Container(
            key=f"sc{scene_id}",
            width=self._card_width,
            height=self.CARD_H,
            padding=10,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Icon(scene_icon(sc.id), color=scene_color(sc.id, sc.color), size=22),
                        width=38,
                        height=38,
                        border_radius=11,
                        bgcolor=ft.Colors.with_opacity(0.16, scene_color(sc.id, sc.color)),
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.30, scene_color(sc.id, sc.color))),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(
                        translated_scene_name(self.i18n, sc.id, sc.name),
                        color=Theme.TEXT,
                        size=12,
                        weight=ft.FontWeight.W_600,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        self._t("scenes.dynamic") if sc.dynamic else self._t("scenes.static"),
                        color=Theme.FAINT,
                        size=9,
                        max_lines=1,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            on_click=lambda e, s=sc: self._activate_builtin(s),
            ink=True,
            animate=ft.Animation(120, EO),
        )
        self._builtin_cards[scene_id] = card
        return card

    # ------------------------------------------------------------------ #
    def _render_custom(self):
        self.custom = CustomScenesManager()
        self._custom_cards.clear()
        self.custom_block.controls.clear()
        scenes = self.custom.get_scenes()

        if not scenes:
            self.custom_block.controls.append(
                ft.Container(
                    height=46,
                    padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                    border_radius=Theme.R_SM,
                    bgcolor=Theme.CARD,
                    border=ft.Border.all(1, Theme.STROKE),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, color=Theme.MUTED, size=16),
                            ft.Text(self._t("scenes.empty"), color=Theme.MUTED, size=12),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        else:
            for scene_row in _chunks(scenes, self._cards_per_row):
                self.custom_block.controls.append(
                    ft.Row(spacing=10, controls=[self._custom_card(scene) for scene in scene_row])
                )
        supdate(self.custom_block)

    def _custom_card(self, scene: dict):
        uid = str(scene.get("id", ""))
        mode = str(scene.get("mode", "rgb"))
        color = "#ec4899" if mode == "rgb" else "#fbbf24" if mode == "white" else "#8b5cf6"
        if mode == "rgb" and isinstance(scene.get("value"), dict):
            v = scene["value"]
            color = "#{:02x}{:02x}{:02x}".format(int(v.get("r", 255)), int(v.get("g", 0)), int(v.get("b", 0)))

        card = ft.Container(
            key=f"custom_{uid}",
            width=self._card_width,
            height=self.CARD_H,
            padding=9,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=30,
                                height=30,
                                border_radius=10,
                                bgcolor=color,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Container(expand=True),
                            ft.IconButton(
                                ft.Icons.EDIT_ROUNDED,
                                icon_color=Theme.MUTED,
                                icon_size=16,
                                width=30,
                                height=30,
                                padding=0,
                                tooltip=self._t("common.edit"),
                                on_click=lambda e, s=scene: self._custom_dialog(s),
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE_ROUNDED,
                                icon_color=Theme.ERROR,
                                icon_size=16,
                                width=30,
                                height=30,
                                padding=0,
                                tooltip=self._t("common.delete"),
                                on_click=lambda e, x=uid: self._delete_custom(x),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                    ft.Text(scene.get("name") or self._t("scenes.custom_fallback"), color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER),
                    ft.Text(self._custom_subtitle(scene), color=Theme.FAINT, size=9, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
            ),
            on_click=lambda e, s=scene: self._activate_custom(s),
            ink=True,
            animate=ft.Animation(120, EO),
        )
        self._custom_cards[uid] = card
        return card

    def _custom_subtitle(self, scene: dict) -> str:
        mode = scene.get("mode")
        v = scene.get("value") or {}
        if mode == "rgb" and isinstance(v, dict):
            return f"RGB · {v.get('dimming', 100)}%"
        if mode == "white" and isinstance(v, dict):
            return f"{v.get('temp', 4000)}K · {v.get('dimming', 100)}%"
        if mode == "scene" and isinstance(v, dict):
            return self._t(
                "scenes.scene_summary",
                scene_id=v.get("sceneId"),
                speed=v.get("speed", 100),
            )
        return str(mode or self._t("scenes.custom_type"))

    # ------------------------------------------------------------------ #
    def _activate_builtin(self, sc):
        self.wiz.set_scene(sc.id, speed=int(self.speed) if sc.dynamic else None)
        self.selected_id = sc.id
        self.selected_custom_id = None
        self._highlight()

    def _activate_custom(self, scene: dict):
        self.wiz.apply_custom_scene(scene)
        self.selected_id = None
        self.selected_custom_id = str(scene.get("id", ""))
        self._highlight()

    def _highlight(self):
        for sid, card in self._builtin_cards.items():
            active = sid == self.selected_id
            sc = wiz_scenes.get(sid)
            card.border = ft.Border.all(2 if active else 1, sc.color if active and sc else Theme.STROKE)
            card.bgcolor = Theme.CARD_HI if active else Theme.CARD
            supdate(card)
        for uid, card in self._custom_cards.items():
            active = uid == self.selected_custom_id
            card.border = ft.Border.all(2 if active else 1, Theme.PRIMARY if active else Theme.STROKE)
            card.bgcolor = Theme.CARD_HI if active else Theme.CARD
            supdate(card)

    def _emit_speed(self, final: bool = False):
        if self.selected_id is None or not self._speed_throttle.ready(final):
            return
        sc = wiz_scenes.get(self.selected_id)
        if sc and sc.dynamic:
            self.wiz.set_scene(sc.id, speed=self.speed)

    def _on_speed(self, e):
        self.speed = int(self.speed_slider.value)
        self._speed_guard.touch(self.speed, hold_seconds=0.80)
        self.speed_label.value = str(self.speed)
        supdate(self.speed_label)
        self._emit_speed(final=False)

    def _on_speed_end(self, e):
        self._speed_guard.touch(int(self.speed_slider.value), hold_seconds=1.10)
        self._emit_speed(final=True)

    def _reset_speed(self, e=None):
        self.speed = 100
        self.speed_slider.value = 100
        self.speed_label.value = "100"
        supdate(self.speed_slider)
        supdate(self.speed_label)
        self._emit_speed(final=True)

    # ------------------------------------------------------------------ #
    def _capture_current_dialog(self, e=None):
        if not mounted(self):
            return
        field = ft.TextField(label=self._t("favorites.name"), value=self._t("scenes.capture_default_name"), autofocus=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        def save(ev):
            payload = self.wiz.capture_current_scene_payload()
            self.custom.add_scene(field.value or self._t("scenes.capture_default_name"), payload["mode"], payload["value"])
            self.page.pop_dialog()
            self._render_custom()

        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(self._t("scenes.capture_title"), color=Theme.TEXT),
                bgcolor=Theme.SURFACE,
                content=field,
                actions=[
                    ft.TextButton(self._t("common.cancel"), on_click=lambda e: self.page.pop_dialog()),
                    ft.ElevatedButton(self._t("common.save"), bgcolor=Theme.PRIMARY, color="white", on_click=save),
                ],
            )
        )

    def _custom_dialog(self, scene: dict | None = None):
        if not mounted(self):
            return
        editing = scene is not None
        scene = scene or {"name": self._t("scenes.custom_fallback"), "mode": "rgb", "value": {"r": 255, "g": 0, "b": 0, "dimming": 100}}
        v = scene.get("value") or {}

        name = ft.TextField(label=self._t("favorites.name"), value=scene.get("name") or self._t("scenes.custom_fallback"), color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        mode = ft.Dropdown(
            label=self._t("common.type"),
            value=scene.get("mode", "rgb"),
            options=[
                ft.DropdownOption(key="rgb", text=self._t("scenes.type_rgb")),
                ft.DropdownOption(key="white", text=self._t("scenes.type_white")),
                ft.DropdownOption(key="scene", text=self._t("scenes.type_wiz")),
            ],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
        rgb_hex = "#ff0000"
        if isinstance(v, dict) and scene.get("mode") == "rgb":
            rgb_hex = "#{:02x}{:02x}{:02x}".format(int(v.get("r", 255)), int(v.get("g", 0)), int(v.get("b", 0)))
        default_value = rgb_hex
        if scene.get("mode") == "white" and isinstance(v, dict):
            default_value = str(v.get("temp", 4000))
        if scene.get("mode") == "scene" and isinstance(v, dict):
            default_value = str(v.get("sceneId", 18))
        value = ft.TextField(label=self._t("common.value"), value=str(default_value), hint_text="#ff0000 / 4000 / 18", color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        dimming = ft.Slider(min=10, max=100, value=int(v.get("dimming", 100) if isinstance(v, dict) else 100), divisions=18, active_color=Theme.ACCENT, thumb_color="white")
        speed = ft.Slider(min=20, max=200, value=int(v.get("speed", 100) if isinstance(v, dict) else 100), divisions=18, active_color=Theme.ACCENT, thumb_color="white")

        def save(e):
            raw = (value.value or "").strip()
            m = mode.value or "rgb"
            try:
                if m == "rgb":
                    h = raw.lstrip("#")
                    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
                        return
                    val = {"r": int(h[0:2], 16), "g": int(h[2:4], 16), "b": int(h[4:6], 16), "dimming": int(dimming.value)}
                elif m == "white":
                    val = {"temp": int(raw), "dimming": int(dimming.value)}
                else:
                    val = {"sceneId": int(raw), "speed": int(speed.value), "dimming": int(dimming.value)}
            except Exception:
                return
            if editing:
                self.custom.update_scene(scene.get("id"), name.value, m, val)
            else:
                self.custom.add_scene(name.value, m, val)
            self.page.pop_dialog()
            self._render_custom()

        dialog_w, dialog_h = dialog_dimensions(self, 460, 560)
        dlg = ft.AlertDialog(
            title=ft.Text(self._t("scenes.edit_title") if editing else self._t("scenes.new_title"), color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=ft.Container(
                width=dialog_w,
                height=dialog_h,
                content=ft.Column(
                    [
                        name,
                        mode,
                        value,
                        ft.Text(self._t("light.brightness"), style=Theme.LABEL),
                        dimming,
                        ft.Text(self._t("scenes.dynamic_speed"), style=Theme.LABEL),
                        speed,
                    ],
                    tight=True,
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[
                ft.TextButton(self._t("common.cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton(self._t("common.save"), bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        viewport = Viewport(max(280.0, float(width)), max(320.0, float(height)))
        available = max(260.0, viewport.width - (4.0 if viewport.compact else 8.0))
        # 120 px es el mínimo real de la card personalizada: contiene un
        # swatch y dos IconButton sin permitir que salgan del borde.
        minimum = 122.0
        cards = max(1, min(7, int((available + 10.0) // (minimum + 10.0))))
        raw_width = (available - 10.0 * (cards - 1)) / cards
        # Cuantizar hacia abajo evita que el redondeo agregue unos píxeles y
        # produzca overflow horizontal justo antes de un breakpoint.
        card_width = float(int(raw_width // 12.0) * 12)
        card_width = max(120.0, min(154.0, card_width, raw_width))
        layout_changed = cards != self._cards_per_row or abs(card_width - self._card_width) >= 6.0
        mode_changed = viewport.mode != self._viewport.mode
        self._viewport = viewport
        if layout_changed:
            self._cards_per_row = cards
            self._card_width = card_width
            self._render_custom()
            self._render_builtin_sections()
            self._highlight()
        if mode_changed:
            self.spacing = 12 if viewport.compact else 14
        if update and (layout_changed or mode_changed):
            supdate(self)

    def _delete_custom(self, uid: str):
        self.custom.remove_scene(uid)
        self._render_custom()
