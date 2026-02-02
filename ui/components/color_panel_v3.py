import flet as ft
import colorsys
import logging
import re
import time
import io
import base64
import threading
from PIL import Image
from ui.styles import Theme
from config.favorites_manager import FavoritesManager
from config.bulbs_manager import BulbsManager
from ui.wiz_constants import STATIC_SCENES, DYNAMIC_SCENES, RICH_RAINBOW


class ColorPanelV3(ft.Column):
    """Color picker hermoso, fluido, sin latencia. Layout simple y directo."""

    def __init__(self, wiz_manager, on_bg_change=None):
        super().__init__(expand=True, scroll="auto", spacing=20)
        self.logger = logging.getLogger(__name__)
        self.wiz = wiz_manager
        self.fav_manager = FavoritesManager()
        self.bulbs_manager = BulbsManager()
        self._on_bg_change = on_bg_change

        self._target_ip: str | None = None
        self._state: dict[str, object] = {
            "state": True,
            "dimming": 100,
            "r": 255,
            "g": 0,
            "b": 0,
            "cw": 0,
            "ww": 0,
            "temperature": 4200,
            "sceneId": 0,
            "speed": 100,
            "ratio": 0,
        }

        self._pending_state: dict[str, object] | None = None
        self._send_event = threading.Event()
        self._send_stop = threading.Event()
        self._send_lock = threading.Lock()
        self._send_thread: threading.Thread | None = None
        self._send_scheduled_at = 0.0
        self._send_delay_s = 0.10

        self._last_preview_ui_t = 0.0
        self._sv_cache: dict[int, bytes] = {}
        self._sv_cache_order: list[int] = []

        # Picker state
        self._picker_h = 0.0
        self._picker_s = 1.0
        self._picker_v = 1.0

        self.padding = ft.padding.symmetric(horizontal=20, vertical=20)
        self.bgcolor = Theme.BG_DARK
        
        self._build_ui()

    def did_unmount(self):
        self._stop_send_worker()

    def _build_ui(self):
        """Build UI simple, limpio, sin anidaciÃ³n compleja."""

        def _rgb_to_hex(r: int, g: int, b: int) -> str:
            return "#{:02x}{:02x}{:02x}".format(
                max(0, min(255, int(r))),
                max(0, min(255, int(g))),
                max(0, min(255, int(b))),
            )

        # --- Header ---
        header = ft.Row(
            [
                ft.Icon(ft.icons.COLOR_LENS, color=Theme.PRIMARY, size=28),
                ft.Text("Estudio Creativo", style=Theme.H1, size=24),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- Target selector ---
        self.dd_target = ft.Dropdown(
            label="Bombilla",
            options=[ft.dropdown.Option("", "Todas")],
            value="",
            bgcolor=Theme.BG_DARK,
            color=Theme.TEXT_MAIN,
            width=250,
        )

        def _on_target_select(e):
            v = (e.control.value or "").strip()
            self._target_ip = v or None
            self._update_caps_from_target()

        self.dd_target.on_select = _on_target_select

        # --- SV Picker (260x260) ---
        self.sv_image = ft.Image(
            src=self._render_sv_png_b64(self._picker_h),
            width=260,
            height=260,
            fit=ft.BoxFit.FILL,
            filter_quality=ft.FilterQuality.LOW,
        )

        self.sv_cursor = ft.Container(
            width=14,
            height=14,
            border_radius=7,
            border=ft.border.all(2, Theme.TEXT_MAIN),
            bgcolor=ft.Colors.with_opacity(0.15, Theme.BG_DARK),
            left=260 - 14,
            top=0,
            animate="150ms",
        )

        self.sv_stack = ft.Stack(
            controls=[self.sv_image, self.sv_cursor],
            width=260,
            height=260,
        )

        self.sv_surface = ft.Container(
            width=260,
            height=260,
            border_radius=16,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            border=ft.border.all(2, ft.Colors.with_opacity(0.2, Theme.PRIMARY)),
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.3, Theme.PRIMARY), spread_radius=0),
            content=self.sv_stack,
        )

        self.sv_gesture = ft.GestureDetector(
            content=self.sv_surface,
            on_tap_down=self._on_sv_pick,
            on_pan_start=self._on_sv_pick,
            on_pan_update=self._on_sv_pick,
        )

        # --- Hue slider ---
        self.picker_hue = ft.Slider(
            min=0,
            max=360,
            value=0,
            divisions=360,
            active_color=Theme.PRIMARY,
            thumb_color=Theme.ACCENT,
            on_change_end=self._on_picker_hue_end,
            width=260,
        )

        hue_row = ft.Column(
            [
                ft.Text("Matiz", size=11, color=Theme.TEXT_MUTED, weight="w500"),
                self.picker_hue,
            ],
            spacing=6,
        )

        # --- Hex input ---
        self.tf_hex = ft.TextField(
            label="Hex",
            value=_rgb_to_hex(self._state["r"], self._state["g"], self._state["b"]),
            color=Theme.TEXT_MAIN,
            bgcolor=Theme.BG_DARK,
            border_color=Theme.TEXT_MUTED,
            width=130,
        )

        def _on_hex(_e):
            s = (self.tf_hex.value or "").strip().lower()
            if not s:
                return
            if not s.startswith("#"):
                s = "#" + s
            if not re.fullmatch(r"#[0-9a-f]{6}", s):
                self.tf_hex.error_text = "#rrggbb"
                try:
                    self.tf_hex.update()
                except Exception:
                    pass
                return
            self.tf_hex.error_text = None
            try:
                self.tf_hex.update()
            except Exception:
                pass
            h = s.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            self._apply_rgb(r, g, b, update_hex=False)

        self.tf_hex.on_submit = _on_hex
        self.tf_hex.on_blur = _on_hex

        # --- Preview box ---
        self.preview_box = ft.Container(
            width=100,
            height=100,
            border_radius=50,
            bgcolor=Theme.PRIMARY,
            border=ft.border.all(3, Theme.ACCENT),
            shadow=ft.BoxShadow(
                blur_radius=24,
                color=ft.Colors.with_opacity(0.5, Theme.PRIMARY),
                spread_radius=2,
            ),
        )

        # --- Picker y preview lado a lado ---
        picker_and_preview = ft.Row(
            [
                ft.Column(
                    [
                        self.sv_gesture,
                        hue_row,
                        ft.Row([ft.Text("Color", size=11, color=Theme.TEXT_MUTED), self.tf_hex], spacing=10),
                    ],
                    spacing=12,
                ),
                ft.Column([self.preview_box], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ],
            spacing=24,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # --- Presets (bonitos) ---
        presets = ft.Row(
            wrap=True,
            spacing=10,
            run_spacing=10,
            controls=[
                ft.Container(
                    width=36,
                    height=36,
                    border_radius=18,
                    bgcolor=c,
                    border=ft.border.all(2, ft.Colors.with_opacity(0.3, Theme.TEXT_MAIN)),
                    shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.2, c)),
                    tooltip=c,
                    on_click=(lambda _e, c=c: self._apply_hex_preset(c)),
                    ink=True,
                    animate="150ms",
                )
                for c in RICH_RAINBOW
            ],
        )

        presets_card = ft.Container(
            padding=16,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.05, Theme.TEXT_MAIN),
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, Theme.TEXT_MAIN)),
            content=ft.Column(
                [
                    ft.Text("Presets", size=12, color=Theme.TEXT_MUTED, weight="w500"),
                    presets,
                ],
                spacing=10,
            ),
        )

        # --- Favoritos ---
        self.favs_col = ft.Column(spacing=8, controls=[])

        favs_section = ft.Column(
            [
                ft.Text("Favoritos", size=12, color=Theme.TEXT_MUTED, weight="w500"),
                ft.Container(
                    height=120,
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.1, Theme.TEXT_MAIN)),
                    bgcolor=ft.Colors.with_opacity(0.05, Theme.TEXT_MAIN),
                    content=ft.Column(
                        controls=[self.favs_col],
                        scroll="auto",
                        expand=True,
                        spacing=6,
                    ),
                ),
            ],
            spacing=8,
        )

        # --- Escenas ---
        self.scenes_col = ft.Column(spacing=8, controls=[])

        scenes_section = ft.Column(
            [
                ft.Text("Escenas", size=12, color=Theme.TEXT_MUTED, weight="w500"),
                ft.Container(
                    height=120,
                    border_radius=12,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.1, Theme.TEXT_MAIN)),
                    bgcolor=ft.Colors.with_opacity(0.05, Theme.TEXT_MAIN),
                    content=ft.Column(
                        controls=[self.scenes_col],
                        scroll="auto",
                        expand=True,
                        spacing=6,
                    ),
                ),
            ],
            spacing=8,
        )

        # --- Assemble everything ---
        self.controls = [
            ft.Container(height=12),
            header,
            self.dd_target,
            ft.Container(height=8),
            picker_and_preview,
            ft.Container(height=8),
            presets_card,
            ft.Container(height=8),
            favs_section,
            ft.Container(height=8),
            scenes_section,
            ft.Container(height=20),
        ]

    def did_mount(self):
        self._start_send_worker()
        self._refresh_targets()
        self._refresh_favorites()
        self._refresh_scenes()

    def _refresh_targets(self) -> None:
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
                pass
            label = f"{name} ({ip})" if name else ip
            opts.append(ft.dropdown.Option(ip, label))

        try:
            self.dd_target.options = opts
            self.dd_target.value = self._target_ip or ""
            self.dd_target.update()
        except Exception:
            pass

        self._update_caps_from_target()

    def _update_caps_from_target(self) -> None:
        ip = self._target_ip
        st = None
        if ip and hasattr(self.wiz, "get_bulb_state"):
            try:
                st = self.wiz.get_bulb_state(ip)
            except Exception:
                st = None

        if not isinstance(st, dict):
            self._caps = {"rgb": True, "white": True}
        else:
            self._caps = {
                "rgb": st.get("rgb") is not None,
                "white": st.get("temp") is not None,
            }

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

                while not self._send_stop.is_set():
                    with self._send_lock:
                        scheduled_at = float(self._send_scheduled_at)
                        delay_s = float(self._send_delay_s)
                    remaining = (scheduled_at + delay_s) - time.monotonic()
                    if remaining <= 0:
                        break
                    self._send_event.wait(timeout=min(0.10, max(0.01, remaining)))
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

    def _schedule_send(self, delay_s: float = 0.10) -> None:
        try:
            self._start_send_worker()
            with self._send_lock:
                self._send_delay_s = float(delay_s)
                self._send_scheduled_at = time.monotonic()
            self._send_event.set()
        except Exception:
            pass

    def _send_state_blocking(self, st: dict[str, object]) -> None:
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

        try:
            if all(k in st for k in ("r", "g", "b")):
                self.wiz.set_rgb(int(st["r"]), int(st["g"]), int(st["b"]), ip=self._target_ip, emit=False)
        except Exception:
            self.logger.exception("Error enviando RGB")

    def _on_picker_hue_end(self, e):
        try:
            self._picker_h = float(e.control.value)
        except Exception:
            return
        try:
            self.sv_image.src = self._render_sv_png_b64(self._picker_h)
            self.sv_image.update()
        except Exception:
            pass
        self._apply_picker_color(schedule=True)

    def _on_sv_pick(self, e):
        x = getattr(e, "local_x", None)
        y = getattr(e, "local_y", None)
        if x is None or y is None:
            return

        try:
            w = float(getattr(self.sv_surface, "width", 220) or 220)
            h = float(getattr(self.sv_surface, "height", 220) or 220)
            sx = max(0.0, min(1.0, float(x) / max(1.0, w)))
            vy = max(0.0, min(1.0, float(y) / max(1.0, h)))
            self._picker_s = sx
            self._picker_v = 1.0 - vy

            cx = max(0.0, min(w - 14.0, sx * w - 7.0))
            cy = max(0.0, min(h - 14.0, vy * h - 7.0))
            self.sv_cursor.left = cx
            self.sv_cursor.top = cy
            try:
                self.sv_cursor.update()
            except Exception:
                pass
        except Exception:
            return

        self._apply_picker_color(schedule=True)

    def _apply_picker_color(self, schedule: bool = True) -> None:
        try:
            r, g, b = colorsys.hsv_to_rgb(self._picker_h / 360.0, max(0.0, min(1.0, self._picker_s)), max(0.0, min(1.0, self._picker_v)))
        except Exception:
            return
        self._apply_rgb(int(r * 255), int(g * 255), int(b * 255))
        if schedule:
            self._schedule_send(0.08)

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

        self._set_preview(hex_c)
        self._pending_state = {
            "r": r,
            "g": g,
            "b": b,
            "dimming": 100,
            "state": True,
        }
        self._schedule_send(0.08)
        if self._on_bg_change:
            try:
                self._on_bg_change(hex_c)
            except Exception:
                pass

    def _set_preview(self, hex_color: str) -> None:
        try:
            now = time.monotonic()
            if (now - self._last_preview_ui_t) < 0.06:
                return
            self._last_preview_ui_t = now
            self.preview_box.bgcolor = hex_color
            self.preview_box.shadow.color = ft.Colors.with_opacity(0.5, hex_color)
            self.preview_box.update()
        except Exception:
            pass

    def _apply_hex_preset(self, hex_color: str) -> None:
        try:
            h = str(hex_color).lstrip("#")
            r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
            self._apply_rgb(r, g, b)
        except Exception:
            pass

    def _render_sv_png_b64(self, hue_deg: float, size: int = 260) -> str:
        """Renderiza SV picker como data URI base64."""
        hue_deg = float(hue_deg)
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
        b64 = base64.b64encode(data).decode("utf-8")
        uri = f"data:image/png;base64,{b64}"

        self._sv_cache[key] = uri
        self._sv_cache_order.append(key)
        if len(self._sv_cache_order) > 20:
            old = self._sv_cache_order.pop(0)
            if old in self._sv_cache:
                self._sv_cache.pop(old, None)

        return uri

    def _refresh_favorites(self) -> None:
        self.favs_col.controls.clear()
        for f in (self.fav_manager.get_favorites() or [])[:20]:
            v = f.get("value")
            if isinstance(v, dict) and all(k in v for k in ("r", "g", "b")):
                preview = "#{:02x}{:02x}{:02x}".format(int(v.get("r", 0)) & 255, int(v.get("g", 0)) & 255, int(v.get("b", 0)) & 255)
            elif isinstance(v, str):
                preview = v
            else:
                preview = Theme.TEXT_MUTED

            row = ft.Container(
                padding=12,
                border_radius=12,
                bgcolor=Theme.BG_CARD,
                border=ft.border.all(1, ft.Colors.with_opacity(0.08, Theme.TEXT_MAIN)),
                content=ft.Row(
                    [
                        ft.Container(width=16, height=16, border_radius=8, bgcolor=preview, border=ft.border.all(1, ft.Colors.with_opacity(0.3, Theme.TEXT_MAIN))),
                        ft.Text(f.get("name", "?"), expand=True, no_wrap=True, size=13),
                        ft.IconButton(ft.icons.PLAY_ARROW, icon_color=Theme.SUCCESS, icon_size=20, on_click=lambda _e, x=f: self._apply_fav(x)),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
            self.favs_col.controls.append(row)
        try:
            self.favs_col.update()
        except Exception:
            pass

    def _apply_fav(self, f) -> None:
        v = f.get("value")

        def _do():
            try:
                if isinstance(v, dict) and hasattr(self.wiz, "apply_piloting_state"):
                    self.wiz.apply_piloting_state(v, ip=self._target_ip)
                elif f.get("type") == "rgb" and isinstance(v, str):
                    h = str(v).lstrip("#")
                    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                    self.wiz.set_rgb(r, g, b, ip=self._target_ip)
            except Exception:
                pass

        try:
            if self.page:
                self.page.run_thread(_do)
            else:
                _do()
        except Exception:
            _do()

    def _refresh_scenes(self) -> None:
        self.scenes_col.controls.clear()
        for s in (STATIC_SCENES + DYNAMIC_SCENES)[:30]:
            card = ft.Container(
                height=56,
                bgcolor=Theme.BG_CARD,
                border_radius=12,
                border=ft.border.all(1, ft.Colors.with_opacity(0.08, s.get("color", Theme.TEXT_MUTED))),
                content=ft.Row(
                    [
                        ft.Container(
                            width=10,
                            height=10,
                            border_radius=5,
                            bgcolor=s.get("color", Theme.ACCENT),
                        ),
                        ft.Text(s.get("name", "?"), expand=True, no_wrap=True, size=13),
                        ft.IconButton(ft.icons.PLAY_ARROW, icon_color=Theme.SUCCESS, icon_size=20, on_click=lambda _e, x=s.get("id"): self._apply_scene(x)),
                    ],
                    spacing=10,
                ),
                on_click=lambda _e, x=s.get("id"): self._apply_scene(x),
                ink=True,
            )
            self.scenes_col.controls.append(card)
        try:
            self.scenes_col.update()
        except Exception:
            pass

    def _apply_scene(self, scene_id: int) -> None:
        def _do():
            try:
                self.wiz.set_scene(int(scene_id), ip=self._target_ip)
            except Exception:
                pass

        try:
            if self.page:
                self.page.run_thread(_do)
            else:
                _do()
        except Exception:
            _do()
