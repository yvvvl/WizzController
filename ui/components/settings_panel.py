from __future__ import annotations

import flet as ft
from ui.theme import Theme, mounted, supdate


class SettingsPanel(ft.Column):
    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        self.btn_scan = ft.ElevatedButton(
            "Buscar ampolletas",
            icon=ft.Icons.WIFI_FIND_ROUNDED,
            bgcolor=Theme.PRIMARY,
            color="white",
            on_click=self._scan,
        )
        self.btn_add = ft.OutlinedButton(
            "Agregar por IP",
            icon=ft.Icons.ADD_ROUNDED,
            style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
            on_click=lambda e: self._add_dialog(),
        )
        self.scan_ring = ft.ProgressRing(width=18, height=18, stroke_width=2, color=Theme.PRIMARY, visible=False)

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Ajustes", style=Theme.H1),
                        ft.Text("Target, discovery y gestión de ampolletas", color=Theme.MUTED, size=13),
                    ],
                    spacing=2,
                ),
                ft.Container(expand=True),
                self.scan_ring,
                self.btn_add,
                self.btn_scan,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.mode_dropdown = ft.Dropdown(
            label="Modo de control",
            value="single",
            options=[
                ft.DropdownOption(key="single", text="Una ampolleta"),
                ft.DropdownOption(key="all", text="Todas las detectadas"),
            ],
            border_color=Theme.STROKE,
            bgcolor=Theme.BG,
            color=Theme.TEXT,
            on_select=self._mode_changed,
            dense=True,
        )
        self.active_dropdown = ft.Dropdown(
            label="Ampolleta activa",
            options=[],
            border_color=Theme.STROKE,
            bgcolor=Theme.BG,
            color=Theme.TEXT,
            on_select=self._active_changed,
            dense=True,
        )
        self.interval_dropdown = ft.Dropdown(
            label="Rendimiento sliders",
            value="65",
            options=[
                ft.DropdownOption(key="35", text="35 ms · ultra rápido / más CPU"),
                ft.DropdownOption(key="65", text="65 ms · recomendado"),
                ft.DropdownOption(key="90", text="90 ms · suave / menos CPU"),
                ft.DropdownOption(key="130", text="130 ms · ahorro CPU"),
            ],
            border_color=Theme.STROKE,
            bgcolor=Theme.BG,
            color=Theme.TEXT,
            dense=True,
            on_select=self._interval_select,
        )
        self.btn_cleanup = ft.OutlinedButton(
            "Limpiar offline",
            icon=ft.Icons.CLEANING_SERVICES_ROUNDED,
            style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
            on_click=self._cleanup,
        )

        target_card = self._card(
            ft.Column(
                [
                    ft.Text("DESTINO", style=Theme.LABEL),
                    ft.ResponsiveRow(
                        spacing=14,
                        run_spacing=12,
                        controls=[
                            ft.Container(content=self.mode_dropdown, col={"xs": 12, "md": 3}),
                            ft.Container(content=self.active_dropdown, col={"xs": 12, "md": 4}),
                            ft.Container(content=self.interval_dropdown, col={"xs": 12, "md": 3}),
                            ft.Container(content=self.btn_cleanup, col={"xs": 12, "md": 2}, alignment=ft.Alignment.CENTER_RIGHT),
                        ],
                    ),
                    ft.Text("Sin paneles vacíos: el destino solo controla a qué IP se mandan los comandos.", color=Theme.FAINT, size=11),
                ],
                spacing=10,
            )
        )

        self.list_view = ft.Column(spacing=12)
        self.controls = [header, target_card, ft.Text("AMPOLLETAS", style=Theme.LABEL), self.list_view]
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
        if active:
            self.active_dropdown.value = active
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
                            ft.Text("No hay ampolletas. Pulsa «Buscar».", color=Theme.MUTED, size=13),
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
            badges.append(self._badge("ACTIVA", Theme.PRIMARY))
        if targeted:
            badges.append(self._badge("TARGET", Theme.ACCENT))
        if b.get("rgb"):
            badges.append(self._badge("RGB", "#ec4899"))
        if b.get("tunable_white"):
            badges.append(self._badge("K", "#f59e0b"))

        details = f"{b['ip']}   ·   {b.get('mac') or 'sin MAC'}"
        if b.get("module"):
            details += f"   ·   {b['module']}"
        kr = ""
        if b.get("kelvin_min") and b.get("kelvin_max"):
            kr = f" · {b['kelvin_min']}–{b['kelvin_max']}K"

        return ft.Container(
            padding=16,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD if not active else ft.Colors.with_opacity(0.22, Theme.PRIMARY),
            border=ft.Border.all(1, Theme.PRIMARY if active else Theme.STROKE),
            on_click=lambda e, ip=b["ip"]: self._select_ip(ip),
            ink=True,
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color=Theme.SUCCESS if online else Theme.MUTED, size=22),
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
                                    ft.Text(b["name"], color=Theme.TEXT, weight=ft.FontWeight.W_600, size=15),
                                    ft.Row(badges, spacing=6),
                                ],
                                spacing=8,
                                wrap=True,
                            ),
                            ft.Text(details, color=Theme.MUTED, size=11),
                            ft.Text(("● en línea · " + b.get("label", "") + kr) if online else "○ sin respuesta", color=Theme.SUCCESS if online else Theme.FAINT, size=11),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(ft.Icons.RADIO_BUTTON_CHECKED_ROUNDED, icon_color=Theme.PRIMARY, icon_size=20, tooltip="Usar como activa", on_click=lambda e, ip=b["ip"]: self._select_ip(ip)),
                    ft.IconButton(ft.Icons.INFO_OUTLINE_ROUNDED, icon_color=Theme.MUTED, icon_size=20, tooltip="Información", on_click=lambda e, ip=b["ip"]: self._info_dialog(ip)),
                    ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Theme.PRIMARY, icon_size=20, tooltip="Renombrar", on_click=lambda e, x=b: self._rename_dialog(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, icon_size=20, tooltip="Quitar", on_click=lambda e, ip=b["ip"]: self._remove(ip)),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=14,
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
        return ft.Row(
            [
                ft.Text(label, color=Theme.MUTED, size=12, width=125),
                ft.Text(value, color=Theme.TEXT, size=12, selectable=True, expand=True),
            ],
            spacing=8,
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

        dlg = ft.AlertDialog(
            title=ft.Text("Información de ampolleta", color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=ft.Container(
                width=520,
                content=ft.Column(rows, spacing=7, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton("Usar como activa", bgcolor=Theme.PRIMARY, color="white", on_click=lambda e: (self._select_ip(ip), self.page.pop_dialog())),
            ],
        )
        self.page.show_dialog(dlg)

    # ------------------------------------------------------------------ #
    def _scan(self, e):
        self.scan_ring.visible = True
        self.btn_scan.disabled = True
        supdate(self)
        self.wiz.rescan()

    def _cleanup(self, e):
        removed = self.wiz.cleanup_offline_bulbs()
        self._render_all()
        if mounted(self):
            dlg = ft.AlertDialog(
                title=ft.Text("Limpieza lista", color=Theme.TEXT),
                bgcolor=Theme.SURFACE,
                content=ft.Text(f"Se quitaron {removed} IP offline.", color=Theme.MUTED),
                actions=[ft.TextButton("OK", on_click=lambda e: self.page.pop_dialog())],
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

    def _remove(self, ip):
        self.wiz.remove_bulb(ip)
        self._render_all()

    def _rename_dialog(self, b):
        if not mounted(self):
            return
        field = ft.TextField(label="Nombre", value=b["name"], autofocus=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        def save(e):
            self.wiz.rename_bulb(b["ip"], (field.value or "").strip() or b["ip"])
            self.page.pop_dialog()
            self._render_all()

        dlg = ft.AlertDialog(
            title=ft.Text("Renombrar ampolleta", color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton("Guardar", bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    def _add_dialog(self):
        if not mounted(self):
            return
        field = ft.TextField(label="Dirección IP", hint_text="192.168.1.20", autofocus=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        def save(e):
            ip = (field.value or "").strip()
            if ip:
                self.wiz.add_bulb_manual(ip)
                self.page.pop_dialog()
                self._render_all()

        dlg = ft.AlertDialog(
            title=ft.Text("Agregar por IP", color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton("Agregar", bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    # ------------------------------------------------------------------ #
    def sync_state(self, state: dict):
        if not mounted(self):
            return
        self.scan_ring.visible = False
        self.btn_scan.disabled = False
        self._render_all()
        supdate(self)
