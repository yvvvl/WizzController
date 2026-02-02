import flet as ft
import colorsys
import logging
import math
import re
import time
import io
import threading
from PIL import Image
from ui.styles import Theme
from ui import flet_overlays as overlays
from config.favorites_manager import FavoritesManager
from config.bulbs_manager import BulbsManager
from ui.wiz_constants import STATIC_SCENES, DYNAMIC_SCENES, RICH_RAINBOW

class ColorPanel(ft.Container):
    def __init__(self, wiz_manager, on_bg_change=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.wiz = wiz_manager
        self.fav_manager = FavoritesManager()
        self.bulbs_manager = BulbsManager()
        self.expand = True
        self._on_bg_change = on_bg_change

        # Target actual (None = todas las bombillas)
        self._target_ip: str | None = None

        # Capacidades detectadas (heurÃ­stico basado en el Ãºltimo estado leÃ­do)
        self._caps = {
            "rgb": True,
            "white": True,
        }

        # Estado estilo WiZ Pro (PilotingLightStateInput)
        self._state: dict[str, object] = {
            "state": True,
            "dimming": 100,   # 10-100
            "r": 255,
            "g": 0,
            "b": 0,
            "cw": 0,
            "ww": 0,
            "temperature": 4200,
            "sceneId": 0,
            "speed": 100,     # 20-200
            "ratio": 0,
        }

        self._pending_state: dict[str, object] | None = None

        # EnvÃ­o de comandos: un solo worker (evita crear miles de Timer threads)
        self._send_event = threading.Event()
        self._send_stop = threading.Event()
        self._send_lock = threading.Lock()
        self._send_thread: threading.Thread | None = None
        self._send_scheduled_at = 0.0
        self._send_delay_s = 0.12

        # Throttle de updates UI durante drag
        self._last_preview_ui_t = 0.0

        # Cache pequeÃ±o para imÃ¡genes del picker (hue -> PNG bytes)
        self._sv_cache: dict[int, bytes] = {}
        self._sv_cache_order: list[int] = []

        self._build_ui()

    def did_unmount(self):
        self._stop_send_worker()

    def _schedule_send(self, delay_s: float = 0.12) -> None:
        # Mantener siempre el Ãºltimo estado pendiente y enviar cuando el usuario se detiene.
        try:
            self._start_send_worker()
            with self._send_lock:
                self._send_delay_s = float(delay_s)
                self._send_scheduled_at = time.monotonic()
            self._send_event.set()
        except Exception:
            # Si algo falla, no romper la UI.
            pass

    def _start_send_worker(self) -> None:
        if self._send_thread and self._send_thread.is_alive():
            return
        self._send_stop.clear()

        def _loop():
            while not self._send_stop.is_set():
                self._send_event.wait()
                self._send_event.clear()
                if self._send_stop.is_set():
                    break

                # Espera "debounced": si llegan nuevos schedule, reprograma.
                while not self._send_stop.is_set():
                    with self._send_lock:
                        scheduled_at = float(self._send_scheduled_at)
                        delay_s = float(self._send_delay_s)
                    remaining = (scheduled_at + delay_s) - time.monotonic()
                    if remaining <= 0:
                        break
                    # Si llega otro schedule durante la espera, re-evaluar.
                    self._send_event.wait(timeout=min(0.12, max(0.01, remaining)))
                    if self._send_event.is_set():
                        self._send_event.clear()
                        continue

                if self._send_stop.is_set():
                    break

                st = self._pending_state
                if not st:
                    continue
                self._pending_state = None
                try:
                    self._send_state_blocking(st)
                except Exception:
                    self.logger.exception("Error enviando estado")

        self._send_thread = threading.Thread(target=_loop, daemon=True)
        self._send_thread.start()

    def _stop_send_worker(self) -> None:
        try:
            self._send_stop.set()
            self._send_event.set()
            if self._send_thread and self._send_thread.is_alive():
                self._send_thread.join(timeout=0.4)
        except Exception:
            pass

    def _send_state_blocking(self, st: dict[str, object]) -> None:
        # Corre SIEMPRE fuera del hilo UI.
        try:
            if hasattr(self.wiz, "set_user_interacting"):
                self.wiz.set_user_interacting(0.9)
        except Exception:
            pass

        try:
            if hasattr(self.wiz, "apply_piloting_state"):
                self.wiz.apply_piloting_state(st, ip=self._target_ip, emit=False)
                return
        except Exception:
            self.logger.exception("Error aplicando piloting state")

        # Fallback mÃ­nimo si por alguna razÃ³n no existe apply_piloting_state
        try:
            if "dimming" in st:
                self.wiz.set_brightness(int(st["dimming"]), ip=self._target_ip, emit=False)
            if "temperature" in st:
                self.wiz.set_white(int(st["temperature"]), ip=self._target_ip, emit=False)
            if all(k in st for k in ("r", "g", "b")):
                self.wiz.set_rgb(int(st["r"]), int(st["g"]), int(st["b"]), ip=self._target_ip, emit=False)
            if "sceneId" in st:
                self.wiz.set_scene(int(st["sceneId"]), ip=self._target_ip)
        except Exception:
            self.logger.exception("Error enviando comando (fallback)")

    def did_mount(self):
        self._start_send_worker()
        self._refresh_targets()
        self._refresh_favorites()

    def _refresh_targets(self) -> None:
        """Refresca el dropdown de bombillas (guardadas + detectadas)."""
        try:
            saved = self.bulbs_manager.get_bulbs() if hasattr(self.bulbs_manager, "get_bulbs") else {}
        except Exception:
            saved = {}

        detected: dict[str, dict] = {}
        try:
            if hasattr(self.wiz, "get_bulb_states_snapshot"):
                snap = self.wiz.get_bulb_states_snapshot() or {}
                for ip, st in snap.items():
                    detected[ip] = {"ip": ip, "reachable": bool(st.get("reachable", False))}
        except Exception:
            pass

        ips = sorted(set(list(saved.keys()) + list(detected.keys())))
        opts = [ft.dropdown.Option("", "Todas")]
        for ip in ips:
            name = None
            try:
                name = saved.get(ip, {}).get("name")
            except Exception:
                name = None
            label = f"{name} ({ip})" if name else ip
            opts.append(ft.dropdown.Option(ip, label))

        try:
            self.dd_target.options = opts
            # Mantener selecciÃ³n si sigue existiendo
            self.dd_target.value = self._target_ip or ""
            self.dd_target.update()
        except Exception:
            pass

        self._update_caps_from_target()

    def _update_caps_from_target(self) -> None:
        """AutodetecciÃ³n simple: ajusta UI segÃºn lo que reporta la bombilla seleccionada."""
        ip = self._target_ip
        st = None
        if ip and hasattr(self.wiz, "get_bulb_state"):
            try:
                st = self.wiz.get_bulb_state(ip)
            except Exception:
                st = None

        # Si no hay estado especÃ­fico, asumimos todo (modo global o aÃºn sin polling)
        if not isinstance(st, dict):
            self._caps = {"rgb": True, "white": True}
        else:
            self._caps = {
                "rgb": st.get("rgb") is not None,
                "white": st.get("temp") is not None,
            }

        # Aplica visibilidad
        try:
            self.tab_simple_color.visible = bool(self._caps.get("rgb", True))
            self.tab_simple_white.visible = bool(self._caps.get("white", True))
            # Si no hay RGB, saltar a Blanco automÃ¡ticamente
            if not self._caps.get("rgb", True) and self._caps.get("white", True):
                self.simple_tabs.selected_index = 1
            elif not self._caps.get("white", True) and self._caps.get("rgb", True):
                self.simple_tabs.selected_index = 0
            self.simple_tabs.update()
        except Exception:
            pass

    def _build_ui(self):
        # --- Utilidades ---
        def _rgb_to_hex(r: int, g: int, b: int) -> str:
            return "#{:02x}{:02x}{:02x}".format(max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b))))

        def _hex_to_rgb(s: str) -> tuple[int, int, int] | None:
            s = (s or "").strip().lower()
            if not s:
                return None
            if not s.startswith("#"):
                s = "#" + s
            if not re.fullmatch(r"#[0-9a-f]{6}", s):
                return None
            h = s.lstrip("#")
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

        # --- Preview ---
        self.preview_box = ft.Container(
            width=130,
            height=130,
            border_radius=65,
            bgcolor=Theme.PRIMARY,
            border=ft.border.all(4, Theme.BG_CARD),
            shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.45, Theme.PRIMARY), spread_radius=1, offset=ft.Offset(0, 0)),
            alignment=ft.Alignment(0, 0),
            content=ft.Icon(ft.icons.LIGHTBULB, color=ft.Colors.with_opacity(0.6, Theme.TEXT_MAIN), size=40),
        )

        # --- Controles globales ---
        self.switch_power = ft.Switch(
            label="Encendido",
            value=True,
            active_color=Theme.ACCENT,
            on_change=self._on_power_change,
        )
        self.slider_dimming = ft.Slider(
            min=10,
            max=100,
            value=int(self._state["dimming"]),
            divisions=90,
            active_color=Theme.PRIMARY,
            on_change=self._on_dimming_change,
        )

        # Selector de bombilla (autocalibraciÃ³n/auto-capacidades)
        self.dd_target = ft.Dropdown(
            label="Bombilla",
            options=[ft.dropdown.Option("", "Todas")],
            value="",
            bgcolor=Theme.BG_DARK,
            color=Theme.TEXT_MAIN,
        )

        def _on_target_select(e):
            v = (e.control.value or "").strip()
            self._target_ip = v or None
            self._update_caps_from_target()

        self.dd_target.on_select = _on_target_select

        self.sw_advanced = ft.Switch(
            label="Avanzado (WiZ Pro)",
            value=False,
            active_color=Theme.PRIMARY,
        )

        header_controls = ft.Container(
            padding=20,
            bgcolor=Theme.CARD_BG,
            border_radius=24,
            border=ft.border.all(1, ft.Colors.with_opacity(0.10, Theme.TEXT_MAIN)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(expand=True),
                            ft.Container(content=self.dd_target, width=300),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row([self.preview_box], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=18, color="transparent"),
                    ft.Row(
                        [
                            self.switch_power,
                            ft.Container(expand=True),
                            self.sw_advanced,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self._build_slider_row(ft.icons.BRIGHTNESS_6, "Brillo", self.slider_dimming),
                    ft.Text("Encendido = ON/OFF. Brillo = intensidad (10100).", size=11, color=Theme.TEXT_MUTED),
                ]
            ),
        )

        # --- MODO SIMPLE (bonito y fÃ¡cil): Color picker SV + Hue + Kelvin + Presets ---
        self._picker_h = 0.0
        self._picker_s = 1.0
        self._picker_v = 1.0

        self.picker_hue = ft.Slider(
            min=0,
            max=360,
            value=0,
            divisions=360,
            active_color=Theme.PRIMARY,
            on_change_end=self._on_picker_hue_end,
        )

        self.sv_image = ft.Image(
            src=self._render_sv_png_bytes(self._picker_h),
            width=240,
            height=240,
            fit=ft.BoxFit.FILL,
            filter_quality=ft.FilterQuality.LOW,
        )
        self.sv_cursor = ft.Container(
            width=16,
            height=16,
            border_radius=8,
            border=ft.border.all(2, Theme.TEXT_MAIN),
            bgcolor=ft.Colors.with_opacity(0.10, Theme.BG_DARK),
            left=240 - 16,
            top=0,
        )
        self.sv_stack = ft.Stack(
            controls=[self.sv_image, self.sv_cursor],
            width=240,
            height=240,
        )
        self.sv_surface = ft.Container(
            width=240,
            height=240,
            border_radius=14,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            border=ft.border.all(1, ft.Colors.with_opacity(0.12, Theme.TEXT_MAIN)),
            content=self.sv_stack,
        )
        self.sv_gesture = ft.GestureDetector(
            content=self.sv_surface,
            on_tap_down=self._on_sv_pick,
            on_pan_start=self._on_sv_pick,
            on_pan_update=self._on_sv_pick,
        )

        self.tf_hex_simple = ft.TextField(
            label="Hex",
            value=_rgb_to_hex(self._state["r"], self._state["g"], self._state["b"]),
            color=Theme.TEXT_MAIN,
            bgcolor=Theme.BG_DARK,
        )

        def _on_hex_simple(_e):
            rgb = _hex_to_rgb(self.tf_hex_simple.value)
            if not rgb:
                self.tf_hex_simple.error_text = "Usa #rrggbb"
                try:
                    self.tf_hex_simple.update()
                except Exception:
                    pass
                return
            self.tf_hex_simple.error_text = None
            r, g, b = rgb
            try:
                self.tf_hex_simple.update()
            except Exception:
                pass
            self._apply_rgb(r, g, b, update_hex=False)

        self.tf_hex_simple.on_submit = _on_hex_simple
        self.tf_hex_simple.on_blur = _on_hex_simple

        # Kelvin simple separado del modo avanzado
        self.slider_temp_simple = ft.Slider(
            min=2200,
            max=6500,
            value=int(self._state["temperature"]),
            divisions=430,
            active_color=Theme.WARNING,
            on_change_end=lambda e: self._set_temp(int(e.control.value)),
        )

        presets_row = ft.Row(
            wrap=True,
            spacing=8,
            run_spacing=8,
            controls=[
                ft.Container(
                    width=22,
                    height=22,
                    border_radius=11,
                    bgcolor=c,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.25, Theme.TEXT_MAIN)),
                    tooltip=c,
                    on_click=(lambda _e, c=c: self._apply_hex_preset(c)),
                    ink=True,
                )
                for c in RICH_RAINBOW[:12]
            ],
        )

        self.tab_simple_color = ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("Color (RGB)", style=Theme.H2),
                    ft.Row(
                        [
                            self.sv_gesture,
                            ft.Container(width=16),
                            ft.Column(
                                [
                                    ft.Text("Picker", size=12, color=Theme.TEXT_MUTED),
                                    self.tf_hex_simple,
                                    self._build_slider_row(ft.icons.TUNE, "Hue", self.picker_hue),
                                    ft.Text("Tip: arrastra en el cuadro para elegir color.", size=11, color=Theme.TEXT_MUTED),
                                ],
                                spacing=10,
                                expand=True,
                            ),
                        ],
                        wrap=True,
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Text("Presets", size=12, color=Theme.TEXT_MUTED),
                    presets_row,
                ],
                spacing=12,
            ),
        )

        self.tab_simple_white = ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("Blancos", style=Theme.H2),
                    self._build_slider_row(ft.icons.THERMOSTAT, "Temperatura", self.slider_temp_simple),
                    ft.Row(
                        [
                            ft.ElevatedButton("2700K", style=Theme.BUTTON_STYLE_SECONDARY, on_click=lambda _e: self._set_temp(2700)),
                            ft.ElevatedButton("4200K", style=Theme.BUTTON_STYLE_SECONDARY, on_click=lambda _e: self._set_temp(4200)),
                            ft.ElevatedButton("6500K", style=Theme.BUTTON_STYLE_SECONDARY, on_click=lambda _e: self._set_temp(6500)),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=12,
            ),
        )

        simple_bar = ft.TabBar(
            tabs=[ft.Tab(label="Color"), ft.Tab(label="Blanco")],
            indicator_color=Theme.PRIMARY,
            divider_color="transparent",
            label_color=Theme.PRIMARY,
            unselected_label_color=Theme.TEXT_MUTED,
        )
        self.simple_view = ft.TabBarView(controls=[self.tab_simple_color, self.tab_simple_white], expand=True)
        self.simple_tabs = ft.Tabs(
            content=ft.Column([simple_bar, self.simple_view], expand=True, spacing=0),
            length=2,
            selected_index=0,
            expand=True,
        )

        simple_card = ft.Container(
            padding=16,
            bgcolor=Theme.CARD_BG,
            border_radius=24,
            border=ft.border.all(1, ft.Colors.with_opacity(0.10, Theme.TEXT_MAIN)),
            content=self.simple_tabs,
        )

        # --- TAB: RGB ---
        self.tf_hex = ft.TextField(label="Hex", value=_rgb_to_hex(self._state["r"], self._state["g"], self._state["b"]), color="white", bgcolor=Theme.BG_DARK)
        self.slider_r = ft.Slider(min=0, max=255, value=int(self._state["r"]), divisions=255, active_color="#ef4444", on_change=self._on_rgb_preview, on_change_end=self._on_rgb_commit)
        self.slider_g = ft.Slider(min=0, max=255, value=int(self._state["g"]), divisions=255, active_color="#22c55e", on_change=self._on_rgb_preview, on_change_end=self._on_rgb_commit)
        self.slider_b = ft.Slider(min=0, max=255, value=int(self._state["b"]), divisions=255, active_color="#3b82f6", on_change=self._on_rgb_preview, on_change_end=self._on_rgb_commit)

        def _on_hex(_e):
            rgb = _hex_to_rgb(self.tf_hex.value)
            if not rgb:
                self.tf_hex.error_text = "Usa #rrggbb"
                try:
                    self.tf_hex.update()
                except Exception:
                    pass
                return
            self.tf_hex.error_text = None
            r, g, b = rgb
            self.slider_r.value = r
            self.slider_g.value = g
            self.slider_b.value = b
            try:
                self.slider_r.update(); self.slider_g.update(); self.slider_b.update(); self.tf_hex.update()
            except Exception:
                pass
            self._apply_rgb(r, g, b, update_hex=False)

        self.tf_hex.on_submit = _on_hex
        self.tf_hex.on_blur = _on_hex

        tab_rgb = ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("WiZ Pro: r/g/b (0-255)", size=12, color=Theme.TEXT_MUTED),
                    self.tf_hex,
                    ft.Row([ft.Text("R", color="#ef4444", width=18), self.slider_r], spacing=10),
                    ft.Row([ft.Text("G", color="#22c55e", width=18), self.slider_g], spacing=10),
                    ft.Row([ft.Text("B", color="#3b82f6", width=18), self.slider_b], spacing=10),
                ],
                spacing=10,
            ),
        )

        # --- TAB: Temperatura ---
        self.slider_temp = ft.Slider(min=2200, max=6500, value=int(self._state["temperature"]), divisions=430, active_color="#fbbf24", on_change=self._on_temperature_change)
        tab_temp = ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("WiZ Pro: temperature (K)", size=12, color=Theme.TEXT_MUTED),
                    self._build_slider_row(ft.icons.THERMOSTAT, "Kelvin", self.slider_temp),
                ],
                spacing=10,
            ),
        )

        # --- TAB: Canales (RGB + CW/WW) ---
        self.slider_cw = ft.Slider(min=0, max=255, value=int(self._state["cw"]), divisions=255, active_color="#60a5fa", on_change=self._on_channels_change)
        self.slider_ww = ft.Slider(min=0, max=255, value=int(self._state["ww"]), divisions=255, active_color="#f59e0b", on_change=self._on_channels_change)
        tab_channels = ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("WiZ Pro: r/g/b + cw/ww (0-255)", size=12, color=Theme.TEXT_MUTED),
                    ft.Row([ft.Text("CW", color="#60a5fa", width=30), self.slider_cw], spacing=10),
                    ft.Row([ft.Text("WW", color="#f59e0b", width=30), self.slider_ww], spacing=10),
                ],
                spacing=10,
            ),
        )

        # --- TAB: Escena + speed ---
        all_scenes = STATIC_SCENES + DYNAMIC_SCENES
        self.dd_scene = ft.Dropdown(
            label="sceneId",
            options=[ft.dropdown.Option(str(s["id"]), s["name"]) for s in all_scenes],
            value=str(all_scenes[0]["id"]) if all_scenes else None,
            bgcolor=Theme.BG_DARK,
            color="white",
        )
        self.dd_scene.on_select = self._on_scene_select
        self.slider_speed = ft.Slider(min=20, max=200, value=int(self._state["speed"]), divisions=180, active_color=Theme.ACCENT, on_change=self._on_speed_change)
        tab_scene = ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("WiZ Pro: sceneId + speed", size=12, color=Theme.TEXT_MUTED),
                    self.dd_scene,
                    self._build_slider_row(ft.icons.SPEED, "Speed", self.slider_speed),
                ],
                spacing=10,
            ),
        )

        tab_bar = ft.TabBar(
            tabs=[
                ft.Tab(label="RGB"),
                ft.Tab(label="Temp"),
                ft.Tab(label="CW/WW"),
                ft.Tab(label="Escena"),
            ],
            indicator_color=Theme.PRIMARY,
            divider_color="transparent",
            label_color=Theme.PRIMARY,
            unselected_label_color=Theme.TEXT_MUTED,
            scrollable=False,
        )
        tab_view = ft.TabBarView(controls=[tab_rgb, tab_temp, tab_channels, tab_scene], expand=True)
        self.tabs = ft.Tabs(
            content=ft.Column([tab_bar, tab_view], expand=True, spacing=0),
            length=4,
            selected_index=0,
            expand=True,
        )

        advanced_card = ft.Container(
            padding=16,
            bgcolor=Theme.CARD_BG,
            border_radius=24,
            border=ft.border.all(1, ft.Colors.with_opacity(0.10, Theme.TEXT_MAIN)),
            content=self.tabs,
            visible=False,
        )

        def _toggle_adv(e):
            advanced_card.visible = bool(e.control.value)
            try:
                advanced_card.update()
            except Exception:
                pass

        self.sw_advanced.on_change = _toggle_adv

        # 4. Favoritos + escenas separadas
        self.favs_grid = ft.Column(spacing=8)
        # Preview liviano (la lista completa se abre en diÃ¡logo)
        self.scenes_static_grid = self._build_scenes_grid(STATIC_SCENES, limit=12)
        self.scenes_dynamic_grid = self._build_scenes_grid(DYNAMIC_SCENES, limit=12)

        # --- Vista re-imaginada (decorada + rÃ¡pida) ---
        picker_card = ft.Container(
            padding=16,
            bgcolor=Theme.CARD_BG,
            border_radius=24,
            border=ft.border.all(1, ft.Colors.with_opacity(0.10, Theme.TEXT_MAIN)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.icons.COLOR_LENS, color=Theme.PRIMARY),
                            ft.Text("Color Picker", style=Theme.H2),
                        ],
                        spacing=10,
                    ),
                    simple_card,
                ],
                spacing=12,
            ),
        )

        adv_card_wrapped = ft.Container(
            padding=16,
            bgcolor=Theme.CARD_BG,
            border_radius=24,
            border=ft.border.all(1, ft.Colors.with_opacity(0.10, Theme.TEXT_MAIN)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.icons.SETTINGS, color=Theme.TEXT_MUTED),
                            ft.Text("Avanzado (WiZ Pro)", style=Theme.H2),
                        ],
                        spacing=10,
                    ),
                    advanced_card,
                ],
                spacing=12,
            ),
        )

        favorites_card = ft.Container(
            padding=16,
            bgcolor=Theme.CARD_BG,
            border_radius=24,
            border=ft.border.all(1, ft.Colors.with_opacity(0.10, Theme.TEXT_MAIN)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Mis favoritos", style=Theme.H2),
                            ft.Container(expand=True),
                            ft.IconButton(
                                ft.icons.SAVE_ALT,
                                icon_color=Theme.PRIMARY,
                                tooltip="Guardar el estado actual",
                                on_click=self._save_favorite,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text("Toca  para aplicar. ADV conserva el payload WiZ Pro.", size=11, color=Theme.TEXT_MUTED),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Ver todos",
                                icon=ft.icons.OPEN_IN_NEW,
                                style=Theme.BUTTON_STYLE_SECONDARY,
                                on_click=lambda _e: self._open_all_favorites_dialog(),
                            ),
                            ft.Container(expand=True),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.favs_grid,
                ],
                spacing=10,
            ),
        )

        scenes_tabs = ft.Tabs(
            length=2,
            selected_index=0,
            expand=True,
            content=ft.Column(
                [
                    ft.TabBar(
                        tabs=[ft.Tab(label="EstÃ¡ticas"), ft.Tab(label="DinÃ¡micas")],
                        indicator_color=Theme.PRIMARY,
                        divider_color="transparent",
                        label_color=Theme.PRIMARY,
                        unselected_label_color=Theme.TEXT_MUTED,
                    ),
                    ft.TabBarView(
                        controls=[
                            ft.Container(padding=8, content=self.scenes_static_grid),
                            ft.Container(padding=8, content=self.scenes_dynamic_grid),
                        ],
                        expand=True,
                    ),
                ],
                expand=True,
                spacing=0,
            ),
        )

        scenes_card = ft.Container(
            padding=16,
            bgcolor=Theme.CARD_BG,
            border_radius=24,
            border=ft.border.all(1, ft.Colors.with_opacity(0.10, Theme.TEXT_MAIN)),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.icons.THEATER_COMEDY, color=Theme.ACCENT),
                            ft.Text("Escenas", style=Theme.H2),
                        ],
                        spacing=10,
                    ),
                    ft.Text("Aplican a la bombilla seleccionada (o a todas si estÃ¡ en 'Todas').", size=11, color=Theme.TEXT_MUTED),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Ver todas",
                                icon=ft.icons.OPEN_IN_NEW,
                                style=Theme.BUTTON_STYLE_SECONDARY,
                                on_click=lambda _e: self._open_all_scenes_dialog(),
                            ),
                            ft.Container(expand=True),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=280, content=scenes_tabs),
                ],
                spacing=10,
            ),
        )

        left_col = ft.Column(
            controls=[header_controls, picker_card, adv_card_wrapped],
            spacing=18,
        )
        right_col = ft.Column(
            controls=[favorites_card, scenes_card],
            spacing=18,
        )

        body = ft.ResponsiveRow(
            columns=12,
            spacing=16,
            run_spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    col={
                        ft.ResponsiveRowBreakpoint.XS: 12,
                        ft.ResponsiveRowBreakpoint.MD: 7,
                        ft.ResponsiveRowBreakpoint.LG: 7,
                    },
                    content=left_col,
                ),
                ft.Container(
                    col={
                        ft.ResponsiveRowBreakpoint.XS: 12,
                        ft.ResponsiveRowBreakpoint.MD: 5,
                        ft.ResponsiveRowBreakpoint.LG: 5,
                    },
                    content=right_col,
                ),
            ],
        )

        self.content = ft.Column(
            expand=True,
            scroll="auto",
            spacing=18,
            controls=[
                ft.Text("Estudio Creativo", style=Theme.H1, size=28),
                body,
                ft.Container(height=20),
            ],
        )

    def _make_gradient_slider(self, min_v, max_v, val, grad, change_fn, end_fn=None):
        # Mantener por compatibilidad con versiones anteriores del panel
        return ft.Container(
            height=28,
            border_radius=14,
            gradient=grad,
            content=ft.Slider(
                min=min_v,
                max=max_v,
                value=val,
                on_change=change_fn,
                on_change_end=end_fn,
                active_color="transparent",
                inactive_color="transparent",
                thumb_color=Theme.TEXT_MAIN,
            ),
        )

    def _apply_rgb(self, r: int, g: int, b: int, update_hex: bool = True) -> None:
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))

        self._state["r"] = r
        self._state["g"] = g
        self._state["b"] = b

        hex_c = "#{:02x}{:02x}{:02x}".format(r, g, b)
        if update_hex:
            try:
                self.tf_hex.value = hex_c
                self.tf_hex.error_text = None
                self.tf_hex.update()
            except Exception:
                pass
            try:
                if hasattr(self, "tf_hex_simple"):
                    self.tf_hex_simple.value = hex_c
                    self.tf_hex_simple.error_text = None
                    self.tf_hex_simple.update()
            except Exception:
                pass

        self._set_preview(hex_c)
        self._pending_state = {
            "r": r,
            "g": g,
            "b": b,
            "dimming": int(self._state["dimming"]),
            "state": bool(self._state["state"]),
        }
        self._schedule_send()
        if self._on_bg_change:
            try:
                self._on_bg_change(hex_c)
            except Exception:
                pass

    def _set_preview(self, hex_color: str) -> None:
        try:
            # Throttle: durante drag, evita saturar el canal de updates.
            now = time.monotonic()
            if (now - self._last_preview_ui_t) < 0.03:
                return
            self._last_preview_ui_t = now
            self.preview_box.bgcolor = hex_color
            self.preview_box.shadow.color = ft.Colors.with_opacity(0.45, hex_color)
            self.preview_box.update()
        except Exception:
            pass

    def _build_slider_row(self, icon_name, label_text, slider_control):
        return ft.Row([
            ft.Icon(icon_name, color=Theme.TEXT_MUTED, size=20),
            ft.Container(width=10),
            ft.Text(label_text, color=Theme.TEXT_MAIN, size=14, weight=ft.FontWeight.W_500, width=90),
            ft.Container(content=slider_control, expand=True)
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _on_picker_hue_end(self, e):
        try:
            self._picker_h = float(e.control.value)
        except Exception:
            return
        try:
            self.sv_image.src = self._render_sv_png_bytes(self._picker_h)
            self.sv_image.update()
        except Exception:
            pass
        # Mantener el color actual con el nuevo hue y los mismos S/V
        self._apply_picker_color(schedule=True)

    def _on_sv_pick(self, e):
        # Eventos de GestureDetector varÃ­an; usamos getattr para ser robustos.
        x = getattr(e, "local_x", None)
        y = getattr(e, "local_y", None)
        if x is None or y is None:
            return

        try:
            w = float(getattr(self.sv_surface, "width", 240) or 240)
            h = float(getattr(self.sv_surface, "height", 240) or 240)
            sx = max(0.0, min(1.0, float(x) / max(1.0, w)))
            vy = max(0.0, min(1.0, float(y) / max(1.0, h)))
            self._picker_s = sx
            self._picker_v = 1.0 - vy
        except Exception:
            return

        # Cursor visual
        try:
            cx = max(0.0, min(w - 16.0, sx * w - 8.0))
            cy = max(0.0, min(h - 16.0, vy * h - 8.0))
            self.sv_cursor.left = cx
            self.sv_cursor.top = cy
            self.sv_cursor.update()
        except Exception:
            pass

        self._apply_picker_color(schedule=True)

    def _apply_picker_color(self, schedule: bool = True) -> None:
        try:
            r, g, b = colorsys.hsv_to_rgb(self._picker_h / 360.0, max(0.0, min(1.0, self._picker_s)), max(0.0, min(1.0, self._picker_v)))
        except Exception:
            return
        self._apply_rgb(int(r * 255), int(g * 255), int(b * 255))
        if schedule:
            # El worker debounced se encarga de no spamear.
            self._schedule_send(0.10)

    def _render_sv_png_bytes(self, hue_deg: float, size: int = 240) -> bytes:
        """Genera un cuadro S/V para un Hue fijo (rÃ¡pido y cacheable)."""
        hue_deg = float(hue_deg)
        size = int(max(64, min(360, size)))

        key = int(round(hue_deg)) % 360
        cached = self._sv_cache.get(key)
        if cached is not None:
            return cached

        img = Image.new("RGB", (size, size))
        px = img.load()
        h = (hue_deg % 360.0) / 360.0
        for y in range(size):
            v = 1.0 - (y / (size - 1))
            for x in range(size):
                s = x / (size - 1)
                rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
                px[x, y] = (int(rr * 255), int(gg * 255), int(bb * 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()

        # LRU muy simple
        self._sv_cache[key] = data
        self._sv_cache_order.append(key)
        if len(self._sv_cache_order) > 24:
            old = self._sv_cache_order.pop(0)
            if old in self._sv_cache:
                self._sv_cache.pop(old, None)

        return data

    def _apply_hex_preset(self, hex_color: str) -> None:
        try:
            h = str(hex_color).lstrip("#")
            r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
            self._apply_rgb(r, g, b)
        except Exception:
            pass

    def _set_temp(self, kelvin: int) -> None:
        k = max(2200, min(6500, int(kelvin)))
        self._state["temperature"] = k
        try:
            self.slider_temp_simple.value = k
            self.slider_temp_simple.update()
        except Exception:
            pass
        # Si existen controles avanzados, sincronÃ­zalos sin forzar update
        try:
            if hasattr(self, "slider_temp"):
                self.slider_temp.value = k
        except Exception:
            pass

        self._set_preview(Theme.TEXT_MAIN)
        self._pending_state = {
            "temperature": k,
            "dimming": int(self._state["dimming"]),
            "state": bool(self._state["state"]),
        }
        self._schedule_send(0.08)

    def _on_power_change(self, e):
        self._state["state"] = bool(e.control.value)
        self._pending_state = {"state": bool(self._state["state"])}
        self._schedule_send(0.05)

    def _on_dimming_change(self, e):
        self._state["dimming"] = int(e.control.value)
        self._pending_state = {
            "dimming": int(self._state["dimming"]),
            "state": bool(self._state["state"]),
        }
        self._schedule_send(0.08)

    def _on_rgb_preview(self, _e):
        # Preview suave mientras arrastras (sin flood de send).
        self._apply_rgb(int(self.slider_r.value), int(self.slider_g.value), int(self.slider_b.value))

    def _on_rgb_commit(self, _e):
        # Al soltar, el debounce manda el comando.
        self._pending_state = {
            "r": int(self._state["r"]),
            "g": int(self._state["g"]),
            "b": int(self._state["b"]),
            "dimming": int(self._state["dimming"]),
            "state": bool(self._state["state"]),
        }
        self._schedule_send(0.10)

    def _on_temperature_change(self, e):
        k = int(e.control.value)
        self._state["temperature"] = k
        self._set_preview(Theme.TEXT_MAIN)
        self._pending_state = {
            "temperature": k,
            "dimming": int(self._state["dimming"]),
            "state": bool(self._state["state"]),
        }
        self._schedule_send(0.12)

    def _on_channels_change(self, _e):
        cw = int(self.slider_cw.value)
        ww = int(self.slider_ww.value)
        self._state["cw"] = cw
        self._state["ww"] = ww
        # Mantiene preview basado en RGB
        hex_c = "#{:02x}{:02x}{:02x}".format(int(self._state["r"]), int(self._state["g"]), int(self._state["b"]))
        self._set_preview(hex_c)
        self._pending_state = {
            "r": int(self._state["r"]),
            "g": int(self._state["g"]),
            "b": int(self._state["b"]),
            "cw": cw,
            "ww": ww,
            "dimming": int(self._state["dimming"]),
            "state": bool(self._state["state"]),
        }
        self._schedule_send(0.12)

    def _on_scene_select(self, e):
        try:
            sid = int(e.control.value)
        except Exception:
            return
        self._state["sceneId"] = sid
        self._pending_state = {
            "sceneId": sid,
            "speed": int(self._state["speed"]),
            "dimming": int(self._state["dimming"]),
            "state": bool(self._state["state"]),
        }
        self._schedule_send(0.08)

    def _on_speed_change(self, e):
        self._state["speed"] = int(e.control.value)
        self._pending_state = {
            "sceneId": int(self._state["sceneId"]),
            "speed": int(self._state["speed"]),
            "dimming": int(self._state["dimming"]),
            "state": bool(self._state["state"]),
        }
        self._schedule_send(0.08)

    # did_mount definido arriba (incluye targets + favoritos)

    def _save_favorite(self, e):
        # Guardar el estado actual.
        # En modo simple: guarda RGB o Kelvin.
        # En modo avanzado: guarda el payload completo segÃºn la doc WiZ Pro (incluye scene/speed/cw/ww/etc).
        dim = int(self._state["dimming"])

        is_adv = bool(getattr(self, "sw_advanced", None) and bool(self.sw_advanced.value))
        if not is_adv:
            if int(getattr(self.simple_tabs, "selected_index", 0)) == 1:
                k = int(self._state["temperature"])
                self.fav_manager.add_favorite(f"Blanco {k}K", "white", k, "WB_SUNNY")
            else:
                hex_v = "#{:02x}{:02x}{:02x}".format(int(self._state["r"]), int(self._state["g"]), int(self._state["b"]))
                self.fav_manager.add_favorite("Color Personal", "rgb", hex_v, "COLOR_LENS")
        else:
            # Avanzado (usa pestaÃ±as WiZ Pro)
            if int(self.tabs.selected_index) == 1:
                k = int(self._state["temperature"])
                self.fav_manager.add_favorite(f"Blanco {k}K", "white", k, "WB_SUNNY")
            elif int(self.tabs.selected_index) == 3:
                sid = int(self._state["sceneId"])
                sp = int(self._state["speed"])
                self.fav_manager.add_favorite(
                    f"Escena {sid}",
                    "scene",
                    {"sceneId": sid, "speed": sp, "dimming": dim, "state": True},
                    "THEATER_COMEDY",
                )
            elif int(self.tabs.selected_index) == 2:
                payload = {
                    "r": int(self._state["r"]),
                    "g": int(self._state["g"]),
                    "b": int(self._state["b"]),
                    "cw": int(self._state["cw"]),
                    "ww": int(self._state["ww"]),
                    "dimming": dim,
                    "state": True,
                }
                self.fav_manager.add_favorite("Canales", "channels", payload, "TUNE")
            else:
                hex_v = "#{:02x}{:02x}{:02x}".format(int(self._state["r"]), int(self._state["g"]), int(self._state["b"]))
                self.fav_manager.add_favorite("Color Personal", "rgb", hex_v, "COLOR_LENS")
        self._refresh_favorites()
        overlays.show_snackbar(self.page, "Â¡Color guardado en favoritos!", bgcolor=Theme.SUCCESS)

    def _delete_fav(self, fid):
        self.fav_manager.remove_favorite(fid)
        self._refresh_favorites()

    def _kelvin_to_hex(self, kelvin: int) -> str:
        """AproximaciÃ³n KelvinRGB (suficiente para UI, no fÃ­sica).

        Basado en fÃ³rmulas ampliamente usadas para renderizado de blanco cÃ¡lido/frÃ­o.
        """
        try:
            k = int(kelvin)
        except Exception:
            k = 4200

        k = max(1000, min(40000, k))
        t = k / 100.0

        # Red
        if t <= 66:
            r = 255
        else:
            r = 329.698727446 * ((t - 60.0) ** -0.1332047592)

        # Green
        if t <= 66:
            g = 99.4708025861 * math.log(t) - 161.1195681661
        else:
            g = 288.1221695283 * ((t - 60.0) ** -0.0755148492)

        # Blue
        if t >= 66:
            b = 255
        elif t <= 19:
            b = 0
        else:
            b = 138.5177312231 * math.log(t - 10.0) - 305.0447927307

        r = max(0, min(255, int(round(r))))
        g = max(0, min(255, int(round(g))))
        b = max(0, min(255, int(round(b))))
        return "#{:02x}{:02x}{:02x}".format(r, g, b)

    def _favorite_tooltip(self, fav: dict) -> str:
        name = str(fav.get("name", "Favorito"))
        ftype = str(fav.get("type", "")).lower()
        v = fav.get("value")

        parts: list[str] = [name]
        if isinstance(v, dict):
            parts.append("ADV")

            if all(k in v for k in ("r", "g", "b")):
                parts.append(
                    "rgb: #{:02x}{:02x}{:02x}".format(int(v.get("r", 0)) & 255, int(v.get("g", 0)) & 255, int(v.get("b", 0)) & 255)
                )
            if "temperature" in v:
                parts.append(f"K: {int(v.get('temperature', 0))}")
            if "cw" in v or "ww" in v:
                parts.append(f"cw/ww: {int(v.get('cw', 0))}/{int(v.get('ww', 0))}")
            if "sceneId" in v:
                parts.append(f"sceneId: {int(v.get('sceneId', 0))}")
            if "speed" in v:
                parts.append(f"speed: {int(v.get('speed', 0))}")
            if "ratio" in v:
                parts.append(f"ratio: {int(v.get('ratio', 0))}")
            if "dimming" in v:
                parts.append(f"dim: {int(v.get('dimming', 0))}%")
            if "state" in v:
                parts.append("on" if bool(v.get("state")) else "off")
        else:
            if ftype:
                parts.append(ftype.upper())
            if ftype == "rgb" and v:
                parts.append(f"rgb: {str(v)}")
            if ftype == "white" and v is not None:
                parts.append(f"K: {int(v)}")
            if ftype == "scene" and v is not None:
                parts.append(f"sceneId: {int(v)}")

        return " | ".join([p for p in parts if p])

    def _refresh_favorites(self):
        self.favs_grid.controls.clear()
        scene_colors = {int(s["id"]): s.get("color") for s in (STATIC_SCENES + DYNAMIC_SCENES) if "id" in s}
        favs = list(self.fav_manager.get_favorites() or [])
        max_preview = 10
        for f in favs[:max_preview]:
            v = f.get("value")
            ftype = str(f.get("type", "")).lower()

            tooltip_text = self._favorite_tooltip(f)

            if ftype == "rgb":
                preview = str(v)
            elif isinstance(v, dict) and all(k in v for k in ("r", "g", "b")):
                preview = "#{:02x}{:02x}{:02x}".format(int(v.get("r", 0)) & 255, int(v.get("g", 0)) & 255, int(v.get("b", 0)) & 255)
            elif ftype == "scene" or (isinstance(v, dict) and "sceneId" in v):
                try:
                    sid = int(v.get("sceneId")) if isinstance(v, dict) else int(v)
                except Exception:
                    sid = None
                preview = scene_colors.get(sid) or Theme.TEXT_MUTED
            elif isinstance(v, dict) and "temperature" in v:
                preview = self._kelvin_to_hex(int(v.get("temperature", 4200)))
            elif ftype == "white":
                try:
                    preview = self._kelvin_to_hex(int(v))
                except Exception:
                    preview = self._kelvin_to_hex(4200)
            else:
                preview = Theme.TEXT_MUTED

            shadow_color = ft.Colors.with_opacity(0.35, preview)

            badge = "ADV" if isinstance(v, dict) else ftype.upper() if ftype else "FAV"

            row = ft.Container(
                padding=12,
                border_radius=14,
                bgcolor=Theme.BG_CARD,
                border=ft.border.all(1, ft.Colors.with_opacity(0.10, Theme.TEXT_MAIN)),
                tooltip=tooltip_text,
                content=ft.Row(
                    [
                        ft.Container(
                            width=18,
                            height=18,
                            border_radius=9,
                            bgcolor=preview,
                            border=ft.border.all(1, ft.Colors.with_opacity(0.25, Theme.TEXT_MAIN)),
                            shadow=ft.BoxShadow(blur_radius=8, color=shadow_color),
                        ),
                        ft.Text(f.get("name", "(sin nombre)"), color=Theme.TEXT_MAIN, expand=True, no_wrap=True),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            border_radius=999,
                            bgcolor=ft.Colors.with_opacity(0.18, Theme.PRIMARY if badge == "ADV" else Theme.ACCENT),
                            content=ft.Text(badge, size=10, color=Theme.TEXT_MAIN, weight=ft.FontWeight.BOLD),
                        ),
                        ft.IconButton(ft.icons.PLAY_ARROW, icon_color=Theme.SUCCESS, tooltip="Aplicar", on_click=lambda _e, x=f: self._apply_fav(x)),
                        ft.IconButton(ft.icons.DELETE, icon_color=Theme.ERROR, tooltip="Eliminar", on_click=lambda _e, x=f.get("id"): self._delete_fav(x)),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
            self.favs_grid.controls.append(row)

        try:
            self.favs_grid.update()
        except Exception:
            pass

    def _open_all_favorites_dialog(self) -> None:
        if not self.page:
            return

        favs = list(self.fav_manager.get_favorites() or [])
        scene_colors = {int(s["id"]): s.get("color") for s in (STATIC_SCENES + DYNAMIC_SCENES) if "id" in s}

        lst = ft.Column(spacing=8, scroll="auto")
        for f in favs:
            v = f.get("value")
            ftype = str(f.get("type", "")).lower()
            tooltip_text = self._favorite_tooltip(f)

            if ftype == "rgb":
                preview = str(v)
            elif isinstance(v, dict) and all(k in v for k in ("r", "g", "b")):
                preview = "#{:02x}{:02x}{:02x}".format(int(v.get("r", 0)) & 255, int(v.get("g", 0)) & 255, int(v.get("b", 0)) & 255)
            elif ftype == "scene" or (isinstance(v, dict) and "sceneId" in v):
                try:
                    sid = int(v.get("sceneId")) if isinstance(v, dict) else int(v)
                except Exception:
                    sid = None
                preview = scene_colors.get(sid) or Theme.TEXT_MUTED
            elif isinstance(v, dict) and "temperature" in v:
                preview = self._kelvin_to_hex(int(v.get("temperature", 4200)))
            elif ftype == "white":
                try:
                    preview = self._kelvin_to_hex(int(v))
                except Exception:
                    preview = self._kelvin_to_hex(4200)
            else:
                preview = Theme.TEXT_MUTED

            shadow_color = ft.Colors.with_opacity(0.35, preview)
            badge = "ADV" if isinstance(v, dict) else ftype.upper() if ftype else "FAV"

            row = ft.Container(
                padding=12,
                border_radius=14,
                bgcolor=Theme.BG_CARD,
                border=ft.border.all(1, ft.Colors.with_opacity(0.10, Theme.TEXT_MAIN)),
                tooltip=tooltip_text,
                content=ft.Row(
                    [
                        ft.Container(
                            width=18,
                            height=18,
                            border_radius=9,
                            bgcolor=preview,
                            border=ft.border.all(1, ft.Colors.with_opacity(0.25, Theme.TEXT_MAIN)),
                            shadow=ft.BoxShadow(blur_radius=8, color=shadow_color),
                        ),
                        ft.Text(f.get("name", "(sin nombre)"), color=Theme.TEXT_MAIN, expand=True, no_wrap=True),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            border_radius=999,
                            bgcolor=ft.Colors.with_opacity(0.18, Theme.PRIMARY if badge == "ADV" else Theme.ACCENT),
                            content=ft.Text(badge, size=10, color=Theme.TEXT_MAIN, weight=ft.FontWeight.BOLD),
                        ),
                        ft.IconButton(ft.icons.PLAY_ARROW, icon_color=Theme.SUCCESS, tooltip="Aplicar", on_click=lambda _e, x=f: self._apply_fav(x)),
                        ft.IconButton(ft.icons.DELETE, icon_color=Theme.ERROR, tooltip="Eliminar", on_click=lambda _e, x=f.get("id"): self._delete_fav(x)),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
            lst.controls.append(row)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Todos los favoritos", color=Theme.TEXT_MAIN),
            content=ft.Container(width=720, height=520, content=lst),
            actions=[ft.TextButton("Cerrar", on_click=lambda _e: overlays.close_dialog(self.page, dlg))],
        )
        overlays.show_dialog(self.page, dlg)

    def _open_all_scenes_dialog(self) -> None:
        if not self.page:
            return

        grid_static = self._build_scenes_grid(STATIC_SCENES, limit=None)
        grid_dynamic = self._build_scenes_grid(DYNAMIC_SCENES, limit=None)

        tabs = ft.Tabs(
            length=2,
            selected_index=0,
            expand=True,
            content=ft.Column(
                [
                    ft.TabBar(
                        tabs=[ft.Tab(label="EstÃ¡ticas"), ft.Tab(label="DinÃ¡micas")],
                        indicator_color=Theme.PRIMARY,
                        divider_color="transparent",
                        label_color=Theme.PRIMARY,
                        unselected_label_color=Theme.TEXT_MUTED,
                    ),
                    ft.TabBarView(
                        controls=[
                            ft.Container(padding=8, content=grid_static),
                            ft.Container(padding=8, content=grid_dynamic),
                        ],
                        expand=True,
                    ),
                ],
                expand=True,
                spacing=0,
            ),
        )

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Todas las escenas", color=Theme.TEXT_MAIN),
            content=ft.Container(width=760, height=560, content=tabs),
            actions=[ft.TextButton("Cerrar", on_click=lambda _e: overlays.close_dialog(self.page, dlg))],
        )
        overlays.show_dialog(self.page, dlg)

    def _apply_fav(self, f):
        v = f.get("value")

        def _do():
            try:
                if isinstance(v, dict) and hasattr(self.wiz, "apply_piloting_state"):
                    self.wiz.apply_piloting_state(v, ip=self._target_ip)
                    return
                if f.get("type") == "rgb":
                    h = str(v).lstrip('#')
                    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                    self.wiz.set_rgb(*rgb, ip=self._target_ip)
                elif f.get("type") == "white":
                    self.wiz.set_white(int(v), ip=self._target_ip)
                elif f.get("type") == "scene":
                    if isinstance(v, dict) and hasattr(self.wiz, "apply_piloting_state"):
                        self.wiz.apply_piloting_state(v, ip=self._target_ip)
                    else:
                        self.wiz.set_scene(int(v), ip=self._target_ip)
            except Exception:
                self.logger.exception("Error aplicando favorito")

        try:
            if self.page:
                self.page.run_thread(_do)
            else:
                _do()
        except Exception:
            _do()

    def _apply_scene(self, scene_id: int) -> None:
        def _do():
            try:
                self.wiz.set_scene(int(scene_id), ip=self._target_ip)
            except Exception:
                self.logger.exception("Error aplicando escena")

        try:
            if self.page:
                self.page.run_thread(_do)
            else:
                _do()
        except Exception:
            _do()

    def _build_scenes_grid(self, scenes, limit: int | None = None):
        items = list(scenes or [])
        if isinstance(limit, int) and limit > 0:
            items = items[:limit]
        return ft.Row(wrap=True, spacing=15, run_spacing=15, controls=[
            ft.Container(
                width=85, height=70, bgcolor=Theme.BG_CARD, border_radius=16,
                border=ft.border.all(1, ft.Colors.with_opacity(0.1, s["color"])),
                content=ft.Column([
                    ft.Icon(s["icon"], color=s["color"], size=24), 
                    ft.Text(s["name"], size=11, weight=ft.FontWeight.W_500, no_wrap=True)
                ], alignment="center", spacing=5),
                on_click=lambda _e, x=s["id"]: self._apply_scene(x),
                # CorrecciÃ³n tambiÃ©n aquÃ­ para seguridad
                ink=True, shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.with_opacity(0.1, s["color"]))
            ) for s in items
        ])
