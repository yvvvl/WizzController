from __future__ import annotations

import re
from typing import Any

import flet as ft

from config.routines_manager import RoutinesManager
from core.action_sequence import ActionSequenceExecutor
from ui.theme import Theme, mounted, supdate

ACTION_LABELS = {
    "turn_on": "Encender",
    "turn_off": "Apagar",
    "toggle": "Alternar",
    "brightness": "Brillo %",
    "brightness_delta": "Brillo +/-",
    "rgb": "Color HEX",
    "white_kelvin": "Blanco Kelvin",
    "white_percent": "Blanco %",
    "scene": "Escena WiZ",
    "wait": "Esperar ms",
    "target_mode": "Destino",
}

ACTION_HINTS = {
    "turn_on": "sin valor",
    "turn_off": "sin valor",
    "toggle": "sin valor",
    "brightness": "10-100",
    "brightness_delta": "+10 / -10",
    "rgb": "#ff0000",
    "white_kelvin": "2200-6500",
    "white_percent": "0-100",
    "scene": "18",
    "wait": "250",
    "target_mode": "single / all",
}


def _icon(name: str):
    return getattr(ft.Icons, str(name or "AUTO_AWESOME_ROUNDED"), ft.Icons.AUTO_AWESOME_ROUNDED)


class RoutinesPanel(ft.Column):
    """Rutinas compuestas: presets manuales sin programación por hora."""

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
                        ft.Text("Presets compuestos para voz, hotkeys y acciones rápidas", color=Theme.MUTED, size=13),
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
                    ft.Text("Sin horarios: estas rutinas se activan manualmente, por voz, hotkey o favoritos.", color=Theme.MUTED, size=12, expand=True),
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
        self.list_view.controls.clear()
        routines = self.manager.get_routines()
        if not routines:
            self.list_view.controls.append(ft.Text("No hay rutinas.", color=Theme.MUTED, size=13))
        for routine in routines:
            self.list_view.controls.append(self._routine_card(routine))
        supdate(self.list_view)

    def _routine_card(self, r: dict[str, Any]):
        color = str(r.get("color") or Theme.PRIMARY)
        actions = r.get("actions") if isinstance(r.get("actions"), list) else []
        summary = "  ·  ".join(self._action_text(a) for a in actions[:4])
        if len(actions) > 4:
            summary += f"  ·  +{len(actions) - 4}"
        return ft.Container(
            padding=14,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(_icon(r.get("icon")), color=color, size=22),
                        width=46,
                        height=46,
                        border_radius=14,
                        bgcolor=ft.Colors.with_opacity(0.15, color),
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

    def _action_text(self, a: dict[str, Any]) -> str:
        kind = str(a.get("type") or "")
        value = a.get("value")
        if kind == "turn_on": return "Encender"
        if kind == "turn_off": return "Apagar"
        if kind == "brightness": return f"Brillo {value}%"
        if kind == "rgb": return f"Color {value}"
        if kind == "white_kelvin": return f"{value}K"
        if kind == "white_percent": return f"Blanco {value}%"
        if kind == "scene":
            sid = value.get("sceneId") if isinstance(value, dict) else value
            return f"Escena {sid}"
        if kind == "wait": return f"Esperar {value}ms"
        if kind == "target_mode": return "Una" if value == "single" else "Todas"
        return ACTION_LABELS.get(kind, kind)

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
        self.manager.add_routine("Rutina capturada", actions, "Creada desde el estado actual", "#5b8cff", "CAMERA_ALT_ROUNDED")
        self._render()

    # ------------------------------------------------------------------ #
    def _open_editor(self, routine: dict[str, Any] | None = None):
        if not mounted(self):
            return
        is_new = routine is None
        routine = routine or {"name": "", "description": "", "color": "#5b8cff", "actions": [{"type": "turn_on"}, {"type": "brightness", "value": 70}]}

        name = ft.TextField(label="Nombre", value=str(routine.get("name", "")), dense=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        desc = ft.TextField(label="Descripción", value=str(routine.get("description", "")), dense=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        color = ft.TextField(label="Color HEX", value=str(routine.get("color", "#5b8cff")), dense=True, width=150, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        rows = ft.Column(spacing=8)
        row_controls: list[tuple[ft.Dropdown, ft.TextField]] = []

        def add_row(action: dict[str, Any] | None = None):
            action = action or {"type": "brightness", "value": 50}
            kind = str(action.get("type") or "brightness")
            val = self._value_to_text(action)
            dd = ft.Dropdown(
                options=[ft.DropdownOption(key=k, text=v) for k, v in ACTION_LABELS.items()],
                value=kind if kind in ACTION_LABELS else "brightness",
                dense=True,
                width=190,
                color=Theme.TEXT,
                bgcolor=Theme.BG,
                border_color=Theme.STROKE,
            )
            vf = ft.TextField(label="Valor", hint_text=ACTION_HINTS.get(kind, ""), value=val, dense=True, width=180, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

            def remove_row(e):
                try:
                    rows.controls.remove(container)
                    row_controls.remove((dd, vf))
                    supdate(rows)
                except Exception:
                    pass

            container = ft.Container(
                padding=8,
                border_radius=12,
                bgcolor=Theme.CARD_HI,
                border=ft.Border.all(1, Theme.STROKE),
                content=ft.Row([dd, vf, ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, on_click=remove_row)], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            )
            rows.controls.append(container)
            row_controls.append((dd, vf))

        for a in routine.get("actions", []):
            if isinstance(a, dict):
                add_row(a)
        if not row_controls:
            add_row()

        def save(e):
            actions = [self._row_to_action(dd.value, vf.value) for dd, vf in row_controls]
            actions = [a for a in actions if a]
            final_color = color.value or "#5b8cff"
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", final_color):
                final_color = "#5b8cff"
            if is_new:
                self.manager.add_routine(name.value or "Nueva rutina", actions, desc.value or "", final_color)
            else:
                self.manager.update_routine(str(routine.get("id")), name=name.value or "Rutina", description=desc.value or "", color=final_color, actions=actions)
            self.page.pop_dialog()
            self._render()

        dlg = ft.AlertDialog(
            bgcolor=Theme.SURFACE,
            title=ft.Text("Nueva rutina" if is_new else "Editar rutina", color=Theme.TEXT),
            content=ft.Container(
                width=520,
                height=520,
                content=ft.Column(
                    [
                        name,
                        desc,
                        color,
                        ft.Text("ACCIONES", style=Theme.LABEL),
                        ft.Container(content=rows, height=270),
                        ft.OutlinedButton("Agregar acción", icon=ft.Icons.ADD_ROUNDED, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)), on_click=lambda e: (add_row(), supdate(rows))),
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

    def _value_to_text(self, action: dict[str, Any]) -> str:
        kind = str(action.get("type") or "")
        value = action.get("value")
        if kind in {"turn_on", "turn_off", "toggle"}:
            return ""
        if kind == "scene" and isinstance(value, dict):
            return str(value.get("sceneId", 18))
        if kind == "rgb" and isinstance(value, (list, tuple)) and len(value) >= 3:
            return "#{:02x}{:02x}{:02x}".format(int(value[0]), int(value[1]), int(value[2]))
        return "" if value is None else str(value)

    def _row_to_action(self, kind: str | None, raw: str | None) -> dict[str, Any] | None:
        kind = str(kind or "").strip()
        raw = str(raw or "").strip()
        try:
            if kind in {"turn_on", "turn_off", "toggle"}:
                return {"type": kind}
            if kind in {"brightness", "brightness_delta", "white_percent", "wait"}:
                return {"type": kind, "value": int(float(raw or 0))}
            if kind == "rgb":
                h = raw if raw.startswith("#") else "#" + raw
                if not re.fullmatch(r"#[0-9a-fA-F]{6}", h):
                    h = "#ff0000"
                return {"type": "rgb", "value": h.lower()}
            if kind == "white_kelvin":
                return {"type": "white_kelvin", "value": int(float(raw or 4000))}
            if kind == "scene":
                return {"type": "scene", "value": {"sceneId": int(float(raw or 18)), "speed": 100}}
            if kind == "target_mode":
                return {"type": "target_mode", "value": "all" if raw.lower() in {"all", "todas", "todos"} else "single"}
        except Exception:
            return None
        return None

    def sync_state(self, state: dict):
        # No necesita sincronizar controles en tiempo real.
        pass
