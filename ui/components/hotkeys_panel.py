from __future__ import annotations

import colorsys
import threading
import time

import flet as ft

from config.hotkeys_manager import HotkeysManager
from localization import LocalizationManager
from ui.responsive import PANEL_BREAKPOINTS, Viewport, dialog_dimensions
from ui.theme import Theme, mounted, supdate

EO = ft.AnimationCurve.EASE_OUT

POPULAR_COLORS = [
    ("color.name.red", "#ff0000"),
    ("color.name.orange", "#ff7f00"),
    ("color.name.yellow", "#ffd000"),
    ("color.name.green", "#00ff40"),
    ("color.name.cyan", "#00d5ff"),
    ("color.name.blue", "#0055ff"),
    ("color.name.violet", "#7f00ff"),
    ("color.name.pink", "#ff4fa3"),
    ("white.name.neutral", "#ffffff"),
    ("white.name.warm", "#ffbf75"),
]

SAFE_PRESETS = [
    ("hotkeys.preset.toggle", "toggle", "ctrl+alt+l"),
    ("hotkeys.preset.bri_up", "bri_up", "ctrl+alt+up"),
    ("hotkeys.preset.bri_down", "bri_down", "ctrl+alt+down"),
    ("hotkeys.preset.red", "color_red", "ctrl+alt+r"),
    ("hotkeys.preset.cinema", "scene_18", "ctrl+alt+t"),
    ("hotkeys.preset.night", "routine_night", "ctrl+alt+n"),
]


def _icon(name: str, fallback=ft.Icons.KEYBOARD_ROUNDED):
    return getattr(ft.Icons, name, fallback)


class HotkeysPanel(ft.Column):
    """Editor responsive para el servicio global de hotkeys.

    El manager sigue viviendo en ``main.py``. Este panel solo configura, prueba
    y muestra el backend activo; ningún resize vuelve a registrar hooks.
    """

    def __init__(self, wiz, manager: HotkeysManager | None = None, i18n=None):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=16, expand=True)
        self.wiz = wiz
        self.i18n = i18n or LocalizationManager(preference="es")
        self.manager = manager or HotkeysManager(wiz, i18n=self.i18n)
        self.manager.i18n = self.i18n
        self.actions: list[dict] = []
        self.filtered_actions: list[dict] = []
        self.recording = False
        self._viewport = Viewport(900, 720)
        self._cards: list[ft.Container] = []

        self.hue = 0.0
        self.sat = 100.0
        self.val = 100.0
        self.custom_hex = "#ff0000"

        self._build()

    # ------------------------------------------------------------------ #
    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def set_language(self, language: str | None = None) -> None:
        self.manager.i18n = self.i18n
        self._build()
        if mounted(self):
            supdate(self)

    def _build(self):
        self._cards = []
        self.status_dot = ft.Container(width=9, height=9, border_radius=5, bgcolor=Theme.MUTED)
        self.status_text = ft.Text("", color=Theme.MUTED, size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
        self.warning_text = ft.Text("", color=Theme.WARNING, size=12, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS)

        self.enabled_switch = ft.Switch(value=self.manager.enabled(), active_color=Theme.PRIMARY, on_change=self._enabled_changed)
        self.suppress_switch = ft.Switch(value=self.manager.suppress_enabled(), active_color=Theme.PRIMARY, on_change=self._suppress_changed)
        self.release_switch = ft.Switch(value=self.manager.trigger_on_release(), active_color=Theme.PRIMARY, on_change=self._release_changed)
        self.cooldown_slider = ft.Slider(
            min=120,
            max=900,
            value=self.manager.cooldown_ms(),
            divisions=13,
            active_color=Theme.ACCENT,
            thumb_color="white",
            on_change=self._cooldown_changed,
            expand=True,
        )
        self.cooldown_label = ft.Text(self._t("hotkeys.ms_value", value=self.manager.cooldown_ms()), color=Theme.MUTED, size=12)
        self.rehook_btn = ft.OutlinedButton(
            self._t("hotkeys.reregister"),
            icon=ft.Icons.REFRESH_ROUNDED,
            style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
            on_click=self._rehook,
        )

        status_chip = ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=18,
            bgcolor=ft.Colors.with_opacity(0.10, Theme.PRIMARY),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.24, Theme.PRIMARY)),
            content=ft.Row([self.status_dot, self.status_text], spacing=9, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )
        self.header = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(self._t("hotkeys.title"), style=Theme.H1),
                            ft.Text(self._t("hotkeys.subtitle"), color=Theme.MUTED, size=13),
                        ],
                        spacing=2,
                    ),
                    col={"xs": 12, "md": 7},
                ),
                ft.Container(content=status_chip, col={"xs": 12, "md": 5}, alignment=ft.Alignment.CENTER_RIGHT),
            ],
        )

        toggles = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=12,
            controls=[
                self._setting_toggle(self._t("hotkeys.enabled"), self.enabled_switch, self._t("hotkeys.enabled_help")),
                self._setting_toggle(self._t("hotkeys.suppress"), self.suppress_switch, self._t("hotkeys.suppress_help")),
                self._setting_toggle(self._t("hotkeys.release"), self.release_switch, self._t("hotkeys.release_help")),
            ],
        )
        cooldown = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=10,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=ft.Text(self._t("hotkeys.debounce"), color=Theme.MUTED, size=12), col={"xs": 12, "sm": 2}),
                ft.Container(content=self.cooldown_slider, col={"xs": 9, "sm": 4, "lg": 7}),
                ft.Container(content=self.cooldown_label, col={"xs": 3, "sm": 2, "lg": 1}, alignment=ft.Alignment.CENTER),
                ft.Container(content=self.rehook_btn, col={"xs": 12, "sm": 4, "lg": 2}, alignment=ft.Alignment.CENTER_RIGHT),
            ],
        )
        status_card = self._card(
            ft.Column(
                [ft.Text(self._t("common.status"), style=Theme.LABEL), toggles, cooldown, self.warning_text],
                spacing=10,
            )
        )

        self.category_dropdown = ft.Dropdown(
            label=self._t("hotkeys.category"),
            options=[],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            dense=True,
            on_select=self._category_changed,
        )
        self.search_field = ft.TextField(
            label=self._t("hotkeys.search_action"),
            hint_text=self._t("hotkeys.search_hint"),
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            dense=True,
            on_change=self._search_changed,
        )
        self.action_dropdown = ft.Dropdown(
            label=self._t("hotkeys.action"),
            options=[],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            dense=True,
            on_select=self._action_changed,
        )
        self.combo_field = ft.TextField(
            label=self._t("hotkeys.shortcut"),
            hint_text=self._t("hotkeys.shortcut_hint"),
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            dense=True,
            on_change=self._combo_changed,
        )
        self.validation_text = ft.Text("", color=Theme.MUTED, size=12, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS)

        self.record_btn = ft.ElevatedButton(self._t("common.record"), icon=ft.Icons.KEYBOARD_ROUNDED, bgcolor=Theme.PRIMARY, color="white", on_click=self._record_hotkey)
        self.save_btn = ft.ElevatedButton(self._t("common.save"), icon=ft.Icons.SAVE_ROUNDED, bgcolor=Theme.PRIMARY_D, color="white", on_click=self._save_hotkey)
        self.test_btn = ft.OutlinedButton(self._t("common.test"), icon=ft.Icons.PLAY_ARROW_ROUNDED, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)), on_click=self._test_action)
        self.remove_selected_btn = ft.OutlinedButton(self._t("common.remove"), icon=ft.Icons.DELETE_OUTLINE_ROUNDED, style=ft.ButtonStyle(color=Theme.ERROR, side=ft.BorderSide(1, Theme.STROKE)), on_click=lambda e: self._remove(self._selected_action_id()))

        self.color_preview = ft.Container(width=54, height=54, border_radius=16, bgcolor=self.custom_hex, border=ft.Border.all(2, ft.Colors.with_opacity(0.35, "white")))
        self.hex_label = ft.Text(self.custom_hex.upper(), color=Theme.TEXT, size=13, weight=ft.FontWeight.W_600)
        self.hex_field = ft.TextField(label=self._t("favorites.hex"), value=self.custom_hex, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE, dense=True, on_submit=self._hex_changed)
        self.hue_slider = self._slider(0, 360, 0, 36, self._hsv_changed)
        self.sat_slider = self._slider(0, 100, 100, 20, self._hsv_changed)
        self.val_slider = self._slider(10, 100, 100, 18, self._hsv_changed)
        self.hue_label = ft.Text(self._t("color.name.red"), color=Theme.MUTED, size=12)
        self.sat_label = ft.Text(self._t("common.percent_value", value=100), color=Theme.MUTED, size=12)
        self.val_label = ft.Text(self._t("common.percent_value", value=100), color=Theme.MUTED, size=12)
        self.color_editor = self._color_editor()

        selector_row = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=10,
            controls=[
                ft.Container(content=self.category_dropdown, col={"xs": 12, "sm": 6}),
                ft.Container(content=self.search_field, col={"xs": 12, "sm": 6}),
                ft.Container(content=self.action_dropdown, col={"xs": 12}),
            ],
        )
        action_buttons = ft.Row(
            [self.record_btn, self.save_btn, self.test_btn, self.remove_selected_btn],
            spacing=8,
            run_spacing=8,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        combo_row = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=10,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=self.combo_field, col={"xs": 12, "md": 4}),
                ft.Container(content=action_buttons, col={"xs": 12, "md": 8}),
            ],
        )
        creator = self._card(
            ft.Column(
                [
                    ft.Text(self._t("hotkeys.create_section"), style=Theme.LABEL),
                    ft.Text(
                        self._t("hotkeys.create_help"),
                        color=Theme.MUTED,
                        size=12,
                    ),
                    selector_row,
                    combo_row,
                    self.validation_text,
                    self.color_editor,
                ],
                spacing=12,
            )
        )

        self.quick_defaults = ft.ResponsiveRow(breakpoints=PANEL_BREAKPOINTS, spacing=10, run_spacing=10)
        defaults_header = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=ft.Text(self._t("hotkeys.templates_section"), style=Theme.LABEL), col={"xs": 12, "sm": 7}),
                ft.Container(
                    content=ft.TextButton(self._t("common.restore_defaults"), icon=ft.Icons.RESTART_ALT_ROUNDED, on_click=self._defaults),
                    col={"xs": 12, "sm": 5},
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
        )
        defaults = self._card(ft.Column([defaults_header, self.quick_defaults], spacing=10))

        self.list_view = ft.Column(spacing=8)
        assigned_header = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=ft.Text(self._t("hotkeys.assigned_section"), style=Theme.LABEL), col={"xs": 12, "sm": 7}),
                ft.Container(
                    content=ft.OutlinedButton(
                        self._t("common.export"),
                        icon=ft.Icons.CONTENT_COPY_ROUNDED,
                        style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
                        on_click=self._export_dialog,
                    ),
                    col={"xs": 12, "sm": 5},
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
        )
        assigned = self._card(ft.Column([assigned_header, self.list_view], spacing=10))

        self.controls = [self.header, status_card, creator, defaults, assigned]
        self._render()

    # ------------------------------------------------------------------ #
    def _card(self, content):
        card = ft.Container(
            content=content,
            padding=16,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )
        self._cards.append(card)
        return card

    def _slider(self, mn, mx, value, div, handler):
        return ft.Slider(
            min=mn,
            max=mx,
            value=value,
            divisions=div,
            active_color=Theme.ACCENT,
            thumb_color="white",
            on_change=handler,
            expand=True,
        )

    def _setting_toggle(self, title: str, switch: ft.Switch, subtitle: str = ""):
        texts = [ft.Text(title, color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600)]
        if subtitle:
            texts.append(ft.Text(subtitle, color=Theme.FAINT, size=10, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS))
        return ft.Container(
            col={"xs": 12, "sm": 6, "lg": 4},
            padding=11,
            border_radius=12,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [ft.Column(texts, spacing=1, expand=True), switch],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _color_editor(self):
        intro = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=self.color_preview, col={"xs": 3, "sm": 2}, alignment=ft.Alignment.CENTER_LEFT),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(self._t("hotkeys.custom_color"), color=Theme.TEXT, weight=ft.FontWeight.W_600, size=13),
                            self.hex_label,
                        ],
                        spacing=4,
                    ),
                    col={"xs": 9, "sm": 4},
                ),
                ft.Container(content=self.hex_field, col={"xs": 12, "sm": 6}),
            ],
        )
        self.color_swatches = ft.ResponsiveRow(breakpoints=PANEL_BREAKPOINTS, spacing=8, run_spacing=8)
        for key, col in POPULAR_COLORS:
            self.color_swatches.controls.append(self._swatch(self._t(key), col))
        sliders = ft.Column(
            [
                self._slider_row(self._t("hotkeys.hue"), self.hue_slider, self.hue_label),
                self._slider_row(self._t("hotkeys.intensity"), self.sat_slider, self.sat_label),
                self._slider_row(self._t("hotkeys.lightness"), self.val_slider, self.val_label),
            ],
            spacing=6,
        )
        return ft.Container(
            visible=False,
            padding=14,
            border_radius=Theme.R_MD,
            bgcolor=ft.Colors.with_opacity(0.26, Theme.BG),
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column(
                [intro, ft.Text(self._t("hotkeys.quick_colors"), style=Theme.LABEL), self.color_swatches, sliders],
                spacing=10,
            ),
        )

    def _slider_row(self, label: str, slider: ft.Slider, value: ft.Text):
        return ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=3,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(content=ft.Text(label, color=Theme.MUTED, size=12), col={"xs": 12, "sm": 2}),
                ft.Container(content=slider, col={"xs": 9, "sm": 8}),
                ft.Container(content=value, col={"xs": 3, "sm": 2}, alignment=ft.Alignment.CENTER),
            ],
        )

    def _swatch(self, name: str, col: str):
        return ft.Container(
            col={"xs": 6, "sm": 4, "md": 3, "lg": 2},
            height=44,
            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.16, col),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.35, col)),
            content=ft.Row(
                [
                    ft.Container(width=18, height=18, border_radius=9, bgcolor=col, border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white"))),
                    ft.Text(name, color=Theme.TEXT, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                ],
                spacing=6,
            ),
            on_click=lambda e, c=col: self._set_custom_hex(c),
            ink=True,
        )

    # ------------------------------------------------------------------ #
    def _status_text(self) -> str:
        if not self.manager.available:
            return self._t("hotkeys.unavailable")
        return self.manager.backend_status()

    def _render(self):
        self.actions = self.manager.list_actions()
        self._render_categories()
        self._render_actions_for_category()
        self._render_defaults()
        self._render_list()
        self._sync_status()
        self._sync_validation()
        self._refresh_color_editor_visibility()
        supdate(self)

    def _render_categories(self):
        groups: list[str] = []
        for action in self.actions:
            group = str(action.get("group") or self._t("hotkeys.group.general"))
            if group not in groups:
                groups.append(group)
        self.category_dropdown.options = [ft.DropdownOption(key=g, text=g) for g in groups]
        if groups and self.category_dropdown.value not in groups:
            self.category_dropdown.value = groups[0]

    def _sync_status(self):
        report = self.manager.registration_report()
        unresolved = bool(report.get("failed"))
        if self.manager.last_error:
            self.status_dot.bgcolor = Theme.ERROR
        elif unresolved:
            self.status_dot.bgcolor = Theme.WARNING
        elif self.manager.available and self.manager.enabled():
            self.status_dot.bgcolor = Theme.SUCCESS
        else:
            self.status_dot.bgcolor = Theme.ERROR
        self.status_text.value = self._status_text()
        self.enabled_switch.value = self.manager.enabled()
        self.suppress_switch.value = self.manager.suppress_enabled()
        self.release_switch.value = self.manager.trigger_on_release()
        self.cooldown_slider.value = self.manager.cooldown_ms()
        self.cooldown_label.value = self._t("hotkeys.ms_value", value=self.manager.cooldown_ms())
        self.warning_text.value = self.manager.last_error or self.manager.last_warning or ""
        self.warning_text.color = Theme.ERROR if self.manager.last_error else Theme.WARNING

    def _category_actions(self) -> list[dict]:
        group = self.category_dropdown.value
        query = (self.search_field.value or "").strip().lower()
        actions = [a for a in self.actions if a.get("group") == group]
        if query:
            actions = [a for a in self.actions if query in str(a.get("name", "")).lower() or query in str(a.get("group", "")).lower() or query in str(a.get("id", "")).lower()]
        return actions

    def _render_actions_for_category(self):
        self.filtered_actions = self._category_actions()
        self.action_dropdown.options = [ft.DropdownOption(key=a["id"], text=f"{a.get('name')}  ·  {a.get('group')}") for a in self.filtered_actions]
        valid = [a["id"] for a in self.filtered_actions]
        if self.filtered_actions and self.action_dropdown.value not in valid:
            self.action_dropdown.value = self.filtered_actions[0]["id"]
        self._sync_combo_from_action()

    def _sync_combo_from_action(self):
        aid = self._selected_action_id()
        self.combo_field.value = self.manager.get_hotkey(aid) or self.combo_field.value or ""
        self._sync_validation()

    def _sync_validation(self):
        combo = self.combo_field.value or ""
        if not combo:
            self.validation_text.value = self._t("hotkeys.choose_shortcut")
            self.validation_text.color = Theme.MUTED
            return
        ok, msg = self.manager.validate_hotkey(combo, self.i18n)
        conflict = self.manager.combo_conflict(combo, ignore_action=self._selected_action_id()) if ok else None
        if not ok:
            self.validation_text.value = msg
            self.validation_text.color = Theme.ERROR
        elif conflict:
            self.validation_text.value = self._t("hotkeys.conflict", action=conflict[1])
            self.validation_text.color = Theme.WARNING
        else:
            self.validation_text.value = self._t("hotkeys.valid")
            self.validation_text.color = Theme.SUCCESS

    def _render_defaults(self):
        self.quick_defaults.controls.clear()
        for key, aid, combo in SAFE_PRESETS:
            self.quick_defaults.controls.append(self._preset_card(self._t(key), aid, combo))

    def _preset_card(self, label: str, aid: str, combo: str):
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4},
            height=66,
            padding=11,
            border_radius=12,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column(
                [
                    ft.Text(label, color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(combo, color=Theme.MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ],
                spacing=2,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            on_click=lambda e, a=aid, c=combo: self._set_preset(a, c),
            ink=True,
        )

    def _render_list(self):
        rows = self.manager.configured_rows()
        self.list_view.controls.clear()
        if not rows:
            self.list_view.controls.append(ft.Text(self._t("hotkeys.empty"), color=Theme.MUTED, size=13))
            return
        for row in rows:
            self.list_view.controls.append(self._hotkey_row(row))

    def _hotkey_row(self, row: dict):
        aid = str(row.get("id"))
        combo = str(row.get("combo"))
        group = str(row.get("group", ""))
        name = str(row.get("name", aid))
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
                icon_box = ft.Container(
                    width=38,
                    height=38,
                    border_radius=12,
                    bgcolor="#" + raw,
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.35, "white")),
                )

        identity = ft.Row(
            [
                icon_box,
                ft.Column(
                    [
                        ft.Text(name, color=Theme.TEXT, weight=ft.FontWeight.W_600, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(group, color=Theme.MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        combo_box = ft.Container(
            content=ft.Text(combo, color=Theme.TEXT, weight=ft.FontWeight.BOLD, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            bgcolor=Theme.BG,
            border=ft.Border.all(1, Theme.STROKE),
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=12, vertical=9),
        )
        actions = ft.Row(
            [
                ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Theme.PRIMARY, tooltip=self._t("common.edit"), on_click=lambda e, x=aid: self._select_action(x)),
                ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_color=Theme.PRIMARY, tooltip=self._t("common.test"), on_click=lambda e, x=aid: self._test_specific(x)),
                ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, tooltip=self._t("common.remove"), on_click=lambda e, x=aid: self._remove(x)),
            ],
            spacing=1,
            wrap=True,
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.Container(
            padding=12,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.ResponsiveRow(
                breakpoints=PANEL_BREAKPOINTS,
                spacing=10,
                run_spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(content=identity, col={"xs": 12, "md": 5}),
                    ft.Container(content=combo_box, col={"xs": 12, "sm": 7, "md": 3}),
                    ft.Container(content=actions, col={"xs": 12, "sm": 5, "md": 4}, alignment=ft.Alignment.CENTER_RIGHT),
                ],
            ),
        )

    # ------------------------------------------------------------------ #
    def _selected_action_id(self) -> str:
        aid = self.action_dropdown.value or "toggle"
        if aid == "color_custom":
            return self._custom_color_action_id()
        return str(aid)

    def _category_changed(self, e):
        self._render_actions_for_category()
        self._refresh_color_editor_visibility()
        self._sync_validation()
        supdate(self)

    def _search_changed(self, e):
        self._render_actions_for_category()
        self._refresh_color_editor_visibility()
        supdate(self.action_dropdown)

    def _action_changed(self, e):
        self._sync_combo_from_action()
        self._refresh_color_editor_visibility()
        supdate(self)

    def _combo_changed(self, e):
        self._sync_validation()
        supdate(self.validation_text)

    def _refresh_color_editor_visibility(self):
        self.color_editor.visible = self.action_dropdown.value == "color_custom"

    def _select_action(self, aid: str):
        group = self._group_for_action(aid)
        self.category_dropdown.value = group
        self.search_field.value = ""
        self._render_actions_for_category()
        self.action_dropdown.value = aid
        self.combo_field.value = self.manager.get_hotkey(aid) or ""
        self._refresh_color_editor_visibility()
        self._sync_validation()
        supdate(self)

    def _set_preset(self, aid: str, combo: str):
        self._select_action(aid)
        self.combo_field.value = combo
        self._sync_validation()
        supdate(self)

    def _group_for_action(self, aid: str) -> str:
        if aid.startswith("color_hex_"):
            return self._t("hotkeys.group.custom_colors")
        for action in self.actions:
            if action.get("id") == aid:
                return str(action.get("group") or self._t("hotkeys.group.general"))
        if aid.startswith("routine_"):
            return self._t("hotkeys.group.routines")
        return self._t("hotkeys.group.general")

    # ------------------------------------------------------------------ #
    def _record_hotkey(self, e):
        if self.recording:
            return
        if not self.manager.can_record:
            self.manager.last_error = self.manager.dependency_message()
            self._render()
            return
        self.recording = True
        self.record_btn.text = self._t("hotkeys.recording")
        self.record_btn.disabled = True
        self.validation_text.value = self._t("hotkeys.recording_help")
        self.validation_text.color = Theme.PRIMARY
        supdate(self)

        def worker():
            try:
                time.sleep(0.2)
                combo = self.manager.read_hotkey_blocking()
                if combo:
                    self.combo_field.value = combo
            finally:
                self.recording = False
                self.record_btn.text = self._t("common.record")
                self.record_btn.disabled = False
                self._sync_validation()
                supdate(self)

        threading.Thread(target=worker, daemon=True).start()

    def _save_hotkey(self, e):
        aid = self._selected_action_id()
        combo = self.combo_field.value or ""
        result = self.manager.assign_hotkey(aid, combo)
        self.validation_text.value = result["message"]
        self.validation_text.color = Theme.SUCCESS if result["ok"] else Theme.ERROR
        self._render_list()
        self._sync_status()
        supdate(self)

    def _test_action(self, e):
        self._test_specific(self._selected_action_id())

    def _test_specific(self, aid: str):
        self.manager.execute_action(aid)
        self._sync_status()
        supdate(self)

    def _remove(self, aid: str):
        self.manager.remove_hotkey(aid)
        self._render()

    def _defaults(self, e):
        self.manager.reset_defaults()
        self._render()

    def _rehook(self, e):
        self.manager.apply_hooks()
        self._render()

    def _enabled_changed(self, e):
        self.manager.set_enabled(bool(self.enabled_switch.value))
        self._render()

    def _suppress_changed(self, e):
        self.manager.set_suppress(bool(self.suppress_switch.value))
        self._render()

    def _release_changed(self, e):
        self.manager.set_trigger_on_release(bool(self.release_switch.value))
        self._render()

    def _cooldown_changed(self, e):
        self.manager.set_cooldown_ms(int(self.cooldown_slider.value or 280))
        self.cooldown_label.value = self._t("hotkeys.ms_value", value=self.manager.cooldown_ms())
        supdate(self.cooldown_label)

    def _export_dialog(self, e):
        if not mounted(self):
            return
        text = ft.TextField(
            value=self.manager.export_json(),
            multiline=True,
            min_lines=8,
            max_lines=14,
            read_only=True,
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            expand=True,
        )
        dialog_w, dialog_h = dialog_dimensions(self, 600, 500)
        dlg = ft.AlertDialog(
            bgcolor=Theme.SURFACE,
            title=ft.Text(self._t("hotkeys.export_title"), color=Theme.TEXT),
            content=ft.Container(width=dialog_w, height=dialog_h, content=text),
            actions=[ft.TextButton(self._t("common.close"), on_click=lambda e: self.page.pop_dialog())],
        )
        self.page.show_dialog(dlg)

    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        viewport = Viewport(max(280.0, float(width)), max(320.0, float(height)))
        mode_changed = viewport.mode != self._viewport.mode
        self._viewport = viewport
        if mode_changed:
            padding = 13 if viewport.compact else 16
            for card in self._cards:
                card.padding = padding
            self.spacing = 13 if viewport.compact else 16
            if update:
                supdate(self)

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
        for limit, key in [
            (15, "color.name.red"),
            (45, "color.name.orange"),
            (75, "color.name.yellow"),
            (150, "color.name.green"),
            (195, "color.name.cyan"),
            (255, "color.name.blue"),
            (300, "color.name.violet"),
            (345, "color.name.pink"),
            (361, "color.name.red"),
        ]:
            if hue <= limit:
                return self._t(key)
        return self._t("color.name.red")

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
            self._sync_validation()
        supdate(self.color_editor)
        supdate(self.validation_text)

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
