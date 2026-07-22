from __future__ import annotations

import os

import flet as ft
from localization import (
    RuntimeLanguagePreference,
    detect_system_language,
    get_manager,
    language_choices,
    normalize_language,
    translated_language_name,
)
from app_meta import APP_PRODUCT, display_version
from config.app_runtime_manager import AppRuntimeManager
from config.paths import config_dir, logs_dir
from ui.responsive import PANEL_BREAKPOINTS, Viewport, dialog_dimensions
from ui.theme import Theme, mounted, supdate


class SettingsPanel(ft.Column):
    # Discovery y gestión de dispositivos cambian metadata aunque el
    # estado luminoso permanezca igual. WizzApp usa esta marca para no
    # descartar el callback final de una búsqueda.
    refresh_on_equal_state = True
    def __init__(self, wiz, *, i18n=None, on_language_change=None, runtime=None):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.i18n = i18n or get_manager()
        self._on_language_change = on_language_change
        self.runtime = runtime or AppRuntimeManager()
        self.language_preference = RuntimeLanguagePreference(self.runtime)
        if i18n is None:
            self.i18n.set_preference(self.language_preference.load())
        self._viewport = Viewport(900, 720)
        self._build()

    # ------------------------------------------------------------------ #
    def _t(self, key: str, **values) -> str:
        return self.i18n.translate(key, **values)

    def _language_effective_text(self) -> str:
        return self._t(
            "language.effective",
            language=translated_language_name(self.i18n, self.i18n.language),
        )

    def _language_detected_text(self) -> str:
        detected = detect_system_language()
        return self._t(
            "language.detected",
            language=translated_language_name(self.i18n, detected),
        )

    def _language_changed(self, e=None) -> None:
        preference = normalize_language(self.language_dropdown.value)
        if callable(self._on_language_change):
            self._on_language_change(preference)
            return

        self.language_preference.save(preference)
        self.i18n.set_preference(preference)
        self.set_language(self.i18n.language)

    def set_language(self, language: str | None = None) -> None:
        # Rebuild is intentional: language changes are rare and rebuilding this
        # panel avoids stale labels inside dropdowns, cards, dialogs and tooltips.
        self._build()
        if mounted(self):
            supdate(self)

    def _build(self):
        self.btn_scan = ft.ElevatedButton(
            self._t("bulbs.search"),
            icon=ft.Icons.WIFI_FIND_ROUNDED,
            bgcolor=Theme.PRIMARY,
            color="white",
            on_click=self._scan,
        )
        self.btn_add = ft.OutlinedButton(
            self._t("bulbs.add_by_ip"),
            icon=ft.Icons.ADD_ROUNDED,
            style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
            on_click=lambda e: self._add_dialog(),
        )
        self.scan_ring = ft.ProgressRing(width=18, height=18, stroke_width=2, color=Theme.PRIMARY, visible=False)
        self.scan_message = ft.Text(
            "",
            color=Theme.FAINT,
            size=10,
            text_align=ft.TextAlign.RIGHT,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self._last_scan_finished_at = 0.0

        self.header_actions = ft.Row(
            [self.scan_ring, self.btn_add, self.btn_scan],
            spacing=10,
            run_spacing=8,
            wrap=True,
            alignment=ft.MainAxisAlignment.END,
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
                            ft.Text(self._t("settings.title"), style=Theme.H1),
                            ft.Text(self._t("settings.subtitle"), color=Theme.MUTED, size=13),
                        ],
                        spacing=2,
                    ),
                    col={"xs": 12, "md": 7},
                ),
                ft.Container(
                    content=ft.Column(
                        [self.header_actions, self.scan_message],
                        spacing=3,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                    col={"xs": 12, "md": 5},
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
        )

        self.mode_dropdown = ft.Dropdown(
            label=self._t("settings.target.mode"),
            value="single",
            options=[
                ft.DropdownOption(key="single", text=self._t("bulbs.mode.single")),
                ft.DropdownOption(key="all", text=self._t("bulbs.mode.all")),
            ],
            border_color=Theme.STROKE,
            bgcolor=Theme.BG,
            color=Theme.TEXT,
            on_select=self._mode_changed,
            dense=True,
        )
        self.active_dropdown = ft.Dropdown(
            label=self._t("bulbs.active"),
            options=[],
            border_color=Theme.STROKE,
            bgcolor=Theme.BG,
            color=Theme.TEXT,
            on_select=self._active_changed,
            dense=True,
        )
        self.interval_dropdown = ft.Dropdown(
            label=self._t("settings.slider_performance"),
            value="65",
            options=[
                ft.DropdownOption(key="35", text=self._t("settings.slider.35")),
                ft.DropdownOption(key="65", text=self._t("settings.slider.65")),
                ft.DropdownOption(key="90", text=self._t("settings.slider.90")),
                ft.DropdownOption(key="130", text=self._t("settings.slider.130")),
            ],
            border_color=Theme.STROKE,
            bgcolor=Theme.BG,
            color=Theme.TEXT,
            dense=True,
            on_select=self._interval_select,
        )
        self.btn_cleanup = ft.OutlinedButton(
            self._t("settings.cleanup_offline"),
            icon=ft.Icons.CLEANING_SERVICES_ROUNDED,
            style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
            on_click=self._cleanup,
        )

        target_card = self._card(
            ft.Column(
                [
                    ft.Text(self._t("settings.target.section"), style=Theme.LABEL),
                    ft.ResponsiveRow(
                        breakpoints=PANEL_BREAKPOINTS,
                        spacing=14,
                        run_spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(content=self.mode_dropdown, col={"xs": 12, "sm": 6, "lg": 3}),
                            ft.Container(content=self.active_dropdown, col={"xs": 12, "sm": 6, "lg": 3}),
                            ft.Container(content=self.interval_dropdown, col={"xs": 12, "sm": 8, "lg": 3}),
                            ft.Container(content=self.btn_cleanup, col={"xs": 12, "sm": 4, "lg": 3}, alignment=ft.Alignment.CENTER_RIGHT),
                        ],
                    ),
                    ft.Text(self._t("settings.target.help"), color=Theme.FAINT, size=11),
                ],
                spacing=10,
            )
        )

        self.language_dropdown = ft.Dropdown(
            label=self._t("language.selector"),
            value=self.i18n.preference,
            options=[
                ft.DropdownOption(key=key, text=label)
                for key, label in language_choices()
            ],
            border_color=Theme.STROKE,
            bgcolor=Theme.BG,
            color=Theme.TEXT,
            dense=True,
            on_select=self._language_changed,
        )
        self.language_effective = ft.Text(
            self._language_effective_text(),
            color=Theme.MUTED,
            size=11,
        )
        self.language_detected = ft.Text(
            self._language_detected_text(),
            color=Theme.FAINT,
            size=10,
        )
        language_card = self._card(
            ft.Column(
                [
                    ft.Text(self._t("language.section"), style=Theme.LABEL),
                    ft.Text(
                        self._t("language.description"),
                        color=Theme.MUTED,
                        size=11,
                    ),
                    self.language_dropdown,
                    self.language_effective,
                    self.language_detected,
                    ft.Text(
                        self._t("language.restart_not_required"),
                        color=Theme.FAINT,
                        size=10,
                    ),
                ],
                spacing=8,
            )
        )

        self.runtime_status = ft.Text("", color=Theme.FAINT, size=11)
        self.tray_enabled_switch = ft.Switch(
            value=bool(self.runtime.get("tray_enabled", True)),
            active_color=Theme.PRIMARY,
            on_change=self._runtime_changed,
        )
        self.minimize_to_tray_switch = ft.Switch(
            value=bool(self.runtime.get("minimize_to_tray", True)),
            active_color=Theme.PRIMARY,
            on_change=self._runtime_changed,
        )
        self.open_minimized_switch = ft.Switch(
            value=bool(self.runtime.get("open_minimized", False)),
            active_color=Theme.PRIMARY,
            on_change=self._runtime_changed,
        )
        self.startup_switch = ft.Switch(
            value=bool(self.runtime.get("startup_with_windows", False)),
            active_color=Theme.PRIMARY,
            on_change=self._runtime_changed,
        )
        self._sync_runtime_controls()

        runtime_options = ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=12,
            run_spacing=12,
            controls=[
                self._runtime_option(self._t("runtime.tray_enabled"), self._t("runtime.tray_enabled.description"), self.tray_enabled_switch),
                self._runtime_option(self._t("runtime.close_to_tray"), self._t("runtime.close_to_tray.description"), self.minimize_to_tray_switch),
                self._runtime_option(self._t("runtime.open_minimized"), self._t("runtime.open_minimized.description"), self.open_minimized_switch),
                self._runtime_option(self._t("runtime.start_with_windows"), self._t("runtime.start_with_windows.description"), self.startup_switch),
            ],
        )
        runtime_card = self._card(
            ft.Column(
                [
                    ft.Text(self._t("runtime.background"), style=Theme.LABEL),
                    runtime_options,
                    ft.Text(
                        self._t("runtime.restart_hint"),
                        color=Theme.FAINT,
                        size=11,
                    ),
                    self.runtime_status,
                ],
                spacing=10,
            )
        )

        release_card = self._card(
            ft.Column(
                [
                    ft.Text(self._t("about.title"), style=Theme.LABEL),
                    ft.ResponsiveRow(
                        breakpoints=PANEL_BREAKPOINTS,
                        spacing=12,
                        run_spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                col={"xs": 12, "md": 7},
                                content=ft.Row(
                                    [
                                        ft.Container(
                                            width=44,
                                            height=44,
                                            border_radius=14,
                                            bgcolor=ft.Colors.with_opacity(0.18, Theme.PRIMARY),
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color="white", size=23),
                                        ),
                                        ft.Column(
                                            [
                                                ft.Text(APP_PRODUCT, color=Theme.TEXT, weight=ft.FontWeight.W_700, size=14),
                                                ft.Text(display_version(), color=Theme.MUTED, size=11),
                                                ft.Text(self._t("about.local_control"), color=Theme.FAINT, size=10),
                                            ],
                                            spacing=1,
                                            expand=True,
                                        ),
                                    ],
                                    spacing=12,
                                ),
                            ),
                            ft.Container(
                                col={"xs": 12, "md": 5},
                                alignment=ft.Alignment.CENTER_RIGHT,
                                content=ft.Row(
                                    [
                                        ft.OutlinedButton(
                                            self._t("about.data"),
                                            icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                                            style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
                                            on_click=lambda e: self._open_folder(config_dir()),
                                        ),
                                        ft.OutlinedButton(
                                            self._t("about.logs"),
                                            icon=ft.Icons.DESCRIPTION_OUTLINED,
                                            style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
                                            on_click=lambda e: self._open_folder(logs_dir()),
                                        ),
                                    ],
                                    spacing=8,
                                    run_spacing=8,
                                    wrap=True,
                                    alignment=ft.MainAxisAlignment.END,
                                ),
                            ),
                        ],
                    ),
                    ft.Text(
                        self._t("about.storage_hint"),
                        color=Theme.FAINT,
                        size=11,
                    ),
                ],
                spacing=10,
            )
        )

        self.list_view = ft.Column(spacing=12)
        self.controls = [
            self.header,
            target_card,
            language_card,
            runtime_card,
            release_card,
            ft.Text(self._t("bulbs.section"), style=Theme.LABEL),
            self.list_view,
        ]
        self._render_all()

    # ------------------------------------------------------------------ #
    def _card(self, content):
        return ft.Container(
            content=content,
            padding=18,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )

    def _runtime_option(self, title: str, subtitle: str, switch: ft.Switch) -> ft.Container:
        return ft.Container(
            col={"xs": 12, "sm": 6, "lg": 3},
            padding=12,
            border_radius=Theme.R_SM,
            bgcolor=Theme.CARD_HI,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(title, color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600),
                            ft.Text(subtitle, color=Theme.FAINT, size=10, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    switch,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _open_folder(self, path) -> None:
        try:
            folder = os.fspath(path)
            if os.name == "nt":
                os.startfile(folder)  # type: ignore[attr-defined]
            else:
                self.runtime_status.value = folder
                supdate(self.runtime_status)
        except Exception as exc:
            self.runtime_status.value = f"No se pudo abrir la carpeta: {exc}"
            self.runtime_status.color = Theme.WARNING
            supdate(self.runtime_status)

    def _render_all(self):
        self._render_target_controls()
        self._render_list()

    def _render_target_controls(self):
        cfg = self.wiz.get_target_config()
        bulbs = self.wiz.get_bulbs_detailed()
        self.mode_dropdown.value = cfg.get("mode", "single")
        self.active_dropdown.options = [
            ft.DropdownOption(
                key=b["ip"],
                text=f"{'●' if b.get('online') else '○'} {b.get('name') or b['ip']} · {b['ip']}",
            )
            for b in bulbs
        ]
        active = cfg.get("active_ip")
        self.active_dropdown.value = active if active else None
        ms = str(int(cfg.get("slider_interval_ms", 65)))
        allowed = {"35", "65", "90", "130"}
        self.interval_dropdown.value = ms if ms in allowed else "65"
        supdate(self.mode_dropdown)
        supdate(self.active_dropdown)
        supdate(self.interval_dropdown)

    def _render_list(self):
        self.list_view.controls.clear()
        bulbs = self.wiz.get_bulbs_detailed()

        if not bulbs:
            self.list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.LIGHTBULB_OUTLINE_ROUNDED, color=Theme.MUTED, size=36),
                            ft.Text(self._t("bulbs.none"), color=Theme.MUTED, size=13),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=40,
                )
            )
        else:
            for b in bulbs:
                self.list_view.controls.append(self._bulb_card(b))

        supdate(self.list_view)

    def _bulb_card(self, b):
        online = bool(b.get("online"))
        active = bool(b.get("active"))
        targeted = bool(b.get("targeted"))
        badges = []
        if active:
            badges.append(self._badge(self._t("bulbs.active_badge"), Theme.PRIMARY))
        if targeted:
            badges.append(self._badge("TARGET", Theme.ACCENT))
        if b.get("rgb"):
            badges.append(self._badge("RGB", "#ec4899"))
        if b.get("tunable_white"):
            badges.append(self._badge("K", "#f59e0b"))

        details = f"{b['ip']} · {b.get('mac') or 'sin MAC'}"
        if b.get("module"):
            details += f" · {b['module']}"
        kr = ""
        if b.get("kelvin_min") and b.get("kelvin_max"):
            kr = f" · {b['kelvin_min']}–{b['kelvin_max']}K"

        identity = ft.Row(
            [
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.LIGHTBULB_ROUNDED,
                        color=Theme.SUCCESS if online else Theme.MUTED,
                        size=22,
                    ),
                    width=44,
                    height=44,
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.14, Theme.SUCCESS if online else Theme.MUTED),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    b.get("name") or b["ip"],
                                    color=Theme.TEXT,
                                    weight=ft.FontWeight.W_600,
                                    size=15,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Row(badges, spacing=6, wrap=True),
                            ],
                            spacing=8,
                            run_spacing=5,
                            wrap=True,
                        ),
                        ft.Text(details, color=Theme.MUTED, size=11, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(
                            ("● en línea · " + b.get("label", "") + kr) if online else "○ sin respuesta",
                            color=Theme.SUCCESS if online else Theme.FAINT,
                            size=11,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        actions = ft.Row(
            [
                ft.IconButton(
                    ft.Icons.RADIO_BUTTON_CHECKED_ROUNDED,
                    icon_color=Theme.PRIMARY,
                    icon_size=20,
                    tooltip=self._t("bulbs.use_as_active"),
                    on_click=lambda e, ip=b["ip"]: self._select_ip(ip),
                ),
                ft.IconButton(
                    ft.Icons.INFO_OUTLINE_ROUNDED,
                    icon_color=Theme.MUTED,
                    icon_size=20,
                    tooltip=self._t("common.information"),
                    on_click=lambda e, ip=b["ip"]: self._info_dialog(ip),
                ),
                ft.IconButton(
                    ft.Icons.EDIT_ROUNDED,
                    icon_color=Theme.PRIMARY,
                    icon_size=20,
                    tooltip=self._t("common.rename"),
                    on_click=lambda e, x=b: self._rename_dialog(x),
                ),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE_ROUNDED,
                    icon_color=Theme.ERROR,
                    icon_size=20,
                    tooltip=self._t("common.remove"),
                    on_click=lambda e, ip=b["ip"]: self._remove(ip),
                ),
            ],
            spacing=2,
            wrap=True,
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            padding=16,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD if not active else ft.Colors.with_opacity(0.22, Theme.PRIMARY),
            border=ft.Border.all(1, Theme.PRIMARY if active else Theme.STROKE),
            content=ft.ResponsiveRow(
                breakpoints=PANEL_BREAKPOINTS,
                spacing=12,
                run_spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        content=identity,
                        col={"xs": 12, "md": 8, "lg": 9},
                        border_radius=Theme.R_SM,
                        ink=True,
                        on_click=lambda e, ip=b["ip"]: self._select_ip(ip),
                    ),
                    ft.Container(content=actions, col={"xs": 12, "md": 4, "lg": 3}, alignment=ft.Alignment.CENTER_RIGHT),
                ],
            ),
        )

    def _badge(self, text, color):
        return ft.Container(
            content=ft.Text(text, size=9, color="white", weight=ft.FontWeight.BOLD),
            bgcolor=color,
            padding=ft.Padding.symmetric(horizontal=7, vertical=3),
            border_radius=12,
        )

    def _info_line(self, label, value):
        value = "—" if value is None or value == "" else str(value)
        return ft.ResponsiveRow(
            breakpoints=PANEL_BREAKPOINTS,
            spacing=8,
            run_spacing=2,
            controls=[
                ft.Container(
                    content=ft.Text(label, color=Theme.MUTED, size=12),
                    col={"xs": 12, "sm": 4},
                ),
                ft.Container(
                    content=ft.Text(value, color=Theme.TEXT, size=12, selectable=True),
                    col={"xs": 12, "sm": 8},
                ),
            ],
        )

    def _info_dialog(self, ip: str):
        if not mounted(self):
            return
        try:
            info = self.wiz.get_device_info(ip)
        except Exception:
            info = {}
        if not info:
            info = next((b for b in self.wiz.get_bulbs_detailed() if b.get("ip") == ip), {"ip": ip})

        caps = info.get("capabilities") or {}
        raw = info.get("raw_state") or {}
        system = info.get("system") or {}
        model = info.get("model_config") or {}

        rows = [
            self._info_line("Nombre", info.get("name")),
            self._info_line("IP", info.get("ip") or ip),
            self._info_line("MAC", info.get("mac")),
            self._info_line("Online", "sí" if info.get("online") else "no"),
            self._info_line("Activa", "sí" if info.get("active") else "no"),
            self._info_line("Target", "sí" if info.get("targeted") else "no"),
            self._info_line("Módulo", info.get("module") or system.get("moduleName")),
            self._info_line("Firmware", system.get("fwVersion")),
            self._info_line("RSSI", info.get("rssi") or raw.get("rssi")),
            self._info_line("Estado", raw.get("state") if raw else info.get("state")),
            self._info_line("Brillo", raw.get("dimming") if raw else info.get("dimming")),
            self._info_line("Temp", raw.get("temp") if raw else info.get("temp")),
            self._info_line("Escena", raw.get("sceneId") if raw else info.get("sceneId")),
            self._info_line("RGB", caps.get("rgb") if caps else info.get("rgb")),
            self._info_line("Blancos", caps.get("tunable_white") if caps else info.get("tunable_white")),
            self._info_line("Kelvin", f"{info.get('kelvin_min') or caps.get('kelvin_min') or '—'}–{info.get('kelvin_max') or caps.get('kelvin_max') or '—'}K"),
            self._info_line("Ratio", caps.get("ratio")),
            self._info_line("Medidor W", caps.get("power_meter")),
        ]

        if model:
            visible_model = {k: model.get(k) for k in ("cctRange", "extRange", "whiteRange", "nowc", "wcr", "fanSpeed") if k in model}
            if visible_model:
                rows.append(self._info_line("Modelo", visible_model))

        dialog_w, dialog_h = dialog_dimensions(self, 560, 590)
        dlg = ft.AlertDialog(
            title=ft.Text(self._t("bulbs.info"), color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=ft.Container(
                width=dialog_w,
                height=dialog_h,
                content=ft.Column(rows, spacing=7, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton(self._t("common.close"), on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton(self._t("bulbs.use_as_active"), bgcolor=Theme.PRIMARY, color="white", on_click=lambda e: (self._select_ip(ip), self.page.pop_dialog())),
            ],
        )
        self.page.show_dialog(dlg)

    # ------------------------------------------------------------------ #
    def _scan(self, e):
        started = bool(self.wiz.rescan())
        self._sync_scan_status()
        if not started:
            status = self.wiz.get_scan_status()
            if not bool(status.get("running")):
                self.scan_message.value = str(
                    status.get("error")
                    or self._t("bulbs.search_not_started")
                )
                self.scan_message.color = Theme.ERROR
        supdate(self.scan_ring)
        supdate(self.btn_scan)
        supdate(self.scan_message)

    def _sync_scan_status(self, state: dict | None = None) -> None:
        status = None
        if isinstance(state, dict):
            candidate = state.get("_scan")
            if isinstance(candidate, dict):
                status = candidate
        if status is None:
            try:
                status = self.wiz.get_scan_status()
            except Exception:
                status = {}

        running = bool(status.get("running"))
        error = str(status.get("error") or "").strip()
        try:
            finished_at = float(status.get("finished_at") or 0.0)
        except Exception:
            finished_at = 0.0

        self.scan_ring.visible = running
        self.btn_scan.disabled = running

        if running:
            self.scan_message.value = self._t("bulbs.searching")
            self.scan_message.color = Theme.PRIMARY
        elif error:
            self.scan_message.value = self._t("bulbs.search_error", error=error[:120])
            self.scan_message.color = Theme.ERROR
            self._last_scan_finished_at = max(self._last_scan_finished_at, finished_at)
        elif finished_at > self._last_scan_finished_at:
            found = int(status.get("found") or 0)
            self.scan_message.value = self.i18n.translate_count("bulbs.search_done", found)
            self.scan_message.color = Theme.SUCCESS
            self._last_scan_finished_at = finished_at

    def _cleanup(self, e):
        removed = self.wiz.cleanup_offline_bulbs()
        self._render_all()
        if mounted(self):
            dlg = ft.AlertDialog(
                title=ft.Text(self._t("settings.cleanup_title"), color=Theme.TEXT),
                bgcolor=Theme.SURFACE,
                content=ft.Text(self._t("settings.cleanup_result", count=removed), color=Theme.MUTED),
                actions=[ft.TextButton(self._t("common.ok"), on_click=lambda e: self.page.pop_dialog())],
            )
            self.page.show_dialog(dlg)

    def _mode_changed(self, e):
        self.wiz.set_target_mode(self.mode_dropdown.value or "single")
        self._render_all()

    def _active_changed(self, e):
        if self.active_dropdown.value:
            self.wiz.set_active_bulb(self.active_dropdown.value)
            self._render_all()

    def _select_ip(self, ip):
        self.wiz.set_active_bulb(ip)
        self._render_all()

    def _interval_select(self, e):
        try:
            self.wiz.set_slider_interval_ms(int(self.interval_dropdown.value or "65"))
        except Exception:
            pass
        self._render_all()

    def _sync_runtime_controls(self):
        tray_enabled = bool(self.tray_enabled_switch.value)
        if not tray_enabled:
            self.minimize_to_tray_switch.value = False
            self.open_minimized_switch.value = False
        self.minimize_to_tray_switch.disabled = not tray_enabled
        self.open_minimized_switch.disabled = not tray_enabled

    def _runtime_changed(self, e=None):
        tray_enabled = bool(self.tray_enabled_switch.value)
        minimize_to_tray = bool(self.minimize_to_tray_switch.value) if tray_enabled else False
        open_minimized = bool(self.open_minimized_switch.value) if tray_enabled else False
        startup = bool(self.startup_switch.value)

        self.runtime.update(
            tray_enabled=tray_enabled,
            minimize_to_tray=minimize_to_tray,
            open_minimized=open_minimized,
        )

        message = self._t("runtime.saved")
        if getattr(e, "control", None) is self.startup_switch:
            ok, startup_msg = self.runtime.set_startup_with_windows(startup)
            if startup or ok:
                message = startup_msg
            else:
                message = "Inicio con Windows desactivado."

        self.runtime_status.value = message
        self._sync_runtime_controls()
        supdate(self.runtime_status)
        supdate(self.minimize_to_tray_switch)
        supdate(self.open_minimized_switch)

    def _remove(self, ip):
        removed = bool(self.wiz.remove_bulb(ip))
        self._render_all()
        self.scan_message.value = (
            self._t("bulbs.removed")
            if removed
            else self._t("bulbs.already_removed")
        )
        self.scan_message.color = Theme.SUCCESS if removed else Theme.FAINT
        supdate(self.scan_message)

    def _rename_dialog(self, b):
        if not mounted(self):
            return
        field = ft.TextField(label=self._t("common.name"), value=b["name"], autofocus=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        def save(e):
            self.wiz.rename_bulb(b["ip"], (field.value or "").strip() or b["ip"])
            self.page.pop_dialog()
            self._render_all()

        dlg = ft.AlertDialog(
            title=ft.Text(self._t("bulbs.rename_title"), color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=field,
            actions=[
                ft.TextButton(self._t("common.cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton(self._t("common.save"), bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    def _add_dialog(self):
        if not mounted(self):
            return
        field = ft.TextField(label=self._t("bulbs.ip_address"), hint_text="192.168.1.20", autofocus=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        def save(e):
            ip = (field.value or "").strip()
            if ip:
                self.wiz.add_bulb_manual(ip)
                self.page.pop_dialog()
                self._render_all()

        dlg = ft.AlertDialog(
            title=ft.Text(self._t("bulbs.add_by_ip"), color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=field,
            actions=[
                ft.TextButton(self._t("common.cancel"), on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton(self._t("common.add"), bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    def set_viewport(self, width: float, height: float, *, update: bool = True) -> None:
        viewport = Viewport(max(280.0, float(width)), max(320.0, float(height)))
        mode_changed = viewport.mode != self._viewport.mode
        self._viewport = viewport
        if mode_changed:
            card_padding = 14 if viewport.compact else 18
            # Las tres cards superiores son controles directos del panel.
            for control in self.controls[:4]:
                if isinstance(control, ft.Container):
                    control.padding = card_padding
            if update:
                supdate(self)

    # ------------------------------------------------------------------ #
    def sync_state(self, state: dict):
        if not mounted(self):
            return
        self._sync_scan_status(state)
        self._render_all()
        supdate(self.scan_ring)
        supdate(self.btn_scan)
        supdate(self.scan_message)
        supdate(self)
