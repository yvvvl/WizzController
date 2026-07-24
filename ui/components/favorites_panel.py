from __future__ import annotations

from typing import Any

import flet as ft

from config.custom_scenes_manager import CustomScenesManager
from config.favorites_manager import FavoritesManager
from core import wiz_scenes
from localization import (
    LocalizationManager,
    translated_favorite_name,
    translated_scene_name,
)
from ui.color_studio import (
    GlobalDragTracker,
    PaletteGeometry,
    contrast_text_color,
    hue_purity_to_rgb,
    kelvin_to_rgb,
    palette_png,
    parse_hex_color,
    rgb_to_hex,
    rgb_to_hsv,
    rgb_to_hue_purity,
)
from ui.responsive import PANEL_BREAKPOINTS, Viewport, dialog_dimensions
from ui.scene_visuals import scene_color, scene_icon
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
    try:
        return parse_hex_color(str(hex_color or ""))
    except (TypeError, ValueError):
        return None


def _custom_scene_icon(scene: dict[str, Any]) -> Any:
    name = str(scene.get("icon") or "AUTO_AWESOME").upper()
    return getattr(ft.Icons, name, getattr(ft.Icons, f"{name}_ROUNDED", ft.Icons.AUTO_AWESOME_ROUNDED))


class FavoritesPanel(ft.Column):
    def __init__(self, wiz, i18n=None):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.i18n = i18n or LocalizationManager(preference="es")
        self.manager = FavoritesManager()
        self.custom_scenes = CustomScenesManager()
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

    def _initial_brightness(self) -> int:
        try:
            value = int((self.wiz.get_state() or {}).get("dimming", 80))
        except Exception:
            value = 80
        return max(10, min(100, value))

    def _initial_editor_state(self, fav: dict[str, Any] | None = None) -> dict[str, Any]:
        favorite = fav or {"type": "rgb", "value": "#ff0000"}
        ftype = str(favorite.get("type") or "rgb")
        value = favorite.get("value")
        rgb_value = str(value) if ftype == "rgb" else "#ff0000"
        rgb = _parse_rgb(rgb_value) or (255, 0, 0)
        hue, purity = rgb_to_hue_purity(rgb)
        scene_id = int(
            value.get("sceneId", 18)
            if ftype == "scene" and isinstance(value, dict)
            else value if ftype == "scene" else 18
        )
        speed = int(value.get("speed", 100)) if ftype == "scene" and isinstance(value, dict) else 100
        lo, hi = self._kelvin_range()
        white = int(value) if ftype == "white" else 4000
        return {
            "type": ftype,
            "rgb": rgb_to_hex(rgb),
            "rgb_exact": rgb,
            "hue": hue,
            "purity": purity,
            "white": max(lo, min(hi, white)),
            "white_brightness": self._initial_brightness(),
            "brightness": max(10, min(100, int(value))) if ftype == "brightness" else 80,
            "scene": scene_id,
            "scene_source": f"wiz:{scene_id}",
            "speed": max(20, min(200, speed)),
        }

    def _rgb_from_state(self, state: dict[str, Any]) -> tuple[int, int, int]:
        exact = state.get("rgb_exact")
        if isinstance(exact, (tuple, list)) and len(exact) >= 3:
            return int(exact[0]), int(exact[1]), int(exact[2])
        return hue_purity_to_rgb(float(state["hue"]), float(state["purity"]))

    def _compatible_custom_scenes(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        if refresh:
            self.custom_scenes = CustomScenesManager()
        return [
            scene
            for scene in self.custom_scenes.get_scenes()
            if str(scene.get("mode") or "") in {"rgb", "white", "scene"}
        ]

    def _scene_details(self, state: dict[str, Any]) -> dict[str, Any]:
        source = str(state.get("scene_source") or f"wiz:{state.get('scene', 18)}")
        if source.startswith("custom:"):
            uid = source.split(":", 1)[1]
            scene = next(
                (item for item in self._compatible_custom_scenes() if str(item.get("id")) == uid),
                None,
            )
            if scene:
                mode = str(scene.get("mode") or "rgb")
                value = scene.get("value") if isinstance(scene.get("value"), dict) else {}
                icon = _custom_scene_icon(scene)
                color = "#8b5cf6"
                dynamic = False
                if mode == "rgb":
                    color = rgb_to_hex(
                        (
                            int(value.get("r", 255)),
                            int(value.get("g", 0)),
                            int(value.get("b", 0)),
                        )
                    )
                elif mode == "white":
                    color = rgb_to_hex(kelvin_to_rgb(int(value.get("temp", 4000))))
                elif mode == "scene":
                    sid = int(value.get("sceneId", 18))
                    builtin = wiz_scenes.get(sid)
                    color = scene_color(sid)
                    icon = scene_icon(sid)
                    dynamic = bool(builtin and builtin.dynamic)
                return {
                    "source": source,
                    "custom": scene,
                    "name": str(scene.get("name") or self._t("scenes.custom_fallback")),
                    "color": color,
                    "icon": icon,
                    "dynamic": dynamic,
                }

        sid = int(source.split(":", 1)[1]) if source.startswith("wiz:") else int(state.get("scene", 18))
        scene = wiz_scenes.get(sid)
        fallback = f"{self._t('favorites.scene')} {sid}"
        state["scene"] = sid
        return {
            "source": f"wiz:{sid}",
            "custom": None,
            "name": translated_scene_name(self.i18n, sid, scene.name if scene else fallback),
            "color": scene_color(sid),
            "icon": scene_icon(sid),
            "dynamic": bool(scene and scene.dynamic),
        }

    def _build_rgb_editor(self, state: dict[str, Any], on_preview) -> list[ft.Control]:
        geometry = PaletteGeometry(400, 120, 24)
        tracker = GlobalDragTracker(geometry.outer_width, geometry.outer_height)
        image = ft.Image(
            src=palette_png(400, 120, 24),
            width=geometry.image_width,
            height=geometry.image_height,
            left=geometry.image_left,
            top=geometry.image_top,
            fit=ft.BoxFit.FILL,
            border_radius=Theme.R_MD,
            filter_quality=ft.FilterQuality.HIGH,
            gapless_playback=True,
        )
        thumb = ft.Container(
            width=24,
            height=24,
            border_radius=12,
            border=ft.Border.all(3, "white"),
            shadow=Theme.SHADOW,
        )
        hex_field = ft.TextField(
            key="favorites-rgb-hex",
            label=self._t("favorites.hex"),
            value=state["rgb"],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            dense=True,
        )
        hue_purity = ft.Text(key="favorites-rgb-hue-purity", color=Theme.MUTED, size=12)
        hsv = ft.Text(key="favorites-rgb-hsv", color=Theme.MUTED, size=12)

        def refresh_rgb() -> None:
            rgb = self._rgb_from_state(state)
            state["rgb"] = rgb_to_hex(rgb)
            left, top = geometry.hue_purity_to_thumb_left_top(
                float(state["hue"]),
                float(state["purity"]),
            )
            thumb.left = left
            thumb.top = top
            thumb.bgcolor = state["rgb"]
            hex_field.value = rgb_to_hex(rgb, upper=True)
            hue_purity.value = self._t(
                "favorites.hue_purity_value",
                hue=round(float(state["hue"]) % 360),
                purity=round(float(state["purity"]) * 100),
            )
            hue, saturation, value = rgb_to_hsv(rgb)
            hsv.value = self._t(
                "favorites.hsv_value",
                hue=round(hue),
                saturation=round(saturation * 100),
                value=round(value * 100),
            )
            on_preview()
            for control in (thumb, hex_field, hue_purity, hsv):
                supdate(control)

        def select_point(point: tuple[float, float] | None) -> None:
            if point is None:
                return
            state["hue"], state["purity"] = geometry.pointer_to_hue_purity(*point)
            state["rgb_exact"] = None
            refresh_rgb()

        gesture = ft.GestureDetector(
            key="favorites-rgb-picker",
            width=geometry.outer_width,
            height=geometry.outer_height,
            drag_interval=6,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap_up=lambda event: select_point(tracker.tap(event)),
            on_pan_start=lambda event: select_point(tracker.begin(event)),
            on_pan_update=lambda event: select_point(tracker.move(event)),
            on_pan_end=lambda event: select_point(tracker.end(event)),
            on_pan_cancel=lambda event: select_point(tracker.cancel()),
        )
        palette = ft.Stack(
            [image, thumb, gesture],
            width=geometry.outer_width,
            height=geometry.outer_height,
        )

        def from_hex(event=None) -> None:
            rgb = _parse_rgb(str(hex_field.value or ""))
            if rgb is None:
                return
            state["rgb_exact"] = rgb
            state["hue"], state["purity"] = rgb_to_hue_purity(rgb)
            refresh_rgb()

        def select_swatch(color: str) -> None:
            hex_field.value = color
            from_hex()

        hex_field.on_submit = from_hex
        hex_field.on_blur = from_hex
        swatches = ft.Row(
            wrap=True,
            spacing=8,
            run_spacing=8,
            controls=[
                ft.Container(
                    key=f"favorites-rgb-swatch-{index}",
                    width=32,
                    height=32,
                    border_radius=16,
                    bgcolor=color,
                    tooltip=self._t(key),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white")),
                    on_click=lambda event, selected=color: select_swatch(selected),
                )
                for index, (key, color) in enumerate(RGB_SWATCHES)
            ],
        )
        refresh_rgb()
        return [
            ft.Text(self._t("favorites.rgb_picker"), style=Theme.LABEL),
            ft.Row([palette], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([hue_purity, hsv], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            hex_field,
            swatches,
        ]

    def _build_white_editor(self, state: dict[str, Any], on_preview) -> list[ft.Control]:
        lo, hi = self._kelvin_range()
        kelvin_label = ft.Text(
            key="favorites-white-kelvin",
            color=Theme.TEXT,
            weight=ft.FontWeight.W_600,
        )
        kelvin_slider = ft.Slider(
            key="favorites-white-kelvin-slider",
            min=lo,
            max=hi,
            value=max(lo, min(hi, int(state["white"]))),
            divisions=max(1, round((hi - lo) / 100)),
            active_color=Theme.WARNING,
            thumb_color="white",
            expand=True,
        )
        brightness_label = ft.Text(
            key="favorites-white-brightness",
            color=Theme.TEXT,
            weight=ft.FontWeight.W_600,
        )
        brightness_slider = ft.Slider(
            key="favorites-white-brightness-slider",
            min=10,
            max=100,
            value=int(state["white_brightness"]),
            divisions=18,
            active_color=Theme.ACCENT,
            thumb_color="white",
            expand=True,
        )

        def refresh_white(event=None) -> None:
            state["white"] = int(kelvin_slider.value)
            state["white_brightness"] = int(brightness_slider.value)
            kelvin_label.value = self._t("favorites.kelvin_value", value=state["white"])
            brightness_label.value = self._t(
                "favorites.brightness_value",
                value=state["white_brightness"],
            )
            on_preview()
            supdate(kelvin_label)
            supdate(brightness_label)

        def select_preset(kelvin: int) -> None:
            kelvin_slider.value = kelvin
            refresh_white()
            supdate(kelvin_slider)

        kelvin_slider.on_change = refresh_white
        brightness_slider.on_change = refresh_white
        presets = [(kelvin, key) for kelvin, key in WHITE_PRESETS if lo <= kelvin <= hi]
        preset_row = ft.Row(
            key="favorites-white-presets",
            wrap=True,
            spacing=8,
            run_spacing=8,
            controls=[
                ft.OutlinedButton(
                    self._t(
                        "favorites.white_preset",
                        name=self._t(key),
                        kelvin=kelvin,
                    ),
                    style=ft.ButtonStyle(
                        color=Theme.TEXT,
                        side=ft.BorderSide(1, Theme.STROKE),
                    ),
                    on_click=lambda event, value=kelvin: select_preset(value),
                )
                for kelvin, key in presets
            ],
        )
        refresh_white()
        return [
            ft.Text(
                self._t("favorites.kelvin_range", minimum=lo, maximum=hi),
                color=Theme.MUTED,
                size=12,
            ),
            kelvin_label,
            kelvin_slider,
            preset_row,
            ft.Divider(height=8, color=Theme.STROKE),
            brightness_label,
            brightness_slider,
        ]

    def _build_scene_editor(self, state: dict[str, Any], on_preview) -> list[ft.Control]:
        custom_scenes = self._compatible_custom_scenes(refresh=True)
        options = [
            ft.DropdownOption(
                key=f"wiz:{sid}",
                text=self._t(
                    "favorites.scene_option_wiz",
                    name=translated_scene_name(self.i18n, sid, scene.name),
                ),
            )
            for sid, scene in wiz_scenes.CATALOG.items()
        ]
        options.extend(
            ft.DropdownOption(
                key=f"custom:{scene.get('id')}",
                text=self._t(
                    "favorites.scene_option_custom",
                    name=scene.get("name") or self._t("scenes.custom_fallback"),
                ),
            )
            for scene in custom_scenes
        )
        selector = ft.Dropdown(
            key="favorites-scene-selector",
            label=self._t("favorites.scene"),
            value=str(state.get("scene_source") or "wiz:18"),
            options=options,
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
        visual_icon = ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color="white", size=22)
        visual = ft.Container(
            key="favorites-scene-visual",
            width=48,
            height=48,
            border_radius=14,
            alignment=ft.Alignment.CENTER,
            content=visual_icon,
        )
        title = ft.Text(color=Theme.TEXT, weight=ft.FontWeight.W_600)
        source = ft.Text(color=Theme.MUTED, size=11)
        speed_label = ft.Text(
            key="favorites-scene-speed",
            color=Theme.TEXT,
            weight=ft.FontWeight.W_600,
        )
        speed = ft.Slider(
            key="favorites-scene-speed-slider",
            min=20,
            max=200,
            value=int(state["speed"]),
            divisions=18,
            active_color=Theme.ACCENT,
            thumb_color="white",
            expand=True,
        )
        speed_section = ft.Column(
            [speed_label, speed],
            key="favorites-scene-speed-section",
            spacing=4,
        )

        def refresh_scene(event=None) -> None:
            state["scene_source"] = str(selector.value or "wiz:18")
            details = self._scene_details(state)
            visual.bgcolor = details["color"]
            visual_icon.name = details["icon"]
            title.value = details["name"]
            source.value = self._t(
                "favorites.custom_scene" if details["custom"] else "favorites.wiz_scene"
            )
            speed_section.visible = bool(details["dynamic"])
            speed_label.value = self._t("favorites.speed_value", value=int(state["speed"]))
            on_preview()
            for control in (visual, visual_icon, title, source, speed_section, speed_label):
                supdate(control)

        def speed_changed(event=None) -> None:
            state["speed"] = int(speed.value)
            refresh_scene()

        def scene_changed(event=None) -> None:
            state["scene_source"] = str(selector.value or "wiz:18")
            details = self._scene_details(state)
            custom = details.get("custom")
            if isinstance(custom, dict) and custom.get("mode") == "scene":
                value = custom.get("value")
                if isinstance(value, dict):
                    state["speed"] = max(20, min(200, int(value.get("speed", 100))))
                    speed.value = state["speed"]
                    supdate(speed)
            refresh_scene()

        selector.on_change = scene_changed
        speed.on_change = speed_changed
        refresh_scene()
        controls: list[ft.Control] = [
            selector,
            ft.Row(
                [visual, ft.Column([title, source], spacing=2, expand=True)],
                spacing=12,
            ),
            speed_section,
        ]
        if not custom_scenes:
            controls.append(
                ft.Text(
                    self._t("favorites.custom_scenes_empty"),
                    color=Theme.FAINT,
                    size=11,
                )
            )
        return controls

    def _build_brightness_editor(self, state: dict[str, Any], on_preview) -> list[ft.Control]:
        label = ft.Text(
            key="favorites-brightness-value",
            color=Theme.TEXT,
            weight=ft.FontWeight.W_600,
            size=18,
            text_align=ft.TextAlign.CENTER,
        )
        slider = ft.Slider(
            key="favorites-brightness-slider",
            min=10,
            max=100,
            value=int(state["brightness"]),
            divisions=18,
            active_color=Theme.ACCENT,
            thumb_color="white",
            expand=True,
        )

        def refresh_brightness(event=None) -> None:
            state["brightness"] = int(slider.value)
            label.value = self._t("favorites.brightness_value", value=state["brightness"])
            on_preview()
            supdate(label)

        slider.on_change = refresh_brightness
        refresh_brightness()
        return [
            ft.Container(
                content=ft.Column(
                    [label, slider],
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(vertical=20),
            )
        ]

    def _render_editor_mode(
        self,
        editor: ft.Column,
        mode: str,
        state: dict[str, Any],
        on_preview,
    ) -> None:
        builders = {
            "rgb": self._build_rgb_editor,
            "white": self._build_white_editor,
            "scene": self._build_scene_editor,
            "brightness": self._build_brightness_editor,
        }
        selected = mode if mode in builders else "rgb"
        state["type"] = selected
        editor.controls = [
            ft.Column(
                key=f"favorites-editor-{selected}",
                controls=builders[selected](state, on_preview),
                spacing=10,
            )
        ]
        editor.data = selected
        supdate(editor)

    def _favorite_payload(self, state: dict[str, Any]) -> tuple[str, object, str]:
        ftype = str(state.get("type") or "rgb")
        if ftype == "rgb":
            return "rgb", rgb_to_hex(self._rgb_from_state(state)), "PALETTE"
        if ftype == "white":
            return "white", int(state["white"]), "LIGHT_MODE"
        if ftype == "brightness":
            return "brightness", int(state["brightness"]), "BRIGHTNESS_6"

        details = self._scene_details(state)
        custom = details.get("custom")
        if isinstance(custom, dict):
            mode = str(custom.get("mode") or "")
            value = custom.get("value") if isinstance(custom.get("value"), dict) else {}
            if mode == "rgb":
                rgb = (
                    int(value.get("r", 255)),
                    int(value.get("g", 0)),
                    int(value.get("b", 0)),
                )
                return "rgb", rgb_to_hex(rgb), "PALETTE"
            if mode == "white":
                return "white", int(value.get("temp", 4000)), "LIGHT_MODE"
            if mode == "scene":
                return (
                    "scene",
                    {
                        "sceneId": int(value.get("sceneId", 18)),
                        "speed": int(state["speed"]),
                    },
                    "AUTO_AWESOME",
                )
        return (
            "scene",
            {"sceneId": int(state["scene"]), "speed": int(state["speed"])},
            "AUTO_AWESOME",
        )

    def _favorite_dialog(self, fav: dict | None = None):
        if not mounted(self):
            return

        editing = fav is not None
        favorite = fav or {
            "name": self._t("favorites.default_name"),
            "type": "rgb",
            "value": "#ff0000",
        }
        state = self._initial_editor_state(favorite)
        name = ft.TextField(
            label=self._t("favorites.name"),
            value=translated_favorite_name(self.i18n, favorite)
            or self._t("favorites.default_name"),
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
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
        preview = ft.Container(
            width=58,
            height=58,
            border_radius=18,
            bgcolor="#ff0000",
            border=ft.Border.all(1, Theme.STROKE),
            alignment=ft.Alignment.CENTER,
        )
        summary = ft.Text("", color=Theme.MUTED, size=12)
        editor = ft.Column(spacing=10)

        def update_preview() -> None:
            ftype = str(kind.value or "rgb")
            if ftype == "rgb":
                rgb = self._rgb_from_state(state)
                preview.bgcolor = rgb_to_hex(rgb)
                preview.content = ft.Icon(
                    ft.Icons.PALETTE_ROUNDED,
                    color=contrast_text_color(rgb),
                )
                hue, saturation, value = rgb_to_hsv(rgb)
                summary.value = self._t(
                    "favorites.rgb_summary",
                    hex=rgb_to_hex(rgb, upper=True),
                    hue=round(hue),
                    saturation=round(saturation * 100),
                    value=round(value * 100),
                )
            elif ftype == "white":
                rgb = kelvin_to_rgb(int(state["white"]))
                preview.bgcolor = rgb_to_hex(rgb)
                preview.content = ft.Icon(
                    ft.Icons.LIGHT_MODE_ROUNDED,
                    color=contrast_text_color(rgb),
                )
                summary.value = self._t(
                    "favorites.white_summary",
                    kelvin=int(state["white"]),
                    brightness=int(state["white_brightness"]),
                )
            elif ftype == "brightness":
                preview.bgcolor = Theme.ACCENT
                preview.content = ft.Icon(
                    ft.Icons.BRIGHTNESS_6_ROUNDED,
                    color="white",
                )
                summary.value = self._t(
                    "favorites.brightness_value",
                    value=int(state["brightness"]),
                )
            else:
                details = self._scene_details(state)
                preview.bgcolor = details["color"]
                preview.content = ft.Icon(details["icon"], color="white")
                summary.value = (
                    self._t(
                        "favorites.scene_summary",
                        scene=details["name"],
                        speed=int(state["speed"]),
                    )
                    if details["dynamic"]
                    else self._t(
                        "favorites.scene_static_summary",
                        scene=details["name"],
                    )
                )
            supdate(preview)
            supdate(summary)

        def render_editor(event=None) -> None:
            mode = str(kind.value or "rgb")
            state["type"] = mode
            update_preview()
            self._render_editor_mode(editor, mode, state, update_preview)

        kind.on_change = render_editor
        render_editor()

        def save(event) -> None:
            state["type"] = str(kind.value or "rgb")
            ftype, value, icon = self._favorite_payload(state)
            if editing:
                self.manager.update_favorite(
                    favorite.get("id"),
                    name.value,
                    ftype,
                    value,
                    icon,
                )
            else:
                self.manager.add_favorite(name.value, ftype, value, icon)
            self.page.pop_dialog()
            self._render()

        dialog_w, dialog_h = dialog_dimensions(self, 580, 620)
        identity = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=preview,
                    col={"xs": 12, "sm": 2},
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(
                    content=ft.Column([name, summary], spacing=6),
                    col={"xs": 12, "sm": 10},
                ),
            ],
        )
        dialog = ft.AlertDialog(
            title=ft.Text(
                self._t("favorites.edit_title")
                if editing
                else self._t("favorites.new_title"),
                color=Theme.TEXT,
            ),
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
                ft.TextButton(
                    self._t("favorites.cancel"),
                    on_click=lambda event: self.page.pop_dialog(),
                ),
                ft.ElevatedButton(
                    self._t("favorites.save"),
                    bgcolor=Theme.PRIMARY,
                    color="white",
                    on_click=save,
                ),
            ],
        )
        self.page.show_dialog(dialog)

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
