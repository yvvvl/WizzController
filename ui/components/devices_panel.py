from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict

import flet as ft

from ui import flet_overlays as overlays
from ui.styles import Theme


class DevicesPanel(ft.Container):
    def __init__(self, wiz_manager: Any):
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.wiz = wiz_manager

        self.expand = True
        self.padding = 20

        self._auto_refresh_enabled: bool = True
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None

        self.device_grid = ft.GridView(
            expand=True,
            runs_count=5,
            max_extent=360,
            child_aspect_ratio=1.7,
            spacing=16,
            run_spacing=16,
        )

        self.content = ft.Column(
            controls=[
                self._build_header(),
                ft.Divider(height=12, color="transparent"),
                self.device_grid,
            ],
            expand=True,
        )

    def did_mount(self):
        self._stop_event.clear()
        self.refresh()
        self._start_worker_if_needed()

    def did_unmount(self):
        self._stop_event.set()

    def set_auto_refresh(self, enabled: bool) -> None:
        self._auto_refresh_enabled = bool(enabled)
        if self._auto_refresh_enabled:
            self._start_worker_if_needed()

    def _build_header(self) -> ft.Control:
        button_style = getattr(Theme, "BUTTON_STYLE_ICON", None)
        return ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.LIGHTBULB_OUTLINE, color=Theme.PRIMARY, size=26),
                        ft.Text("Dispositivos", style=Theme.H2),
                    ],
                    spacing=10,
                ),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.icons.SEARCH,
                    icon_color=Theme.TEXT_MAIN,
                    style=button_style,
                    tooltip="Buscar bombillas",
                    on_click=self._on_discover,
                ),
                ft.IconButton(
                    icon=ft.icons.REFRESH,
                    icon_color=Theme.TEXT_MAIN,
                    style=button_style,
                    tooltip="Refrescar",
                    on_click=lambda _e: self.refresh(),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def _start_worker_if_needed(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._monitor_loop, daemon=True)
        self._worker.start()

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(2.0)
            if not self._auto_refresh_enabled:
                continue
            try:
                if self.page:
                    self.page.run_task(self._safe_refresh)
                else:
                    self.refresh()
            except Exception:
                pass

    async def _safe_refresh(self, *_args):
        self.refresh()

    def refresh(self) -> None:
        bulbs = getattr(self.wiz, "bulbs", []) or []

        states: Dict[str, Dict[str, Any]] = {}
        try:
            if hasattr(self.wiz, "get_bulb_states_snapshot"):
                maybe_states = self.wiz.get_bulb_states_snapshot()
                if isinstance(maybe_states, dict):
                    states = maybe_states
        except Exception:
            states = {}

        manager = getattr(self.wiz, "bulbs_manager", None)
        self.device_grid.controls = [self._build_device_card(b, states, manager) for b in bulbs]

        try:
            self.update()
        except Exception:
            pass

    def _build_device_card(self, bulb: Any, states: Dict[str, Dict[str, Any]], manager: Any) -> ft.Control:
        ip = getattr(bulb, "ip", None) or "?"
        mac = getattr(bulb, "mac", "") or ""

        meta: Dict[str, Any] = {}
        try:
            if manager and hasattr(manager, "get_bulbs"):
                meta = (manager.get_bulbs() or {}).get(ip, {}) or {}
        except Exception:
            meta = {}

        display_name = meta.get("name") or meta.get("mac") or mac or "Wiz Light"
        st = states.get(ip, {}) if isinstance(states, dict) else {}

        reachable = bool(st.get("reachable", True))
        is_on = bool(st.get("state")) if st.get("state") is not None else False
        bri = int(st.get("brightness") or 50)

        icon_color = Theme.WARNING if is_on else Theme.TEXT_MUTED
        if not reachable:
            icon_color = Theme.ERROR

        header = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.icons.LIGHTBULB, color=icon_color),
                    bgcolor=ft.Colors.with_opacity(0.10, icon_color),
                    padding=10,
                    border_radius=10,
                ),
                ft.Column(
                    controls=[
                        ft.Text(display_name, weight="bold", size=16, color=Theme.TEXT_MAIN, max_lines=1),
                        ft.Text(f"IP: {ip}", size=11, color=Theme.TEXT_MUTED, font_family="monospace"),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Switch(
                    value=is_on,
                    disabled=not reachable,
                    active_color=Theme.SUCCESS,
                    on_change=lambda e, target_ip=ip: self._toggle_bulb(target_ip, bool(e.control.value)),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        slider = ft.Slider(
            min=10,
            max=100,
            value=bri,
            expand=True,
            disabled=not reachable,
            active_color=Theme.ACCENT,
            height=20,
            on_change_end=lambda e, target_ip=ip: self._set_brightness(target_ip, e.control.value),
        )

        return ft.Container(
            bgcolor=Theme.CARD_BG,
            border=getattr(Theme, "CARD_BORDER", None),
            border_radius=getattr(Theme, "CARD_RADIUS", 14),
            shadow=getattr(Theme, "SHADOW_CARD", None),
            padding=18,
            content=ft.Column(
                controls=[
                    header,
                    ft.Divider(color=ft.Colors.with_opacity(0.05, "white"), height=18),
                    ft.Row(
                        controls=[
                            ft.Text("Brillo", size=11, color=getattr(Theme, "TEXT_SUBTLE", Theme.TEXT_MUTED)),
                            slider,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=0,
            ),
        )

    def _toggle_bulb(self, ip: str, state: bool) -> None:
        try:
            if state:
                self.wiz.turn_on(ip=ip)
            else:
                self.wiz.turn_off(ip=ip)
        except Exception:
            self.logger.exception("No se pudo alternar el dispositivo")
            if self.page:
                overlays.show_snackbar(self.page, "No se pudo alternar el dispositivo", bgcolor=Theme.ERROR)

    def _set_brightness(self, ip: str, value: float) -> None:
        try:
            if hasattr(self.wiz, "set_brightness"):
                self.wiz.set_brightness(int(value), ip=ip, emit=False)
        except Exception:
            self.logger.exception("No se pudo ajustar brillo")
            if self.page:
                overlays.show_snackbar(self.page, "No se pudo ajustar brillo", bgcolor=Theme.ERROR)

    def _on_discover(self, _e=None) -> None:
        if self.page:
            overlays.show_snackbar(self.page, "Buscando bombillas...", bgcolor=Theme.PRIMARY)
        try:
            if hasattr(self.wiz, "discover"):
                self.wiz.discover()
        except Exception:
            self.logger.exception("No se pudo iniciar discovery")
