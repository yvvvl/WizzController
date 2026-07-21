from __future__ import annotations

import colorsys
import re
from copy import deepcopy
from typing import Any, Callable

import flet as ft

from config.custom_scenes_manager import CustomScenesManager
from config.favorites_manager import FavoritesManager
from config.routines_manager import RoutinesManager
from core import wiz_scenes
from core.action_sequence import ActionSequenceExecutor
from ui.scene_visuals import scene_color, scene_icon
from ui.theme import Theme, mounted, supdate

RGB_SWATCHES = [
    ("Rojo", "#ff0000"), ("Naranjo", "#ff7f00"), ("Amarillo", "#ffd000"),
    ("Verde", "#00ff40"), ("Cian", "#00d5ff"), ("Azul", "#0055ff"),
    ("Violeta", "#7f00ff"), ("Magenta", "#ff00cc"), ("Rosa", "#ff4fa3"),
]
WHITE_PRESETS = [(2200, "Vela"), (2700, "Cálido"), (4000, "Neutro"), (5000, "Día"), (6500, "Frío")]

ACTION_LABELS = {
    "turn_on": "Encender",
    "turn_off": "Apagar",
    "toggle": "Alternar",
    "brightness": "Brillo",
    "brightness_delta": "Subir/Bajar brillo",
    "rgb": "Color",
    "white_percent": "Blanco cálido/frío",
    "white_kelvin": "Blanco Kelvin",
    "scene": "Escena WiZ",
    "favorite": "Favorito",
    "custom_scene": "Escena personalizada",
    "routine": "Otra rutina",
    "wait": "Esperar",
    "target_mode": "Destino",
}
ACTION_ORDER = [
    "turn_on", "turn_off", "toggle", "brightness", "brightness_delta", "rgb", "white_percent", "white_kelvin",
    "scene", "favorite", "custom_scene", "routine", "wait", "target_mode",
]
ROUTINE_ICON_OPTIONS = [
    ("AUTO_AWESOME_ROUNDED", "Auto"),
    ("SCHOOL_ROUNDED", "Estudio"),
    ("NIGHTLIGHT_ROUNDED", "Noche"),
    ("SPORTS_ESPORTS_ROUNDED", "Juego"),
    ("MOVIE_ROUNDED", "Cine"),
    ("MENU_BOOK_ROUNDED", "Lectura"),
    ("POWER_SETTINGS_NEW_ROUNDED", "Apagado"),
    ("PALETTE_ROUNDED", "Color"),
    ("LIGHT_MODE_ROUNDED", "Luz"),
    ("ROCKET_LAUNCH_ROUNDED", "Rutina"),
]


def _icon(name: str | None, fallback=None):
    return getattr(ft.Icons, str(name or "AUTO_AWESOME_ROUNDED"), fallback or ft.Icons.AUTO_AWESOME_ROUNDED)


def _parse_rgb(hex_color: Any) -> tuple[int, int, int] | None:
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


def _hsv_from_hex(hex_color: Any) -> tuple[int, int, int]:
    rgb = _parse_rgb(hex_color) or (255, 0, 0)
    h, s, v = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    return round(h * 360), round(s * 100), round(v * 100)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return int(default)


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


class RoutinesPanel(ft.Column):
    """Rutinas compuestas con editor visual.

    Fase 55: deja de usar “tipo + valor” crudo para crear rutinas. Cada acción
    tiene un editor visual mínimo: color picker simple, blanco cálido/frío,
    escenas por nombre, sliders de brillo, favoritos y escenas personalizadas.
    """

    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=16, expand=True)
        self.wiz = wiz
        self.manager = RoutinesManager()
        self.executor = ActionSequenceExecutor(wiz)
        self.list_view = ft.Column(spacing=10)
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Rutinas", style=Theme.H1),
                        ft.Text("Presets compuestos simples para voz, hotkeys y acciones rápidas", color=Theme.MUTED, size=13),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.ElevatedButton("Nueva", icon=ft.Icons.ADD_ROUNDED, bgcolor=Theme.PRIMARY, color="white", on_click=lambda e: self._open_editor()),
                ft.OutlinedButton("Capturar estado", icon=ft.Icons.CAMERA_ALT_ROUNDED, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)), on_click=lambda e: self._capture_current()),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )
        info = self._card(
            ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, color=Theme.PRIMARY, size=18),
                    ft.Text("Crea rutinas visuales sin JSON: color, blanco, brillo, escena, favoritos, espera y destino.", color=Theme.MUTED, size=12, expand=True),
                    ft.TextButton("Restaurar presets", icon=ft.Icons.RESTART_ALT_ROUNDED, on_click=lambda e: self._reset_defaults()),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            pad=12,
        )
        self.controls = [header, info, self.list_view]
        self._render()

    def _card(self, content, pad=16):
        return ft.Container(
            content=content,
            padding=pad,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )

    def _render(self):
        self.manager = RoutinesManager()
        self.list_view.controls.clear()
        routines = self.manager.get_routines()
        if not routines:
            self.list_view.controls.append(
                ft.Container(
                    padding=32,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        [ft.Icon(ft.Icons.ROCKET_LAUNCH_OUTLINED, color=Theme.MUTED, size=40), ft.Text("No hay rutinas.", color=Theme.MUTED)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        for routine in routines:
            self.list_view.controls.append(self._routine_card(routine))
        supdate(self.list_view)

    # ------------------------------------------------------------------ #
    # Cards / resumen
    # ------------------------------------------------------------------ #
    def _routine_card(self, r: dict[str, Any]):
        color = str(r.get("color") or self._color_from_actions(r.get("actions", [])) or Theme.PRIMARY)
        actions = r.get("actions") if isinstance(r.get("actions"), list) else []
        summary = "  ·  ".join(self._action_text(a) for a in actions[:5])
        if len(actions) > 5:
            summary += f"  ·  +{len(actions) - 5}"
        return ft.Container(
            padding=14,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(_icon(r.get("icon")), color="white", size=22),
                        width=48,
                        height=48,
                        border_radius=15,
                        bgcolor=color,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(r.get("name", "Rutina"), color=Theme.TEXT, weight=ft.FontWeight.W_600, size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(r.get("description", ""), color=Theme.MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(summary or "Sin acciones", color=Theme.FAINT, size=10, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.ElevatedButton("Aplicar", icon=ft.Icons.PLAY_ARROW_ROUNDED, bgcolor=Theme.PRIMARY, color="white", on_click=lambda e, x=r: self._apply(x)),
                    ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Theme.PRIMARY, tooltip="Editar", on_click=lambda e, x=r: self._open_editor(x)),
                    ft.IconButton(ft.Icons.CONTENT_COPY_ROUNDED, icon_color=Theme.MUTED, tooltip="Duplicar", on_click=lambda e, uid=r.get("id"): self._duplicate(uid)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, tooltip="Eliminar", on_click=lambda e, uid=r.get("id"): self._delete(uid)),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _action_visual(self, action: dict[str, Any]) -> tuple[str, Any, str, str]:
        kind = str(action.get("type") or "")
        value = action.get("value")
        if kind == "turn_on":
            return Theme.SUCCESS, ft.Icons.POWER_SETTINGS_NEW_ROUNDED, "Encender", "sin valor"
        if kind == "turn_off":
            return Theme.FAINT, ft.Icons.POWER_OFF_ROUNDED, "Apagar", "sin valor"
        if kind == "toggle":
            return Theme.PRIMARY, ft.Icons.TOGGLE_ON_ROUNDED, "Alternar", "sin valor"
        if kind == "brightness":
            return Theme.ACCENT, ft.Icons.BRIGHTNESS_6_ROUNDED, "Brillo", f"{value}%"
        if kind == "brightness_delta":
            return Theme.ACCENT, ft.Icons.EXPOSURE_ROUNDED, "Brillo +/-", f"{int(value or 0):+d}%"
        if kind == "rgb":
            rgb = value if isinstance(value, str) else "#{:02x}{:02x}{:02x}".format(*self._rgb_tuple(value))
            return str(rgb), ft.Icons.PALETTE_ROUNDED, "Color", str(rgb).upper()
        if kind == "white_percent":
            return Theme.WARNING, ft.Icons.LIGHT_MODE_ROUNDED, "Blanco", f"{value}%"
        if kind == "white_kelvin":
            return Theme.WARNING, ft.Icons.WB_SUNNY_ROUNDED, "Blanco", f"{value}K"
        if kind == "scene":
            sid = int(value.get("sceneId", 18) if isinstance(value, dict) else value or 18)
            sc = wiz_scenes.get(sid)
            return scene_color(sid, "#8b5cf6"), scene_icon(sid), "Escena", sc.name if sc else f"Escena {sid}"
        if kind == "favorite":
            fav = FavoritesManager().get_favorite(str(value or ""))
            return "#fbbf24", ft.Icons.STAR_ROUNDED, "Favorito", fav.get("name", "Favorito") if fav else "No encontrado"
        if kind == "custom_scene":
            scn = CustomScenesManager().get_scene(str(value or ""))
            return "#ec4899", ft.Icons.AUTO_AWESOME_ROUNDED, "Mi escena", scn.get("name", "Escena") if scn else "No encontrada"
        if kind == "routine":
            rt = RoutinesManager().get_routine(str(value or ""))
            return "#5b8cff", ft.Icons.ROCKET_LAUNCH_ROUNDED, "Rutina", rt.get("name", "Rutina") if rt else "No encontrada"
        if kind == "wait":
            return Theme.MUTED, ft.Icons.HOURGLASS_BOTTOM_ROUNDED, "Esperar", f"{value}ms"
        if kind == "target_mode":
            return Theme.PRIMARY, ft.Icons.ADJUST_ROUNDED, "Destino", "Todas" if value == "all" else "Una ampolleta"
        return Theme.PRIMARY, ft.Icons.AUTO_AWESOME_ROUNDED, ACTION_LABELS.get(kind, kind or "Acción"), str(value or "")

    def _action_text(self, action: dict[str, Any]) -> str:
        _, _, title, sub = self._action_visual(action)
        return title if not sub or sub == "sin valor" else f"{title} {sub}"

    def _color_from_actions(self, actions: Any) -> str | None:
        if not isinstance(actions, list):
            return None
        for action in actions:
            if not isinstance(action, dict):
                continue
            color, _, _, _ = self._action_visual(action)
            if isinstance(color, str) and color.startswith("#"):
                return color
        return None

    # ------------------------------------------------------------------ #
    # Operaciones
    # ------------------------------------------------------------------ #
    def _apply(self, routine: dict[str, Any]):
        self.executor.execute(routine, threaded=True)

    def _duplicate(self, uid):
        self.manager.duplicate_routine(str(uid))
        self._render()

    def _delete(self, uid):
        self.manager.remove_routine(str(uid))
        self._render()

    def _reset_defaults(self):
        self.manager.reset_defaults()
        self._render()

    def _capture_current(self):
        state = self.wiz.get_state() if hasattr(self.wiz, "get_state") else {}
        actions = [{"type": "turn_on"}]
        if state.get("sceneId"):
            actions.append({"type": "scene", "value": {"sceneId": int(state.get("sceneId")), "speed": int(state.get("speed", 100) or 100)}})
        elif all(k in state for k in ("r", "g", "b")):
            actions.append({"type": "rgb", "value": "#{:02x}{:02x}{:02x}".format(int(state.get("r", 0)), int(state.get("g", 0)), int(state.get("b", 0)))})
        elif state.get("temp"):
            actions.append({"type": "white_kelvin", "value": int(state.get("temp"))})
        if state.get("dimming"):
            actions.append({"type": "brightness", "value": int(state.get("dimming"))})
        self.manager.add_routine("Rutina capturada", actions, "Creada desde el estado actual", self._color_from_actions(actions) or "#5b8cff", "CAMERA_ALT_ROUNDED")
        self._render()

    # ------------------------------------------------------------------ #
    # Editor de rutina
    # ------------------------------------------------------------------ #
    def _open_editor(self, routine: dict[str, Any] | None = None):
        if not mounted(self):
            return
        is_new = routine is None
        routine = deepcopy(routine or {"name": "", "description": "", "color": "#5b8cff", "icon": "AUTO_AWESOME_ROUNDED", "actions": [{"type": "turn_on"}, {"type": "brightness", "value": 70}]})
        actions: list[dict[str, Any]] = [deepcopy(a) for a in routine.get("actions", []) if isinstance(a, dict)]
        if not actions:
            actions.append({"type": "turn_on"})

        name = ft.TextField(label="Nombre", value=str(routine.get("name", "")), dense=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        desc = ft.TextField(label="Descripción", value=str(routine.get("description", "")), dense=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        accent = {"color": str(routine.get("color") or self._color_from_actions(actions) or "#5b8cff")}
        icon_dd = ft.Dropdown(
            label="Icono",
            value=str(routine.get("icon") or "AUTO_AWESOME_ROUNDED"),
            options=[ft.DropdownOption(key=k, text=v) for k, v in ROUTINE_ICON_OPTIONS],
            width=180,
            dense=True,
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
        color_field = ft.TextField(label="Color tarjeta", value=accent["color"], dense=True, width=150, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        color_preview = ft.Container(width=42, height=42, border_radius=13, bgcolor=accent["color"], border=ft.Border.all(1, Theme.STROKE), alignment=ft.Alignment.CENTER, content=ft.Icon(_icon(icon_dd.value), color="white"))
        actions_column = ft.Column(spacing=8)

        def update_routine_preview(e=None):
            c = str(color_field.value or "#5b8cff")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", c):
                c = self._color_from_actions(actions) or "#5b8cff"
            accent["color"] = c
            color_preview.bgcolor = c
            color_preview.content = ft.Icon(_icon(icon_dd.value), color="white")
            supdate(color_preview)

        def render_actions():
            actions_column.controls.clear()
            for idx, action in enumerate(actions):
                actions_column.controls.append(self._action_row(idx, action, actions, render_actions))
            supdate(actions_column)
            update_routine_preview()

        def add_action(e=None):
            self._open_action_dialog(None, lambda a: (actions.append(a), render_actions()), current_routine_id=str(routine.get("id") or ""))

        def save(e):
            update_routine_preview()
            final_actions = [a for a in actions if isinstance(a, dict) and a.get("type")]
            if not final_actions:
                final_actions = [{"type": "turn_on"}]
            final_name = (name.value or "Nueva rutina").strip() or "Nueva rutina"
            final_desc = (desc.value or "").strip()
            final_icon = icon_dd.value or "AUTO_AWESOME_ROUNDED"
            if is_new:
                self.manager.add_routine(final_name, final_actions, final_desc, accent["color"], final_icon)
            else:
                self.manager.update_routine(str(routine.get("id")), name=final_name, description=final_desc, color=accent["color"], icon=final_icon, actions=final_actions)
            self.page.pop_dialog()
            self._render()

        icon_dd.on_change = update_routine_preview
        color_field.on_submit = update_routine_preview
        color_swatches = ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[
            ft.Container(width=28, height=28, border_radius=14, bgcolor=c, tooltip=n, border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white")), on_click=lambda ev, col=c: (setattr(color_field, "value", col), update_routine_preview(), supdate(color_field)))
            for n, c in RGB_SWATCHES
        ])
        render_actions()

        dlg = ft.AlertDialog(
            bgcolor=Theme.SURFACE,
            title=ft.Text("Nueva rutina" if is_new else "Editar rutina", color=Theme.TEXT),
            content=ft.Container(
                width=620,
                height=610,
                content=ft.Column(
                    [
                        ft.Row([color_preview, ft.Column([name, desc], spacing=8, expand=True)], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Row([icon_dd, color_field], spacing=10),
                        color_swatches,
                        ft.Divider(height=8, color=Theme.STROKE),
                        ft.Row([ft.Text("ACCIONES", style=Theme.LABEL), ft.Container(expand=True), ft.OutlinedButton("Agregar acción", icon=ft.Icons.ADD_ROUNDED, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)), on_click=add_action)], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Container(content=actions_column, expand=True),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton("Guardar", bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    def _action_row(self, idx: int, action: dict[str, Any], actions: list[dict[str, Any]], rerender: Callable[[], None]):
        color, icon, title, subtitle = self._action_visual(action)

        def edit(e=None):
            self._open_action_dialog(action, lambda new: (actions.__setitem__(idx, new), rerender()))

        def delete(e=None):
            try:
                actions.pop(idx)
                rerender()
            except Exception:
                pass

        def move(delta: int):
            j = idx + delta
            if 0 <= j < len(actions):
                actions[idx], actions[j] = actions[j], actions[idx]
                rerender()

        return ft.Container(
            padding=10,
            border_radius=Theme.R_SM,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [
                    ft.Text(str(idx + 1), color=Theme.FAINT, width=20),
                    ft.Container(content=ft.Icon(icon, color="white", size=18), width=36, height=36, border_radius=11, bgcolor=color, alignment=ft.Alignment.CENTER),
                    ft.Column([ft.Text(title, color=Theme.TEXT, weight=ft.FontWeight.W_600, size=13), ft.Text(subtitle, color=Theme.MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)], spacing=1, expand=True),
                    ft.IconButton(ft.Icons.KEYBOARD_ARROW_UP_ROUNDED, icon_color=Theme.MUTED, tooltip="Subir", icon_size=18, on_click=lambda e: move(-1)),
                    ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, icon_color=Theme.MUTED, tooltip="Bajar", icon_size=18, on_click=lambda e: move(1)),
                    ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Theme.PRIMARY, tooltip="Editar acción", icon_size=18, on_click=edit),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, tooltip="Borrar acción", icon_size=18, on_click=delete),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    # ------------------------------------------------------------------ #
    # Editor visual de acción
    # ------------------------------------------------------------------ #
    def _open_action_dialog(self, action: dict[str, Any] | None, on_save: Callable[[dict[str, Any]], None], current_routine_id: str = ""):
        if not mounted(self):
            return
        state = self._action_to_state(action or {"type": "brightness", "value": 70})
        kind = ft.Dropdown(
            label="Acción",
            value=state["type"],
            options=[ft.DropdownOption(key=k, text=ACTION_LABELS[k]) for k in ACTION_ORDER],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
        preview = ft.Container(width=58, height=58, border_radius=18, bgcolor=Theme.PRIMARY, border=ft.Border.all(1, Theme.STROKE), alignment=ft.Alignment.CENTER)
        summary = ft.Text("", color=Theme.MUTED, size=12)
        editor = ft.Column(spacing=10)

        def update_preview():
            action_now = self._state_to_action(state)
            color, icon, title, subtitle = self._action_visual(action_now)
            preview.bgcolor = color
            preview.content = ft.Icon(icon, color="white")
            summary.value = title if not subtitle else f"{title} · {subtitle}"
            supdate(preview)
            supdate(summary)

        def render(e=None):
            state["type"] = kind.value or "brightness"
            editor.controls.clear()
            t = state["type"]
            if t in {"turn_on", "turn_off", "toggle"}:
                editor.controls.append(ft.Text("Esta acción no necesita configuración.", color=Theme.MUTED, size=13))

            elif t == "brightness":
                label = ft.Text("", color=Theme.TEXT, weight=ft.FontWeight.W_600)
                slider = ft.Slider(min=10, max=100, value=_clamp(state.get("brightness", 70), 10, 100), divisions=18, active_color=Theme.ACCENT, thumb_color="white", expand=True)
                def changed(ev=None):
                    state["brightness"] = int(slider.value)
                    label.value = f"Brillo {state['brightness']}%"
                    update_preview(); supdate(label)
                slider.on_change = changed
                changed()
                editor.controls.extend([label, slider])

            elif t == "brightness_delta":
                label = ft.Text("", color=Theme.TEXT, weight=ft.FontWeight.W_600)
                slider = ft.Slider(min=-50, max=50, value=_clamp(state.get("delta", 10), -50, 50), divisions=20, active_color=Theme.ACCENT, thumb_color="white", expand=True)
                def changed(ev=None):
                    val = int(slider.value)
                    if val == 0:
                        val = 10
                        slider.value = 10
                    state["delta"] = val
                    label.value = f"Cambio {val:+d}%"
                    update_preview(); supdate(label); supdate(slider)
                slider.on_change = changed
                changed()
                editor.controls.extend([label, slider])

            elif t == "rgb":
                hex_field = ft.TextField(label="HEX", value=state.get("rgb", "#ff0000"), color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE, dense=True)
                hue = ft.Slider(min=0, max=359, value=state.get("h", 0), divisions=36, active_color=Theme.PRIMARY, thumb_color="white", expand=True)
                sat = ft.Slider(min=0, max=100, value=state.get("s", 100), divisions=20, active_color=Theme.ACCENT, thumb_color="white", expand=True)
                val = ft.Slider(min=10, max=100, value=max(10, state.get("v", 100)), divisions=18, active_color=Theme.WARNING, thumb_color="white", expand=True)
                def from_sliders(ev=None):
                    state["h"], state["s"], state["v"] = int(hue.value), int(sat.value), int(val.value)
                    state["rgb"] = _hex_from_hsv(state["h"], state["s"], state["v"])
                    hex_field.value = state["rgb"]
                    update_preview(); supdate(hex_field)
                def from_hex(ev=None):
                    rgb = _parse_rgb(hex_field.value)
                    if not rgb:
                        return
                    state["rgb"] = hex_field.value if str(hex_field.value).startswith("#") else "#" + str(hex_field.value)
                    state["h"], state["s"], state["v"] = _hsv_from_hex(state["rgb"])
                    hue.value, sat.value, val.value = state["h"], state["s"], state["v"]
                    update_preview(); supdate(hue); supdate(sat); supdate(val)
                hue.on_change = sat.on_change = val.on_change = from_sliders
                hex_field.on_submit = from_hex
                swatches = ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[
                    ft.Container(width=32, height=32, border_radius=16, bgcolor=c, tooltip=n, border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white")), on_click=lambda ev, col=c, hf=hex_field: (setattr(hf, "value", col), from_hex()))
                    for n, c in RGB_SWATCHES
                ])
                editor.controls.extend([swatches, hex_field, ft.Text("Matiz", style=Theme.LABEL), hue, ft.Text("Intensidad", style=Theme.LABEL), sat, ft.Text("Claridad", style=Theme.LABEL), val])

            elif t == "white_percent":
                label = ft.Text("", color=Theme.TEXT, weight=ft.FontWeight.W_600)
                slider = ft.Slider(min=0, max=100, value=_clamp(state.get("white_percent", 50), 0, 100), divisions=100, active_color=Theme.WARNING, thumb_color="white", expand=True)
                def changed(ev=None):
                    state["white_percent"] = int(slider.value)
                    label.value = f"Blanco {state['white_percent']}% · {self._kelvin_from_pct(state['white_percent'])}K"
                    update_preview(); supdate(label)
                slider.on_change = changed
                def preset(k: int):
                    state["white_percent"] = self._pct_from_kelvin(k)
                    slider.value = state["white_percent"]
                    changed(); supdate(slider)
                buttons = ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[ft.OutlinedButton(txt, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)), on_click=lambda ev, kk=k: preset(kk)) for k, txt in WHITE_PRESETS])
                changed()
                editor.controls.extend([label, slider, buttons])

            elif t == "white_kelvin":
                lo, hi = self._kelvin_range()
                label = ft.Text("", color=Theme.TEXT, weight=ft.FontWeight.W_600)
                slider = ft.Slider(min=lo, max=hi, value=_clamp(state.get("kelvin", 4000), lo, hi), divisions=80, active_color=Theme.WARNING, thumb_color="white", expand=True)
                def changed(ev=None):
                    state["kelvin"] = int(slider.value)
                    label.value = f"{state['kelvin']}K"
                    update_preview(); supdate(label)
                slider.on_change = changed
                changed()
                editor.controls.extend([label, slider])

            elif t == "scene":
                dd = ft.Dropdown(
                    label="Escena",
                    value=str(state.get("scene", 18)),
                    options=[ft.DropdownOption(key=str(sid), text=f"{sid} · {sc.name}") for sid, sc in wiz_scenes.CATALOG.items()],
                    color=Theme.TEXT,
                    bgcolor=Theme.BG,
                    border_color=Theme.STROKE,
                )
                speed_label = ft.Text("", color=Theme.TEXT, weight=ft.FontWeight.W_600)
                speed = ft.Slider(min=20, max=200, value=_clamp(state.get("speed", 100), 20, 200), divisions=18, active_color=Theme.ACCENT, thumb_color="white", expand=True)
                def scene_changed(ev=None):
                    state["scene"] = int(dd.value or 18)
                    update_preview()
                def speed_changed(ev=None):
                    state["speed"] = int(speed.value)
                    speed_label.value = f"Velocidad {state['speed']}"
                    update_preview(); supdate(speed_label)
                dd.on_change = scene_changed
                speed.on_change = speed_changed
                speed_changed()
                editor.controls.extend([dd, speed_label, speed])

            elif t == "favorite":
                favs = FavoritesManager().get_favorites()
                dd = ft.Dropdown(
                    label="Favorito",
                    value=str(state.get("favorite") or (favs[0].get("id") if favs else "")),
                    options=[ft.DropdownOption(key=str(f.get("id")), text=f.get("name", "Favorito")) for f in favs],
                    color=Theme.TEXT,
                    bgcolor=Theme.BG,
                    border_color=Theme.STROKE,
                )
                def changed(ev=None):
                    state["favorite"] = dd.value or ""
                    update_preview()
                dd.on_change = changed
                changed()
                editor.controls.append(dd if favs else ft.Text("No hay favoritos creados.", color=Theme.MUTED))

            elif t == "custom_scene":
                scenes = CustomScenesManager().get_scenes()
                dd = ft.Dropdown(
                    label="Escena personalizada",
                    value=str(state.get("custom_scene") or (scenes[0].get("id") if scenes else "")),
                    options=[ft.DropdownOption(key=str(s.get("id")), text=s.get("name", "Escena")) for s in scenes],
                    color=Theme.TEXT,
                    bgcolor=Theme.BG,
                    border_color=Theme.STROKE,
                )
                def changed(ev=None):
                    state["custom_scene"] = dd.value or ""
                    update_preview()
                dd.on_change = changed
                changed()
                editor.controls.append(dd if scenes else ft.Text("No hay escenas personalizadas.", color=Theme.MUTED))

            elif t == "routine":
                routines = [r for r in RoutinesManager().get_routines() if str(r.get("id")) != str(current_routine_id or "")]
                dd = ft.Dropdown(
                    label="Rutina",
                    value=str(state.get("routine") or (routines[0].get("id") if routines else "")),
                    options=[ft.DropdownOption(key=str(r.get("id")), text=r.get("name", "Rutina")) for r in routines],
                    color=Theme.TEXT,
                    bgcolor=Theme.BG,
                    border_color=Theme.STROKE,
                )
                def changed(ev=None):
                    state["routine"] = dd.value or ""
                    update_preview()
                dd.on_change = changed
                changed()
                editor.controls.append(dd if routines else ft.Text("No hay otras rutinas disponibles.", color=Theme.MUTED))

            elif t == "wait":
                label = ft.Text("", color=Theme.TEXT, weight=ft.FontWeight.W_600)
                slider = ft.Slider(min=0, max=3000, value=_clamp(state.get("wait", 250), 0, 3000), divisions=30, active_color=Theme.MUTED, thumb_color="white", expand=True)
                def changed(ev=None):
                    state["wait"] = int(slider.value)
                    label.value = f"Esperar {state['wait']}ms"
                    update_preview(); supdate(label)
                slider.on_change = changed
                changed()
                editor.controls.extend([label, slider])

            elif t == "target_mode":
                dd = ft.Dropdown(
                    label="Destino",
                    value=str(state.get("target_mode", "single")),
                    options=[ft.DropdownOption(key="single", text="Una ampolleta"), ft.DropdownOption(key="all", text="Todas")],
                    color=Theme.TEXT,
                    bgcolor=Theme.BG,
                    border_color=Theme.STROKE,
                )
                def changed(ev=None):
                    state["target_mode"] = dd.value or "single"
                    update_preview()
                dd.on_change = changed
                changed()
                editor.controls.append(dd)

            update_preview()
            supdate(editor)

        kind.on_change = render
        render()

        def save(e):
            action_out = self._state_to_action(state)
            on_save(action_out)
            self.page.pop_dialog()

        dlg = ft.AlertDialog(
            title=ft.Text("Editar acción" if action else "Agregar acción", color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=ft.Container(
                width=540,
                height=540,
                content=ft.Column(
                    [
                        ft.Row([preview, ft.Column([kind, summary], spacing=6, expand=True)], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Divider(height=8, color=Theme.STROKE),
                        ft.Container(content=editor, expand=True),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton("Guardar acción", bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    def _action_to_state(self, action: dict[str, Any]) -> dict[str, Any]:
        kind = str(action.get("type") or "brightness")
        value = action.get("value")
        st: dict[str, Any] = {"type": kind, "brightness": 70, "delta": 10, "rgb": "#ff0000", "white_percent": 50, "kelvin": 4000, "scene": 18, "speed": 100, "wait": 250, "target_mode": "single", "favorite": "", "custom_scene": "", "routine": ""}
        if kind == "brightness": st["brightness"] = _clamp(_safe_int(value, 70), 10, 100)
        elif kind == "brightness_delta": st["delta"] = _clamp(_safe_int(value, 10), -50, 50)
        elif kind == "rgb": st["rgb"] = value if isinstance(value, str) else "#{:02x}{:02x}{:02x}".format(*self._rgb_tuple(value))
        elif kind == "white_percent": st["white_percent"] = _clamp(_safe_int(value, 50), 0, 100)
        elif kind == "white_kelvin": st["kelvin"] = _safe_int(value, 4000)
        elif kind == "scene":
            st["scene"] = _safe_int(value.get("sceneId", 18) if isinstance(value, dict) else value, 18)
            st["speed"] = _safe_int(value.get("speed", 100) if isinstance(value, dict) else action.get("speed", 100), 100)
        elif kind == "favorite": st["favorite"] = str(value or action.get("id") or "")
        elif kind == "custom_scene": st["custom_scene"] = str(value or action.get("id") or "")
        elif kind == "routine": st["routine"] = str(value or action.get("id") or "")
        elif kind == "wait": st["wait"] = _clamp(_safe_int(value if value is not None else action.get("ms"), 250), 0, 5000)
        elif kind == "target_mode": st["target_mode"] = "all" if str(value).lower() in {"all", "todas", "todos"} else "single"
        st["h"], st["s"], st["v"] = _hsv_from_hex(st["rgb"])
        return st

    def _state_to_action(self, st: dict[str, Any]) -> dict[str, Any]:
        t = str(st.get("type") or "brightness")
        if t in {"turn_on", "turn_off", "toggle"}:
            return {"type": t}
        if t == "brightness":
            return {"type": "brightness", "value": _clamp(_safe_int(st.get("brightness"), 70), 10, 100)}
        if t == "brightness_delta":
            return {"type": "brightness_delta", "value": _clamp(_safe_int(st.get("delta"), 10), -50, 50)}
        if t == "rgb":
            return {"type": "rgb", "value": str(st.get("rgb") or "#ff0000").lower()}
        if t == "white_percent":
            return {"type": "white_percent", "value": _clamp(_safe_int(st.get("white_percent"), 50), 0, 100)}
        if t == "white_kelvin":
            return {"type": "white_kelvin", "value": _safe_int(st.get("kelvin"), 4000)}
        if t == "scene":
            return {"type": "scene", "value": {"sceneId": _safe_int(st.get("scene"), 18), "speed": _clamp(_safe_int(st.get("speed"), 100), 20, 200)}}
        if t == "favorite":
            return {"type": "favorite", "value": str(st.get("favorite") or "")}
        if t == "custom_scene":
            return {"type": "custom_scene", "value": str(st.get("custom_scene") or "")}
        if t == "routine":
            return {"type": "routine", "value": str(st.get("routine") or "")}
        if t == "wait":
            return {"type": "wait", "value": _clamp(_safe_int(st.get("wait"), 250), 0, 5000)}
        if t == "target_mode":
            return {"type": "target_mode", "value": "all" if st.get("target_mode") == "all" else "single"}
        return {"type": "brightness", "value": 70}

    # ------------------------------------------------------------------ #
    # Helpers de rangos / colores
    # ------------------------------------------------------------------ #
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

    def _rgb_tuple(self, value: Any) -> tuple[int, int, int]:
        if isinstance(value, str):
            parsed = _parse_rgb(value)
            if parsed:
                return parsed
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            return _clamp(_safe_int(value[0], 255), 0, 255), _clamp(_safe_int(value[1], 0), 0, 255), _clamp(_safe_int(value[2], 0), 0, 255)
        if isinstance(value, dict):
            if "hex" in value:
                return self._rgb_tuple(value.get("hex"))
            return _clamp(_safe_int(value.get("r"), 255), 0, 255), _clamp(_safe_int(value.get("g"), 0), 0, 255), _clamp(_safe_int(value.get("b"), 0), 0, 255)
        return 255, 0, 0

    def sync_state(self, state: dict):
        # Rutinas no necesita sincronizar cada tick; evita repintados.
        pass
