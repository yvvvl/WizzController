import flet as ft
import threading
import logging
import time
from ui.styles import Theme
from .favorites_panel import FavoritesPanel
from ui import flet_overlays as overlays
from config.config_manager import ConfigManager

class HomePanel(ft.Container):
    def __init__(self, wiz_manager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.wiz = wiz_manager
        self.expand = True

        self.cfg = ConfigManager()

        self._pending_bri: int | None = None
        self._last_sent_bri: int | None = None
        self._drag_active_until: float = 0.0
        self._last_ui_bri_update_ts: float = 0.0
        self._last_send_ts: float = 0.0
        self._send_interval_s: float = 0.22
        
        self._build_ui()

    def did_unmount(self):
        pass

    def _build_ui(self):
        header = ft.Row([
            ft.Icon(ft.icons.HOME_FILLED, color=Theme.PRIMARY, size=28),
            ft.Text("Panel de Control", style=Theme.H1),
        ])

        # Perfil de rendimiento (cambia cÃ³mo de agresivo es el modo idle)
        try:
            perf = self.cfg.get_performance()
            profile = str(perf.get("profile", "balanced"))
        except Exception:
            profile = "balanced"

        self.dd_perf = ft.Dropdown(
            label="Perfil de rendimiento",
            value=profile,
            options=[
                ft.dropdown.Option("balanced", "Balanced (recomendado)"),
                ft.dropdown.Option("ultra_light", "Ultra light (mÃ­nimo consumo)"),
            ],
            width=320,
            bgcolor=Theme.BG_DARK,
            color=Theme.TEXT_MAIN,
        )

        def _on_perf_change(e):
            try:
                new_profile = str(e.control.value or "balanced")
                self.cfg.set_performance_profile(new_profile)
                perf_cfg = self.cfg.get_performance()
                if hasattr(self.wiz, "apply_performance_config"):
                    self.wiz.apply_performance_config(perf_cfg)
                if self.page:
                    overlays.show_snackbar(
                        self.page,
                        f"Perfil aplicado: {new_profile}",
                        bgcolor=Theme.SUCCESS,
                    )
            except Exception:
                self.logger.exception("No se pudo aplicar perfil de rendimiento")
                if self.page:
                    overlays.show_snackbar(self.page, "No se pudo aplicar perfil", bgcolor=Theme.ERROR)

        self.dd_perf.on_change = _on_perf_change

        self.lbl_bri = ft.Text("100%", size=16, weight="bold", color=Theme.TEXT_MAIN)
        self.lbl_temp = ft.Text("4200K", size=14, color=Theme.TEXT_MUTED)
        
        self.slider_bri = ft.Slider(
            min=10, max=100, value=100,
            active_color=Theme.PRIMARY,
            thumb_color=Theme.TEXT_MAIN,
            expand=True,
            on_change_end=self._on_slider_commit,
        )
        
        self.slider_temp = ft.Slider(
            min=2200, max=6500, value=4200,
            active_color=Theme.WARNING,
            thumb_color=Theme.TEXT_MAIN,
            expand=True,
            on_change_end=self._on_temp_commit,
        )

        btn_on = self._make_power_btn("ON", ft.icons.POWER_SETTINGS_NEW, Theme.SUCCESS, self.wiz.turn_on)
        btn_off = self._make_power_btn("OFF", ft.icons.POWER_OFF, Theme.ERROR, self.wiz.turn_off)

        self.content = ft.ListView(
            controls=[
                header,
                ft.Container(height=10),
                ft.Container(
                    padding=18,
                    bgcolor=Theme.CARD_BG,
                    border_radius=16,
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.SPEED, color=Theme.ACCENT, size=22),
                                    ft.Text("Rendimiento", style=Theme.LABEL, color=Theme.TEXT_MAIN),
                                ],
                                spacing=10,
                            ),
                            ft.Text(
                                "Balanced mantiene respuesta rÃ¡pida; Ultra light minimiza consumo en reposo.",
                                size=12,
                                color=Theme.TEXT_MUTED,
                            ),
                            self.dd_perf,
                        ],
                        spacing=10,
                    ),
                ),
                ft.Container(height=20),
                ft.Container(
                    padding=25, bgcolor=Theme.CARD_BG, border_radius=16,
                    content=ft.Column([
                        ft.Row([ft.Text("INTENSIDAD", style=Theme.LABEL), self.lbl_bri], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        self.slider_bri,
                        ft.Container(height=15),
                        ft.Row([btn_on, ft.Container(width=10), btn_off])
                    ])
                ),
                ft.Container(height=18),
                ft.Container(
                    padding=25, bgcolor=Theme.CARD_BG, border_radius=16,
                    content=ft.Column([
                        ft.Row([ft.Text("TEMPERATURA (Blanco)", style=Theme.LABEL), self.lbl_temp], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        self.slider_temp,
                    ])
                ),
                ft.Container(height=20),
                FavoritesPanel(self.wiz)
            ],
            padding=ft.padding.only(bottom=50)
        )

    def _make_power_btn(self, text, icon, color, func):
        return ft.Container(
            expand=True, height=60,
            bgcolor=ft.Colors.with_opacity(0.1, color),
            border=ft.border.all(1, ft.Colors.with_opacity(0.5, color)),
            border_radius=12,
            content=ft.Row([ft.Icon(icon, color=color), ft.Text(text, weight="bold", color=Theme.TEXT_MAIN)], alignment=ft.MainAxisAlignment.CENTER),
            on_click=lambda _: threading.Thread(target=func).start(),
            ink=True
        )

    def _on_slider_commit(self, e):
        val = int(e.control.value)
        self._pending_bri = val
        self._drag_active_until = time.time() + 0.25
        self.lbl_bri.value = f"{val}%"
        try:
            self.lbl_bri.update()
        except Exception:
            pass

        # Pausa polling y envia una sola vez.
        try:
            if hasattr(self.wiz, "set_user_interacting"):
                self.wiz.set_user_interacting(0.9)
        except Exception:
            pass
        self._send_brightness_now(val)

    def _send_brightness_now(self, val: int) -> None:
        try:
            if self._last_sent_bri != int(val):
                self._last_sent_bri = int(val)
                self.wiz.set_brightness(int(val), emit=False)
        except Exception:
            self.logger.exception("Error enviando brillo")

    def _on_temp_commit(self, e):
        val = int(e.control.value)
        self.lbl_temp.value = f"{val}K"
        try:
            self.lbl_temp.update()
        except Exception:
            pass
        try:
            self.wiz.set_white(int(val), emit=False)
        except Exception:
            self.logger.exception("Error enviando temperatura")

    def sync_state(self, state):
        if time.time() < self._drag_active_until:
            return
        if "brightness" in state:
            b = int(state["brightness"])
            self.slider_bri.value = b
            self.lbl_bri.value = f"{b}%"
            self.slider_bri.update()
            self.lbl_bri.update()
        if "temp" in state:
            t = int(state["temp"])
            self.slider_temp.value = t
            self.lbl_temp.value = f"{t}K"
            try:
                self.slider_temp.update()
                self.lbl_temp.update()
            except Exception:
                pass
