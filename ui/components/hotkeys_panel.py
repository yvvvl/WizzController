from __future__ import annotations

import colorsys
import threading
import time

import flet as ft

from config.hotkeys_manager import HotkeysManager
from ui.theme import Theme, mounted, supdate

EO = ft.AnimationCurve.EASE_OUT

POPULAR_COLORS = [
    ("Rojo", "#ff0000"),
    ("Naranjo", "#ff7f00"),
    ("Amarillo", "#ffd000"),
    ("Verde", "#00ff40"),
    ("Cian", "#00d5ff"),
    ("Azul", "#0055ff"),
    ("Morado", "#7f00ff"),
    ("Rosa", "#ff4fa3"),
    ("Blanco", "#ffffff"),
    ("Cálido", "#ffbf75"),
]


class HotkeysPanel(ft.Column):
    """Fase 10: panel estable de hotkeys.

    Evita los controles que estaban provocando el bloque gris en Flet:
    - sin Row(wrap=True)
    - sin Stack
    - sin ExpansionTile
    - sin controles expandibles dentro de filas complejas
    - sin picker basado en gestos

    Mantiene color personalizado con selector simple: colores rápidos + tono/intensidad/brillo.
    """

    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=16, expand=True)
        self.wiz = wiz
        self.manager = HotkeysManager(wiz)
        self.actions: list[dict[str, str]] = []
        self.recording = False

        self.hue = 0.0
        self.sat = 100.0
        self.val = 100.0
        self.custom_hex = "#ff0000"

        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        self.status_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=Theme.MUTED)
        self.status_text = ft.Text("", color=Theme.MUTED, size=12)
        self.enabled_switch = ft.Switch(
            value=self.manager.enabled(),
            active_color=Theme.PRIMARY,
            on_change=self._enabled_changed,
        )

        header = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Hotkeys", style=Theme.H1),
                                ft.Text("Creador simple de atajos globales", color=Theme.MUTED, size=13),
                            ],
                            spacing=2,
                        ),
                        ft.Container(width=18),
                        self.status_dot,
                        self.status_text,
                        ft.Text("Activo", color=Theme.MUTED, size=12),
                        self.enabled_switch,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                )
            ]
        )

        self.category_dropdown = ft.Dropdown(
            label="1. Categoría",
            options=[],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            dense=True,
            width=260,
            on_select=self._category_changed,
        )
        self.action_dropdown = ft.Dropdown(
            label="2. Acción",
            options=[],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            dense=True,
            width=320,
            on_select=self._action_changed,
        )
        self.combo_field = ft.TextField(
            label="3. Atajo",
            hint_text="ctrl+alt+l",
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            dense=True,
            width=260,
        )

        self.record_btn = ft.ElevatedButton(
            "Grabar teclas",
            icon=ft.Icons.KEYBOARD_ROUNDED,
            bgcolor=Theme.PRIMARY,
            color="white",
            on_click=self._record_hotkey,
        )
        self.save_btn = ft.ElevatedButton(
            "Guardar",
            icon=ft.Icons.SAVE_ROUNDED,
            bgcolor=Theme.PRIMARY_D,
            color="white",
            on_click=self._save_hotkey,
        )
        self.test_btn = ft.OutlinedButton(
            "Probar",
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
            on_click=self._test_action,
        )

        self.color_preview = ft.Container(
            width=58,
            height=58,
            border_radius=16,
            bgcolor=self.custom_hex,
            border=ft.Border.all(2, ft.Colors.with_opacity(0.35, "white")),
        )
        self.hex_label = ft.Text(self.custom_hex.upper(), color=Theme.TEXT, size=13, weight=ft.FontWeight.W_600)
        self.hue_slider = ft.Slider(
            min=0,
            max=360,
            value=0,
            divisions=36,
            active_color=Theme.PRIMARY,
            thumb_color="white",
            on_change=self._hsv_changed,
            width=520,
        )
        self.sat_slider = ft.Slider(
            min=0,
            max=100,
            value=100,
            divisions=20,
            active_color=Theme.ACCENT,
            thumb_color="white",
            on_change=self._hsv_changed,
            width=520,
        )
        self.val_slider = ft.Slider(
            min=10,
            max=100,
            value=100,
            divisions=18,
            active_color=Theme.ACCENT,
            thumb_color="white",
            on_change=self._hsv_changed,
            width=520,
        )
        self.hue_label = ft.Text("Rojo", color=Theme.MUTED, size=12, width=90)
        self.sat_label = ft.Text("100%", color=Theme.MUTED, size=12, width=50)
        self.val_label = ft.Text("100%", color=Theme.MUTED, size=12, width=50)
        self.hex_field = ft.TextField(
            label="HEX opcional",
            value=self.custom_hex,
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            dense=True,
            width=150,
            on_submit=self._hex_changed,
        )
        self.color_editor = self._color_editor()

        creator = self._card(
            ft.Column(
                [
                    ft.Text("CREADOR RÁPIDO", style=Theme.LABEL),
                    ft.Text("Elige acción, graba una combinación y guarda. Para colores, usa Color personalizado.", color=Theme.MUTED, size=12),
                    ft.Row([self.category_dropdown, self.action_dropdown], spacing=12),
                    ft.Row([self.combo_field, self.record_btn, self.save_btn, self.test_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    self.color_editor,
                    ft.Text("Ejemplos buenos: ctrl+alt+l, ctrl+alt+up, shift+f8. Evita alt+tab, win+l y combinaciones del sistema.", color=Theme.FAINT, size=11),
                ],
                spacing=12,
            )
        )

        self.quick_defaults = ft.Column(spacing=8)
        defaults = self._card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("PLANTILLAS", style=Theme.LABEL),
                            ft.Container(width=20),
                            ft.TextButton("Restaurar defaults", icon=ft.Icons.RESTART_ALT_ROUNDED, on_click=self._defaults),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.quick_defaults,
                ],
                spacing=10,
            )
        )

        self.list_view = ft.Column(spacing=8)
        assigned = self._card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("ATAJOS CONFIGURADOS", style=Theme.LABEL),
                            ft.Container(width=20),
                            ft.OutlinedButton("Re-registrar", icon=ft.Icons.REFRESH_ROUNDED, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)), on_click=self._rehook),
                            ft.OutlinedButton("Activar/Desactivar", icon=ft.Icons.POWER_SETTINGS_NEW_ROUNDED, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)), on_click=self._toggle_enabled),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.list_view,
                ],
                spacing=10,
            )
        )

        self.controls = [header, creator, defaults, assigned]
        self._render()

    # ------------------------------------------------------------------ #
    def _card(self, content):
        return ft.Container(
            content=content,
            padding=16,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )

    def _color_editor(self):
        row1 = ft.Row([self.color_preview, ft.Column([ft.Text("Color personalizado", color=Theme.TEXT, weight=ft.FontWeight.W_600, size=13), self.hex_label], spacing=4), self.hex_field], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        row2 = ft.Row([ft.Text("Tono", color=Theme.MUTED, size=12, width=80), self.hue_slider, self.hue_label], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        row3 = ft.Row([ft.Text("Intensidad", color=Theme.MUTED, size=12, width=80), self.sat_slider, self.sat_label], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        row4 = ft.Row([ft.Text("Brillo", color=Theme.MUTED, size=12, width=80), self.val_slider, self.val_label], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        swatch_rows = []
        for i in range(0, len(POPULAR_COLORS), 5):
            swatch_rows.append(
                ft.Row(
                    [
                        ft.Container(
                            width=94,
                            height=42,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                            border_radius=12,
                            bgcolor=ft.Colors.with_opacity(0.16, col),
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.35, col)),
                            content=ft.Row([
                                ft.Container(width=18, height=18, border_radius=9, bgcolor=col, border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white"))),
                                ft.Text(name, color=Theme.TEXT, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ], spacing=6),
                            on_click=lambda e, c=col: self._set_custom_hex(c),
                            ink=True,
                        )
                        for name, col in POPULAR_COLORS[i:i + 5]
                    ],
                    spacing=8,
                )
            )

        return ft.Container(
            visible=False,
            padding=14,
            border_radius=Theme.R_MD,
            bgcolor=ft.Colors.with_opacity(0.28, Theme.BG),
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column([row1, ft.Text("Colores rápidos", style=Theme.LABEL), *swatch_rows, row2, row3, row4], spacing=9),
        )

    # ------------------------------------------------------------------ #
    def _status_text(self):
        if not self.manager.available:
            return "keyboard no disponible"
        if not self.manager.enabled():
            return "desactivado"
        if self.manager.last_error:
            return "activo con advertencias"
        return "activo"

    def _render(self):
        self.actions = self.manager.list_actions()
        groups = []
        for action in self.actions:
            group = action.get("group", "General")
            if group not in groups:
                groups.append(group)
        self.category_dropdown.options = [ft.DropdownOption(key=g, text=g) for g in groups]
        if groups and self.category_dropdown.value not in groups:
            self.category_dropdown.value = groups[0]
        self._render_actions_for_category()
        self._render_defaults()
        self._render_list()
        self._sync_status()
        self._refresh_color_editor_visibility()
        supdate(self)

    def _sync_status(self):
        if self.manager.available and self.manager.enabled() and not self.manager.last_error:
            self.status_dot.bgcolor = Theme.SUCCESS
        elif self.manager.last_error:
            self.status_dot.bgcolor = Theme.WARNING
        else:
            self.status_dot.bgcolor = Theme.ERROR
        self.status_text.value = self._status_text()
        self.enabled_switch.value = self.manager.enabled()

    def _render_actions_for_category(self):
        group = self.category_dropdown.value
        actions = [a for a in self.actions if a.get("group") == group]
        self.action_dropdown.options = [ft.DropdownOption(key=a["id"], text=a["name"]) for a in actions]
        valid = [a["id"] for a in actions]
        if actions and self.action_dropdown.value not in valid:
            self.action_dropdown.value = actions[0]["id"]
        self._sync_combo_from_action()

    def _sync_combo_from_action(self):
        aid = self._selected_action_id()
        self.combo_field.value = self.manager.get_hotkey(aid) or ""

    def _render_defaults(self):
        presets = [
            [("Toggle", "toggle", "ctrl+alt+l"), ("Brillo +", "bri_up", "ctrl+alt+up"), ("Brillo -", "bri_down", "ctrl+alt+down")],
            [("Rojo", "color_red", "ctrl+alt+r"), ("Cálido", "white_warm", "ctrl+alt+w"), ("TV/Cine", "scene_18", "ctrl+alt+t")],
        ]
        self.quick_defaults.controls.clear()
        for row in presets:
            self.quick_defaults.controls.append(
                ft.Row(
                    [self._preset_card(label, aid, combo) for label, aid, combo in row],
                    spacing=10,
                )
            )

    def _preset_card(self, label: str, aid: str, combo: str):
        return ft.Container(
            width=180,
            height=60,
            padding=10,
            border_radius=12,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column([
                ft.Text(label, color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(combo, color=Theme.MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
            on_click=lambda e, a=aid, c=combo: self._set_preset(a, c),
            ink=True,
        )

    def _render_list(self):
        actions_by_id = {a["id"]: a for a in self.actions}
        hotkeys = self.manager.get_hotkeys()
        self.list_view.controls.clear()
        if not hotkeys:
            self.list_view.controls.append(ft.Text("No hay hotkeys asignadas.", color=Theme.MUTED, size=13))
            return
        for aid, combo in sorted(hotkeys.items()):
            action = actions_by_id.get(aid) or {"id": aid, "name": self._unknown_label(aid), "group": "Personalizado"}
            self.list_view.controls.append(self._hotkey_row(action, combo))

    def _unknown_label(self, aid: str) -> str:
        if aid.startswith("color_hex_"):
            raw = aid.removeprefix("color_hex_")[:6]
            return "Color #" + raw.upper()
        return aid

    def _hotkey_row(self, action: dict, combo: str):
        aid = action["id"]
        icon_box = ft.Container(
            content=ft.Icon(ft.Icons.KEYBOARD_ROUNDED, color=Theme.PRIMARY, size=18),
            width=38,
            height=38,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.12, Theme.PRIMARY),
            alignment=ft.Alignment.CENTER,
        )
        if aid.startswith("color_hex_"):
            raw = aid.removeprefix("color_hex_")[:6]
            if len(raw) == 6:
                icon_box = ft.Container(width=38, height=38, border_radius=12, bgcolor="#" + raw, border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white")))

        return ft.Container(
            padding=12,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [
                    icon_box,
                    ft.Container(width=250, content=ft.Column([
                        ft.Text(action.get("name", aid), color=Theme.TEXT, weight=ft.FontWeight.W_600, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(action.get("group", ""), color=Theme.MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=2)),
                    ft.Container(width=180, content=ft.Text(combo, color=Theme.TEXT, weight=ft.FontWeight.BOLD, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), bgcolor=Theme.BG, border=ft.Border.all(1, Theme.STROKE), border_radius=10, padding=ft.Padding.symmetric(horizontal=12, vertical=8)),
                    ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_color=Theme.PRIMARY, tooltip="Probar", on_click=lambda e, x=aid: self.manager.execute_action(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, tooltip="Quitar", on_click=lambda e, x=aid: self._remove(x)),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    # ------------------------------------------------------------------ #
    def _selected_action_id(self) -> str:
        aid = self.action_dropdown.value or "toggle"
        if aid == "color_custom":
            return self._custom_color_action_id()
        return aid

    def _category_changed(self, e):
        self._render_actions_for_category()
        self._refresh_color_editor_visibility()
        supdate(self.category_dropdown)
        supdate(self.action_dropdown)
        supdate(self.combo_field)
        supdate(self.color_editor)

    def _action_changed(self, e):
        self._sync_combo_from_action()
        self._refresh_color_editor_visibility()
        supdate(self.action_dropdown)
        supdate(self.combo_field)
        supdate(self.color_editor)

    def _refresh_color_editor_visibility(self):
        self.color_editor.visible = self.action_dropdown.value == "color_custom"

    def _set_preset(self, aid: str, combo: str):
        group = self._group_for_action(aid)
        self.category_dropdown.value = group
        self._render_actions_for_category()
        self.action_dropdown.value = aid
        self.combo_field.value = combo
        self._refresh_color_editor_visibility()
        supdate(self.category_dropdown)
        supdate(self.action_dropdown)
        supdate(self.combo_field)
        supdate(self.color_editor)

    def _group_for_action(self, aid: str) -> str:
        for action in self.actions:
            if action.get("id") == aid:
                return action.get("group", "General")
        return "General"

    def _record_hotkey(self, e):
        if self.recording:
            return
        self.recording = True
        self.record_btn.text = "Presiona teclas..."
        self.record_btn.disabled = True
        supdate(self.record_btn)

        def worker():
            try:
                time.sleep(0.2)
                combo = self.manager.read_hotkey_blocking()
                if combo and combo != "esc":
                    self.combo_field.value = combo
            finally:
                self.recording = False
                self.record_btn.text = "Grabar teclas"
                self.record_btn.disabled = False
                supdate(self.combo_field)
                supdate(self.record_btn)

        threading.Thread(target=worker, daemon=True).start()

    def _save_hotkey(self, e):
        aid = self._selected_action_id()
        combo = (self.combo_field.value or "").strip()
        if not aid or not combo:
            return
        self.manager.set_hotkey(aid, combo)
        self._render()

    def _test_action(self, e):
        self.manager.execute_action(self._selected_action_id())
        self._sync_status()
        supdate(self.status_dot)
        supdate(self.status_text)

    def _remove(self, aid: str):
        self.manager.remove_hotkey(aid)
        self._render()

    def _defaults(self, e):
        self.manager.reset_defaults()
        self._render()

    def _rehook(self, e):
        self.manager.apply_hooks()
        self._render()

    def _toggle_enabled(self, e=None):
        self.manager.set_enabled(not self.manager.enabled())
        self._render()

    def _enabled_changed(self, e):
        self.manager.set_enabled(bool(self.enabled_switch.value))
        self._render()

    # ------------------------------------------------------------------ #
    def _custom_color_action_id(self) -> str:
        return "color_hex_" + self.custom_hex.lstrip("#").lower()[:6]

    def _hsv_to_hex(self) -> str:
        r, g, b = colorsys.hsv_to_rgb(self.hue / 360.0, self.sat / 100.0, self.val / 100.0)
        return f"#{int(round(r * 255)):02x}{int(round(g * 255)):02x}{int(round(b * 255)):02x}"

    def _hex_to_hsv(self, hex_color: str):
        h = str(hex_color or "").strip().lstrip("#")[:6]
        if len(h) != 6:
            return None
        try:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            return None
        hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        return hh * 360.0, ss * 100.0, max(10.0, vv * 100.0)

    def _hue_name(self, hue: float) -> str:
        names = [
            (15, "Rojo"), (45, "Naranjo"), (75, "Amarillo"), (150, "Verde"),
            (195, "Cian"), (255, "Azul"), (300, "Morado"), (345, "Rosa"), (361, "Rojo"),
        ]
        for limit, name in names:
            if hue <= limit:
                return name
        return "Rojo"

    def _set_custom_hsv(self, hue=None, sat=None, val=None):
        if hue is not None:
            self.hue = max(0.0, min(360.0, float(hue)))
        if sat is not None:
            self.sat = max(0.0, min(100.0, float(sat)))
        if val is not None:
            self.val = max(10.0, min(100.0, float(val)))
        self.custom_hex = self._hsv_to_hex()
        self.color_preview.bgcolor = self.custom_hex
        self.hex_label.value = self.custom_hex.upper()
        self.hex_field.value = self.custom_hex
        self.hue_slider.value = self.hue
        self.sat_slider.value = self.sat
        self.val_slider.value = self.val
        self.hue_label.value = self._hue_name(self.hue)
        self.sat_label.value = f"{int(round(self.sat))}%"
        self.val_label.value = f"{int(round(self.val))}%"
        if self.action_dropdown.value == "color_custom":
            self.combo_field.value = self.manager.get_hotkey(self._custom_color_action_id()) or self.combo_field.value
        supdate(self.color_editor)
        supdate(self.combo_field)

    def _set_custom_hex(self, hex_color: str):
        parsed = self._hex_to_hsv(hex_color)
        if not parsed:
            return
        self.hue, self.sat, self.val = parsed
        self.custom_hex = "#" + str(hex_color).strip().lstrip("#")[:6].lower()
        self._set_custom_hsv(self.hue, self.sat, self.val)

    def _hsv_changed(self, e):
        self._set_custom_hsv(self.hue_slider.value, self.sat_slider.value, self.val_slider.value)

    def _hex_changed(self, e):
        self._set_custom_hex(self.hex_field.value)
