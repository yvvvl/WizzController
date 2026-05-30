from __future__ import annotations

import time

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
                    [ft.Text("Ajustes", style=Theme.H1), ft.Text("Gestión, destino e información de ampolletas", color=Theme.MUTED, size=13)],
                    spacing=2,
                ),
                ft.Container(expand=True),
                self.scan_ring,
                self.btn_add,
                self.btn_scan,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.target_box = ft.Column(spacing=10)
        self.list_view = ft.Column(spacing=12)
        self.controls = [header, self.target_box, ft.Text("AMPOLLETAS", style=Theme.LABEL), self.list_view]
        self._render_target()
        self._render_list()

    # ------------------------------------------------------------------ #
    def _render_target(self):
        self.target_box.controls.clear()
        cfg = self.wiz.get_target_config()
        mode = cfg.get("mode", "single")
        interval = cfg.get("slider_interval_ms", 65)
        active = cfg.get("active_name") or "—"
        targets = cfg.get("target_count", 0)

        self.slider_interval_label = ft.Text(f"{interval} ms", color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600)
        self.slider_interval = ft.Slider(
            min=35,
            max=160,
            value=interval,
            divisions=25,
            active_color=Theme.ACCENT,
            thumb_color="white",
            on_change=self._on_interval,
            expand=True,
        )

        single_btn = ft.ElevatedButton(
            "Una ampolleta",
            icon=ft.Icons.LIGHTBULB_ROUNDED,
            bgcolor=Theme.PRIMARY if mode == "single" else Theme.CARD_HI,
            color="white" if mode == "single" else Theme.MUTED,
            on_click=lambda e: self._set_mode("single"),
        )
        all_btn = ft.ElevatedButton(
            "Todas online",
            icon=ft.Icons.HUB_ROUNDED,
            bgcolor=Theme.PRIMARY if mode == "all" else Theme.CARD_HI,
            color="white" if mode == "all" else Theme.MUTED,
            on_click=lambda e: self._set_mode("all"),
        )

        self.target_box.controls.append(
            ft.Container(
                padding=18,
                border_radius=Theme.R_MD,
                bgcolor=Theme.CARD,
                border=ft.Border.all(1, Theme.STROKE),
                shadow=Theme.SHADOW,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Row([ft.Icon(ft.Icons.NEAR_ME_ROUNDED, color=Theme.ACCENT, size=18), ft.Text("MODO DE CONTROL", style=Theme.LABEL)], spacing=8),
                                ft.Container(expand=True),
                                ft.Text(f"Destino: {active} · {targets} target(s)", color=Theme.MUTED, size=12),
                            ],
                            wrap=True,
                            run_spacing=8,
                        ),
                        ft.Row([single_btn, all_btn], wrap=True, spacing=10, run_spacing=10),
                        ft.Divider(height=8, color=Theme.STROKE),
                        ft.Row(
                            [ft.Text("Throttle sliders/drag", style=Theme.LABEL), self.slider_interval, self.slider_interval_label],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=12,
                        ),
                    ],
                    spacing=10,
                ),
            )
        )
        supdate(self.target_box)

    def _on_interval(self, e):
        v = int(self.slider_interval.value)
        self.slider_interval_label.value = f"{v} ms"
        self.wiz.set_slider_interval_ms(v)
        supdate(self.slider_interval_label)

    def _set_mode(self, mode: str):
        self.wiz.set_target_mode(mode)
        self._render_target()
        self._render_list()

    # ------------------------------------------------------------------ #
    def _render_list(self):
        self.list_view.controls.clear()
        bulbs = self.wiz.get_bulbs_detailed()

        if not bulbs:
            self.list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        [ft.Icon(ft.Icons.LIGHTBULB_OUTLINE_ROUNDED, color=Theme.MUTED, size=36), ft.Text("No hay ampolletas. Pulsa «Buscar».", color=Theme.MUTED, size=13)],
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
        selected = bool(b.get("selected"))
        status = "● online" if online else "○ sin respuesta"
        if selected:
            status += " · destino"
        kelvin = ""
        if b.get("kelvin_min") and b.get("kelvin_max"):
            kelvin = f" · {b['kelvin_min']}-{b['kelvin_max']}K"

        return ft.Container(
            padding=16,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD_HI if selected else Theme.CARD,
            border=ft.Border.all(2 if selected else 1, Theme.PRIMARY if selected else Theme.STROKE),
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
                            ft.Text(b.get("name") or b.get("ip"), color=Theme.TEXT, weight=ft.FontWeight.W_600, size=15),
                            ft.Text(f"{b.get('ip')}   ·   {b.get('mac') or 'sin MAC'}", color=Theme.MUTED, size=11),
                            ft.Text(f"{status} · {b.get('label', '—')}{kelvin}", color=Theme.SUCCESS if online else Theme.FAINT, size=11),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.OutlinedButton("Usar", icon=ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, on_click=lambda e, ip=b["ip"]: self._select(ip)),
                    ft.IconButton(ft.Icons.INFO_OUTLINE_ROUNDED, icon_color=Theme.MUTED, icon_size=20, tooltip="Información", on_click=lambda e, x=b: self._info_dialog(x)),
                    ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Theme.PRIMARY, icon_size=20, tooltip="Renombrar", on_click=lambda e, x=b: self._rename_dialog(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, icon_size=20, tooltip="Quitar", on_click=lambda e, ip=b["ip"]: self._remove(ip)),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=14,
                wrap=True,
                run_spacing=10,
            ),
        )

    # ------------------------------------------------------------------ #
    def _scan(self, e):
        self.scan_ring.visible = True
        self.btn_scan.disabled = True
        supdate(self)
        self.wiz.rescan()

    def _select(self, ip: str):
        self.wiz.set_active_bulb(ip)
        self._render_target()
        self._render_list()

    def _remove(self, ip):
        self.wiz.remove_bulb(ip)
        self._render_target()
        self._render_list()

    def _rename_dialog(self, b):
        if not mounted(self):
            return
        field = ft.TextField(label="Nombre identificatorio", value=b.get("name") or b.get("ip"), autofocus=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        def save(e):
            self.wiz.rename_bulb(b["ip"], (field.value or "").strip() or b["ip"])
            self.page.pop_dialog()
            self._render_target()
            self._render_list()

        dlg = ft.AlertDialog(
            title=ft.Text("Renombrar ampolleta", color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=field,
            actions=[ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()), ft.ElevatedButton("Guardar", bgcolor=Theme.PRIMARY, color="white", on_click=save)],
        )
        self.page.show_dialog(dlg)

    def _add_dialog(self):
        if not mounted(self):
            return
        ip_field = ft.TextField(label="Dirección IP", hint_text="192.168.1.20", autofocus=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        name_field = ft.TextField(label="Nombre opcional", hint_text="Escritorio", color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        def save(e):
            ip = (ip_field.value or "").strip()
            if ip:
                self.wiz.add_bulb_manual(ip)
                if (name_field.value or "").strip():
                    self.wiz.rename_bulb(ip, name_field.value.strip())
                self.page.pop_dialog()
                self._render_target()
                self._render_list()

        dlg = ft.AlertDialog(
            title=ft.Text("Agregar por IP", color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=ft.Column([ip_field, name_field], tight=True, spacing=10),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()), ft.ElevatedButton("Agregar", bgcolor=Theme.PRIMARY, color="white", on_click=save)],
        )
        self.page.show_dialog(dlg)

    def _info_dialog(self, b):
        if not mounted(self):
            return

        def row(k, v):
            return ft.Row([ft.Text(k, color=Theme.MUTED, size=12, width=120), ft.Text(str(v if v not in (None, "") else "—"), color=Theme.TEXT, size=12, selectable=True)], wrap=True)

        last = b.get("last_seen")
        last_txt = "—"
        if last:
            try:
                last_txt = time.strftime("%H:%M:%S", time.localtime(float(last)))
            except Exception:
                last_txt = str(last)

        content = ft.Column(
            [
                row("Nombre", b.get("name")),
                row("IP", b.get("ip")),
                row("MAC", b.get("mac")),
                row("Estado", "online" if b.get("online") else "sin respuesta"),
                row("Modelo", b.get("module")),
                row("Firmware", b.get("fw_version")),
                row("Tipo", b.get("type_id")),
                row("Capacidad", b.get("label")),
                row("RGB", "sí" if b.get("rgb") else "no"),
                row("Blancos", "sí" if b.get("tunable_white") else "no"),
                row("Rango K", f"{b.get('kelvin_min')}-{b.get('kelvin_max')}" if b.get("kelvin_min") else "—"),
                row("Brillo", b.get("dimming")),
                row("Temp", b.get("temp")),
                row("RSSI", b.get("rssi")),
                row("Última lectura", last_txt),
            ],
            tight=True,
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
        )
        dlg = ft.AlertDialog(
            title=ft.Text("Información de ampolleta", color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=ft.Container(content=content, width=420, height=360),
            actions=[ft.TextButton("Cerrar", on_click=lambda e: self.page.pop_dialog())],
        )
        self.page.show_dialog(dlg)

    # ------------------------------------------------------------------ #
    def sync_state(self, state: dict):
        if not mounted(self):
            return
        self.scan_ring.visible = False
        self.btn_scan.disabled = False
        self._render_target()
        self._render_list()
        supdate(self)
