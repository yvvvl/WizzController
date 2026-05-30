from __future__ import annotations

import threading
import time

import flet as ft

from config.favorites_manager import FavoritesManager
from core import wiz_scenes
from ui.theme import Theme, mounted, supdate


class HotkeysPanel(ft.Column):
    def __init__(self, wiz, manager):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.manager = manager
        self.fav_manager = FavoritesManager()
        self.recording_id: str | None = None
        self._build()

    def _build(self):
        self.enabled_switch = ft.Switch(
            label="Atajos globales",
            value=self.manager.is_enabled(),
            active_color=Theme.PRIMARY,
            on_change=self._toggle_enabled,
        )
        self.suppress_switch = ft.Switch(
            label="Capturar tecla",
            value=bool(self.manager.data.get("suppress", False)),
            active_color=Theme.PRIMARY,
            on_change=self._toggle_suppress,
        )
        self.status_text = ft.Text(self._status_text(), color=Theme.MUTED, size=12)

        header = ft.Row(
            [
                ft.Column([ft.Text("Hotkeys", style=Theme.H1), ft.Text("Atajos globales para controlar WiZ sin abrir la ventana", color=Theme.MUTED, size=13)], spacing=2),
                ft.Container(expand=True),
                self.enabled_switch,
                self.suppress_switch,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
            run_spacing=8,
        )
        self.body = ft.Column(spacing=18)
        self.controls = [header, self.status_text, self.body]
        self._render()

    def _status_text(self) -> str:
        if not self.manager.available:
            return f"keyboard no disponible: {self.manager.last_error or 'instala/permite la librería keyboard'}"
        if self.manager.last_error:
            return f"Aviso: {self.manager.last_error}"
        if not self.manager.is_enabled():
            return "Desactivado. Actívalo cuando ya tengas combinaciones configuradas."
        return "Activo. En Linux puede requerir permisos; en Windows debería funcionar normal."

    def _render(self):
        self.fav_manager = FavoritesManager()
        self.body.controls.clear()
        self.body.controls.append(self._section("GENERAL", self._general_actions()))
        self.body.controls.append(self._section("COLORES / BLANCOS", self._color_actions()))
        self.body.controls.append(self._section("ESCENAS", self._scene_actions()))
        self.body.controls.append(self._section("FAVORITOS", self._favorite_actions()))
        self.status_text.value = self._status_text()
        supdate(self.body)
        supdate(self.status_text)

    def _general_actions(self):
        return [
            ("Encender", "on", ft.Icons.POWER_SETTINGS_NEW_ROUNDED),
            ("Apagar", "off", ft.Icons.POWER_OFF_ROUNDED),
            ("Alternar", "toggle", ft.Icons.TOGGLE_ON_ROUNDED),
            ("Reset luz", "reset", ft.Icons.RESTART_ALT_ROUNDED),
            ("Brillo +10", "bri_up", ft.Icons.ADD_ROUNDED),
            ("Brillo -10", "bri_down", ft.Icons.REMOVE_ROUNDED),
        ]

    def _color_actions(self):
        return [
            ("Rojo", "color_red", ft.Icons.PALETTE_ROUNDED),
            ("Verde", "color_green", ft.Icons.PALETTE_ROUNDED),
            ("Azul", "color_blue", ft.Icons.PALETTE_ROUNDED),
            ("Cian", "color_cyan", ft.Icons.PALETTE_ROUNDED),
            ("Magenta", "color_magenta", ft.Icons.PALETTE_ROUNDED),
            ("Naranja", "color_orange", ft.Icons.PALETTE_ROUNDED),
            ("Blanco cálido", "white_warm", ft.Icons.LIGHT_MODE_ROUNDED),
            ("Blanco neutro", "white_neutral", ft.Icons.LIGHT_MODE_ROUNDED),
            ("Blanco frío", "white_cold", ft.Icons.LIGHT_MODE_ROUNDED),
        ]

    def _scene_actions(self):
        return [(f"{sc.glyph} {sc.name}", f"scene_{sid}", ft.Icons.AUTO_AWESOME_ROUNDED) for sid, sc in wiz_scenes.CATALOG.items()]

    def _favorite_actions(self):
        favs = self.fav_manager.get_favorites()
        if not favs:
            return [("Sin favoritos", "", ft.Icons.STAR_BORDER_ROUNDED)]
        return [(fav.get("name") or "Favorito", f"fav_{fav.get('id')}", ft.Icons.STAR_ROUNDED) for fav in favs]

    def _section(self, title: str, actions: list[tuple[str, str, object]]):
        rows = [self._row(label, aid, icon) for label, aid, icon in actions]
        return ft.Container(
            padding=18,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
            content=ft.Column([ft.Text(title, style=Theme.LABEL), *rows], spacing=8),
        )

    def _row(self, label: str, aid: str, icon):
        if not aid:
            return ft.Container(
                padding=10,
                content=ft.Text("Crea favoritos en el panel Favoritos para asignarles hotkeys.", color=Theme.MUTED, size=12),
            )
        key = self.manager.get_hotkey(aid)
        rec = aid == self.recording_id
        txt = "Grabando…" if rec else (key.upper() if key else "Asignar")
        btn_color = Theme.ERROR if rec else Theme.PRIMARY if key else Theme.MUTED
        return ft.Container(
            padding=10,
            border_radius=Theme.R_SM,
            bgcolor=Theme.BG,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [
                    ft.Row([ft.Icon(icon, color=Theme.ACCENT, size=18), ft.Text(label, color=Theme.TEXT, size=13)], spacing=10, expand=True),
                    ft.Text(key or "—", color=Theme.MUTED, size=12, selectable=True),
                    ft.OutlinedButton(txt, icon=ft.Icons.KEYBOARD_ROUNDED, style=ft.ButtonStyle(color=btn_color, side=ft.BorderSide(1, btn_color)), on_click=lambda e, x=aid: self._start_recording(x), disabled=not self.manager.available),
                    ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_color=Theme.SUCCESS, tooltip="Probar", on_click=lambda e, x=aid: self.manager.execute_action(x)),
                    ft.IconButton(ft.Icons.CLEAR_ROUNDED, icon_color=Theme.ERROR, tooltip="Limpiar", on_click=lambda e, x=aid: self._clear(x)),
                ],
                spacing=10,
                wrap=True,
                run_spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    # ------------------------------------------------------------------ #
    def _toggle_enabled(self, e):
        self.manager.set_enabled(bool(self.enabled_switch.value))
        self._render()

    def _toggle_suppress(self, e):
        self.manager.set_suppress(bool(self.suppress_switch.value))
        self._render()

    def _clear(self, aid: str):
        self.manager.clear_hotkey(aid)
        self._render()

    def _start_recording(self, aid: str):
        if not self.manager.available:
            return
        self.recording_id = aid
        self._render()
        threading.Thread(target=self._record_thread, args=(aid,), daemon=True).start()

    def _record_thread(self, aid: str):
        try:
            time.sleep(0.2)
            combo = self.manager.read_hotkey_blocking()
            if combo and combo.lower() != "esc":
                self.manager.set_hotkey(aid, combo)
        finally:
            try:
                if mounted(self):
                    self.page.run_task(self._finish_recording)
                else:
                    self.recording_id = None
            except Exception:
                self.recording_id = None

    async def _finish_recording(self, *args):
        self.recording_id = None
        self._render()
        supdate(self)

    def sync_state(self, state: dict):
        pass
