from __future__ import annotations

import threading
from typing import Any

import flet as ft

from core.voice.voice_service import VoiceService
from config.app_runtime_manager import AppRuntimeManager
from ui.theme import Theme, mounted, supdate


ICON_MIC = getattr(ft.Icons, "MIC_ROUNDED", ft.Icons.KEYBOARD_ROUNDED)
ICON_VOICE = getattr(ft.Icons, "SETTINGS_VOICE_ROUNDED", ICON_MIC)
ICON_INFO = getattr(ft.Icons, "INFO_OUTLINE_ROUNDED", ft.Icons.INFO_OUTLINE)


class VoicePanel(ft.Column):
    """Panel de voz Fase 30: UI compacta con avanzado oculto."""

    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=14, expand=True)
        self.wiz = wiz
        self.service = VoiceService(wiz)
        self.runtime = AppRuntimeManager()
        self._pending_result: dict[str, Any] | None = None
        self._actions: list[dict[str, Any]] = []
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        cfg = self.service.config()
        deps = self.service.dependency_status()
        self._advanced_visible = False
        self._diagnostics_visible = False

        # Estado global
        self.status_dot = ft.Container(width=9, height=9, border_radius=5, bgcolor=Theme.SUCCESS if deps.get("ok") else Theme.WARNING)
        self.status_text = ft.Text("Listo" if deps.get("ok") else "Faltan dependencias de voz", color=Theme.MUTED, size=12)
        self.busy_ring = ft.ProgressRing(width=18, height=18, stroke_width=2, color=Theme.PRIMARY, visible=False)

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Voz", style=Theme.H1),
                        ft.Text("Asistente local: activador + comando, bajo consumo y entrenamiento opcional", color=Theme.MUTED, size=13),
                    ],
                    spacing=2,
                ),
                ft.Container(expand=True),
                self.busy_ring,
                ft.Container(
                    content=ft.Row([self.status_dot, self.status_text], spacing=8),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=8),
                    bgcolor=Theme.CARD,
                    border_radius=20,
                    border=ft.Border.all(1, Theme.STROKE),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Controles principales visibles. Esto es lo normal que el usuario sí debería tocar.
        self.setup_preset_dropdown = ft.Dropdown(
            label="Preset",
            value=str(cfg.get("voice_setup_preset", "voicemeeter")),
            width=230,
            options=[
                ft.DropdownOption(key="voicemeeter", text="Voicemeeter recomendado"),
                ft.DropdownOption(key="very_gated", text="Gate fuerte"),
                ft.DropdownOption(key="normal", text="Mic normal"),
                ft.DropdownOption(key="low", text="Bajo consumo"),
                ft.DropdownOption(key="precision", text="Precisión alta"),
            ],
            on_select=self._apply_setup_preset,
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
        self.audio_profile_dropdown = ft.Dropdown(
            label="Micrófono",
            value=str(cfg.get("audio_input_profile", "flow_gated")),
            width=230,
            options=[
                ft.DropdownOption(key="flow_gated", text="Voicemeeter fluido"),
                ft.DropdownOption(key="normal", text="Normal"),
                ft.DropdownOption(key="gated", text="Voicemeeter / gate"),
                ft.DropdownOption(key="very_gated", text="Gate fuerte"),
            ],
            on_select=self._save_config,
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
        self.wake_words = ft.TextField(
            label="Activadores",
            value=", ".join(cfg.get("wake_words", ["pc", "pese", "wizz", "wiz"])),
            hint_text="pc, pese, wizz, wiz",
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            dense=True,
            width=300,
            on_submit=self._save_config,
        )
        self.continuous_dot = ft.Container(width=9, height=9, border_radius=5, bgcolor=Theme.FAINT)
        self.continuous_text = ft.Text("Escucha continua detenida", color=Theme.MUTED, size=12)
        self.btn_continuous = ft.ElevatedButton("Activar escucha continua", icon=ICON_VOICE, bgcolor=Theme.CARD_HI, color=Theme.TEXT, on_click=self._toggle_continuous)
        self.btn_listen = ft.ElevatedButton("Escuchar ahora", icon=ICON_MIC, bgcolor=Theme.PRIMARY, color="white", on_click=self._listen_once)
        self.btn_load = ft.OutlinedButton("Cargar modelo", icon=ft.Icons.DOWNLOAD_ROUNDED, on_click=self._load_model, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)))
        self.test_text = ft.TextField(
            label="Probar texto",
            hint_text="pc prende la luz al 50",
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            expand=True,
            dense=True,
            on_submit=self._test_text,
        )
        self.btn_test = ft.OutlinedButton("Probar", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=self._test_text, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)))

        # Inicio / segundo plano. Visible pero compacto: solo lo que se toca una vez.
        self.voice_start_mode = ft.Dropdown(
            label="Voz al iniciar",
            value=str(self.runtime.get("voice_start_mode", "manual")),
            width=230,
            options=[
                ft.DropdownOption(key="manual", text="Manual"),
                ft.DropdownOption(key="always", text="Activar siempre"),
                ft.DropdownOption(key="remember", text="Recordar último estado"),
            ],
            on_select=self._save_runtime_config,
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
        self.startup_switch = ft.Switch(
            label="Iniciar con Windows",
            value=bool(self.runtime.get("startup_with_windows", False)),
            on_change=self._save_runtime_config,
        )
        self.tray_switch = ft.Switch(
            label="Bandeja al cerrar",
            value=bool(self.runtime.get("minimize_to_tray", True)),
            on_change=self._save_runtime_config,
        )
        self.open_minimized_switch = ft.Switch(
            label="Abrir minimizado",
            value=bool(self.runtime.get("open_minimized", False)),
            on_change=self._save_runtime_config,
        )

        startup_card = self._card(
            ft.Column(
                [
                    ft.Text("INICIO Y SEGUNDO PLANO", style=Theme.LABEL),
                    ft.Row([self.voice_start_mode, self.startup_switch, self.tray_switch, self.open_minimized_switch], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text("Recomendado: voz manual. Si quieres asistente diario, usa ‘Recordar último estado’. La bandeja requiere pystray/Pillow.", color=Theme.FAINT, size=11),
                ],
                spacing=9,
            )
        )

        main_card = self._card(
            ft.Column(
                [
                    ft.Text("CONTROL DE VOZ", style=Theme.LABEL),
                    ft.Row([self.continuous_dot, self.continuous_text], spacing=8),
                    ft.Row([self.btn_continuous, self.btn_listen, self.btn_load], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([self.setup_preset_dropdown, self.audio_profile_dropdown, self.wake_words], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([self.test_text, self.btn_test], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text("Punto dulce actual: activador al inicio, corte de silencio y filtro de ruido activos. Ej: pc apaga la luz.", color=Theme.FAINT, size=11),
                ],
                spacing=10,
            )
        )

        # Controles avanzados: existen para compatibilidad, pero quedan ocultos por defecto.
        self.model_dropdown = ft.Dropdown(
            label="Modelo PTT",
            value=str(cfg.get("model_size", "base")),
            width=165,
            options=[ft.DropdownOption(key="tiny", text="tiny"), ft.DropdownOption(key="base", text="base"), ft.DropdownOption(key="small", text="small")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.seconds_dropdown = ft.Dropdown(
            label="Duración máx.",
            value=str(float(cfg.get("record_seconds", 4.0))),
            width=145,
            options=[ft.DropdownOption(key="2.5", text="2.5 s"), ft.DropdownOption(key="4.0", text="4 s"), ft.DropdownOption(key="6.0", text="6 s"), ft.DropdownOption(key="8.0", text="8 s")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.silence_dropdown = ft.Dropdown(
            label="Corte silencio",
            value=str(int(cfg.get("end_silence_ms", 650))),
            width=165,
            options=[ft.DropdownOption(key="450", text="0.45 s"), ft.DropdownOption(key="650", text="0.65 s"), ft.DropdownOption(key="900", text="0.90 s"), ft.DropdownOption(key="1200", text="1.2 s")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.sensitivity_dropdown = ft.Dropdown(
            label="Sensibilidad",
            value=str(float(cfg.get("energy_threshold", 0.014))),
            width=150,
            options=[ft.DropdownOption(key="0.008", text="alta"), ft.DropdownOption(key="0.014", text="normal"), ft.DropdownOption(key="0.022", text="baja")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.language_dropdown = ft.Dropdown(
            label="Idioma",
            value=str(cfg.get("language_mode", "es_mixed")),
            width=220,
            options=[ft.DropdownOption(key="es_mixed", text="Español + inglés"), ft.DropdownOption(key="es", text="Solo español"), ft.DropdownOption(key="auto_ptt", text="Auto solo PTT")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.profile_dropdown = ft.Dropdown(
            label="Perfil fondo",
            value=str(cfg.get("performance_profile", "balanced")),
            width=190,
            options=[ft.DropdownOption(key="eco", text="Eficiente"), ft.DropdownOption(key="balanced", text="Equilibrado"), ft.DropdownOption(key="accuracy", text="Preciso")],
            on_select=self._apply_profile,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.strategy_dropdown = ft.Dropdown(
            label="Estrategia",
            value=str(cfg.get("continuous_strategy", "wake_then_command")),
            width=190,
            options=[ft.DropdownOption(key="wake_then_command", text="Activador + comando"), ft.DropdownOption(key="full_phrase", text="Frase completa")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.cont_model_dropdown = ft.Dropdown(
            label="Modelo fondo",
            value=str(cfg.get("continuous_model_size", "base")),
            width=135,
            options=[ft.DropdownOption(key="tiny", text="tiny"), ft.DropdownOption(key="base", text="base")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.thread_dropdown = ft.Dropdown(
            label="CPU fondo",
            value=str(int(cfg.get("continuous_cpu_threads", 1))),
            width=135,
            options=[ft.DropdownOption(key="1", text="1 hilo"), ft.DropdownOption(key="2", text="2 hilos")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.cont_timeout = ft.Dropdown(
            label="Espera inicio",
            value=str(float(cfg.get("continuous_start_timeout", 1.7))),
            width=130,
            options=[ft.DropdownOption(key="1.2", text="1.2 s"), ft.DropdownOption(key="1.7", text="1.7 s"), ft.DropdownOption(key="2.2", text="2.2 s")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.smart_switch = ft.Switch(label="Corte al silencio activo", value=True, disabled=True)
        self.vad_switch = ft.Switch(label="Filtro de ruido activo", value=True, disabled=True)
        self.btn_unload = ft.OutlinedButton("Liberar modelos", icon=ft.Icons.MEMORY_ROUNDED, on_click=self._unload_models, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)))
        self.wake_chip = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.LOCK_ROUNDED, size=15, color=Theme.SUCCESS), ft.Text("Activador al inicio", color=Theme.TEXT, size=12)], spacing=7),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8), border_radius=18,
            bgcolor=ft.Colors.with_opacity(0.10, Theme.SUCCESS), border=ft.Border.all(1, ft.Colors.with_opacity(0.35, Theme.SUCCESS)),
        )

        # Seguridad multi-voz avanzada
        self.speaker_mode_dropdown = ft.Dropdown(
            label="Seguridad de voz",
            value=str(cfg.get("speaker_security_mode", "open")),
            width=220,
            options=[ft.DropdownOption(key="open", text="Libre"), ft.DropdownOption(key="cautious", text="Solo si parece mi voz"), ft.DropdownOption(key="owner", text="Solo mi voz")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.speaker_threshold_dropdown = ft.Dropdown(
            label="Coincidencia",
            value=str(float(cfg.get("speaker_min_similarity", 0.58))),
            width=160,
            options=[ft.DropdownOption(key="0.50", text="flexible"), ft.DropdownOption(key="0.58", text="normal"), ft.DropdownOption(key="0.66", text="estricta")],
            on_select=self._save_config,
            color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE,
        )
        self.speaker_status_text = ft.Text("", color=Theme.MUTED, size=12)
        self.btn_enroll_voice = ft.ElevatedButton("Grabar muestra", icon=ICON_MIC, bgcolor=Theme.PRIMARY, color="white", on_click=self._enroll_voice_sample)
        self.btn_clear_voice = ft.OutlinedButton("Borrar perfil", icon=ft.Icons.DELETE_OUTLINE_ROUNDED, on_click=self._clear_voice_profile, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)))
        self._refresh_speaker_status()

        # Entrenamiento manual avanzado
        self._actions = self.service.available_actions()
        self.category_dropdown = ft.Dropdown(label="Categoría", width=220, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE, on_select=self._refresh_action_dropdown)
        self.action_dropdown = ft.Dropdown(label="Acción", width=340, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        self.train_phrase = ft.TextField(label="Frase personalizada", hint_text="Ej: modo estudio", color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE, width=360, dense=True)
        self.btn_train = ft.ElevatedButton("Guardar frase", icon=ft.Icons.SAVE_ROUNDED, bgcolor=Theme.PRIMARY, color="white", on_click=self._save_training)
        self.training_list = ft.Column(spacing=8)

        self.advanced_container = ft.Container(
            visible=False,
            content=ft.Column(
                [
                    ft.Text("AJUSTES AVANZADOS", style=Theme.LABEL),
                    ft.Row([self.model_dropdown, self.language_dropdown, self.btn_unload], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([self.seconds_dropdown, self.silence_dropdown, self.sensitivity_dropdown], spacing=12),
                    ft.Row([self.profile_dropdown, self.strategy_dropdown, self.cont_model_dropdown, self.thread_dropdown, self.cont_timeout], spacing=12),
                    ft.Row([self.smart_switch, self.vad_switch, self.wake_chip], spacing=14),
                    ft.Text("SEGURIDAD MULTI-VOZ", style=Theme.LABEL),
                    ft.Row([self.speaker_mode_dropdown, self.speaker_threshold_dropdown, self.btn_enroll_voice, self.btn_clear_voice], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    self.speaker_status_text,
                    ft.Text("ENTRENAMIENTO MANUAL", style=Theme.LABEL),
                    ft.Row([self.category_dropdown, self.action_dropdown], spacing=12),
                    ft.Row([self.train_phrase, self.btn_train], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    self.training_list,
                ],
                spacing=10,
            ),
            padding=18,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )
        self.btn_advanced = ft.OutlinedButton("Mostrar ajustes avanzados", icon=ft.Icons.TUNE_ROUNDED, on_click=self._toggle_advanced, style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)))

        # Resultados compactos
        self.transcript = ft.Text("—", color=Theme.TEXT, size=14, selectable=True, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS)
        self.intent = ft.Text("Sin comando ejecutado", color=Theme.MUTED, size=12)
        self.diagnostic_col = ft.Column(spacing=5)
        self.diagnostic_box = ft.Container(visible=False, content=ft.Column([ft.Text("DIAGNÓSTICO", style=Theme.LABEL), self.diagnostic_col], spacing=8))
        self.btn_diagnostics = ft.TextButton("Ver diagnóstico", icon=ICON_INFO, on_click=self._toggle_diagnostics)
        self.log_col = ft.Column(spacing=8)
        result_card = self._card(
            ft.Column(
                [
                    ft.Row([ft.Text("ÚLTIMO RESULTADO", style=Theme.LABEL), ft.Container(expand=True), self.btn_diagnostics], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(content=self.transcript, padding=12, border_radius=Theme.R_SM, bgcolor=Theme.BG, border=ft.Border.all(1, Theme.STROKE)),
                    self.intent,
                    self.diagnostic_box,
                    ft.Text("HISTORIAL", style=Theme.LABEL),
                    self.log_col,
                ],
                spacing=9,
            )
        )

        self.controls = [header, main_card, startup_card, result_card, self.btn_advanced, self.advanced_container]
        self._refresh_categories()
        self._refresh_training_list()
        self._sync_continuous_ui()
    def _card(self, content):
        return ft.Container(
            content=content,
            padding=18,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
        )


    def did_mount(self):
        # Autoarranque controlado. No escucha sola salvo que el usuario lo pida.
        if not self.runtime.should_start_voice():
            return

        def worker():
            try:
                import time
                time.sleep(0.9)
                if not self.service.is_continuous_running():
                    res = self.service.start_continuous(callback=self._on_continuous_event)
                    self._pending_result = {
                        "text": "—",
                        "message": res.get("message", "Escucha continua iniciada automáticamente"),
                        "ok": bool(res.get("ok")),
                        "event": "continuous_started",
                    }
                    self.runtime.remember_voice_active(bool(res.get("ok")))
                try:
                    if mounted(self):
                        self.page.run_task(self._finish_async)
                except Exception:
                    pass
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _save_runtime_config(self, e=None):
        mode = self.voice_start_mode.value or "manual"
        startup = bool(self.startup_switch.value)
        tray_close = bool(self.tray_switch.value)
        minimized = bool(self.open_minimized_switch.value)
        self.runtime.update(
            voice_start_mode=mode,
            minimize_to_tray=tray_close,
            open_minimized=minimized,
            tray_enabled=True,
        )
        ok, msg = self.runtime.set_startup_with_windows(startup)
        self._set_status(msg if msg else "Configuración de inicio guardada", ok=ok or not startup)


    def _toggle_advanced(self, e=None):
        self._advanced_visible = not bool(getattr(self, "_advanced_visible", False))
        self.advanced_container.visible = self._advanced_visible
        self.btn_advanced.text = "Ocultar ajustes avanzados" if self._advanced_visible else "Mostrar ajustes avanzados"
        try:
            self.btn_advanced.icon = ft.Icons.EXPAND_LESS_ROUNDED if self._advanced_visible else ft.Icons.TUNE_ROUNDED
        except Exception:
            pass
        supdate(self.advanced_container)
        supdate(self.btn_advanced)

    def _toggle_diagnostics(self, e=None):
        self._diagnostics_visible = not bool(getattr(self, "_diagnostics_visible", False))
        self.diagnostic_box.visible = self._diagnostics_visible
        self.btn_diagnostics.text = "Ocultar diagnóstico" if self._diagnostics_visible else "Ver diagnóstico"
        supdate(self.diagnostic_box)
        supdate(self.btn_diagnostics)

    # ------------------------------------------------------------------ #
    # Configuración
    # ------------------------------------------------------------------ #
    def _save_config(self, e=None):
        try:
            words = [w.strip() for w in str(self.wake_words.value or "").split(",") if w.strip()] if hasattr(self, "wake_words") else None
            payload = {
                "model_size": self.model_dropdown.value or "base",
                "record_seconds": float(self.seconds_dropdown.value or 4.0),
                "vad_filter": bool(self.vad_switch.value),
                "smart_recording": bool(self.smart_switch.value),
                "end_silence_ms": int(self.silence_dropdown.value or 650),
                "energy_threshold": float(self.sensitivity_dropdown.value or 0.014),
                "language_mode": self.language_dropdown.value or "es_mixed",
                "language": "es",
                "audio_input_profile": self.audio_profile_dropdown.value or "flow_gated",
            }
            if hasattr(self, "profile_dropdown"):
                payload["performance_profile"] = self.profile_dropdown.value or "eco"
            if hasattr(self, "strategy_dropdown"):
                payload["continuous_strategy"] = self.strategy_dropdown.value or "wake_then_command"
            if hasattr(self, "cont_model_dropdown"):
                payload["continuous_model_size"] = self.cont_model_dropdown.value or "tiny"
            if hasattr(self, "thread_dropdown"):
                payload["continuous_cpu_threads"] = int(self.thread_dropdown.value or 1)
            payload["continuous_require_wake_word"] = True
            if words is not None:
                cleaned = []
                for word in words:
                    lw = str(word).strip().lower()
                    if lw and len(lw.replace(" ", "")) >= 2 and lw not in cleaned:
                        cleaned.append(lw)
                # Se permite pc/pese. La seguridad está en que debe ir al INICIO.
                payload["wake_words"] = cleaned or ["wizz", "wiz"]
                payload["continuous_wake_position"] = "prefix"
                payload["continuous_require_command_after_wake"] = True
                self.wake_words.value = ", ".join(payload["wake_words"])
            if hasattr(self, "cont_timeout"):
                payload["continuous_start_timeout"] = float(self.cont_timeout.value or 1.7)
            if hasattr(self, "speaker_mode_dropdown"):
                payload["speaker_security_mode"] = self.speaker_mode_dropdown.value or "open"
            if hasattr(self, "speaker_threshold_dropdown"):
                payload["speaker_min_similarity"] = float(self.speaker_threshold_dropdown.value or 0.58)
            self.service.save_config(**payload)
            self._set_status("Configuración guardada", ok=True)
        except Exception as exc:
            self._set_status(f"Error config: {exc}", ok=False)

    def _apply_profile(self, e=None):
        profile = self.profile_dropdown.value or "eco"
        payload = self.service.apply_performance_profile(profile)
        self.strategy_dropdown.value = str(payload.get("continuous_strategy", "wake_then_command"))
        self.cont_model_dropdown.value = str(payload.get("continuous_model_size", "tiny"))
        self.thread_dropdown.value = str(payload.get("continuous_cpu_threads", 1))
        self.cont_timeout.value = str(float(payload.get("continuous_start_timeout", 1.7)))
        self.sensitivity_dropdown.value = str(float(payload.get("energy_threshold", 0.014)))
        self.language_dropdown.value = str(payload.get("language_mode", "es_mixed"))
        if hasattr(self, "audio_profile_dropdown"):
            self.audio_profile_dropdown.value = str(self.service.config().get("audio_input_profile", "flow_gated"))
        self.wake_words.value = ", ".join(payload.get("wake_words", ["wizz", "wiz"])) or "wizz, wiz"
        self._set_status(f"Perfil aplicado: {profile}", ok=True)
        supdate(self)

    def _apply_setup_preset(self, e=None):
        preset = self.setup_preset_dropdown.value or "voicemeeter"
        try:
            payload = self.service.apply_setup_preset(preset)
            # Reflejar valores aplicados en los controles visibles.
            self.profile_dropdown.value = str(payload.get("performance_profile", self.profile_dropdown.value or "balanced"))
            self.strategy_dropdown.value = str(payload.get("continuous_strategy", "wake_then_command"))
            self.cont_model_dropdown.value = str(payload.get("continuous_model_size", "base"))
            self.thread_dropdown.value = str(int(payload.get("continuous_cpu_threads", 1)))
            self.audio_profile_dropdown.value = str(payload.get("audio_input_profile", self.audio_profile_dropdown.value or "flow_gated"))
            self.sensitivity_dropdown.value = str(float(payload.get("energy_threshold", self.sensitivity_dropdown.value or 0.010)))
            self.silence_dropdown.value = str(int(payload.get("end_silence_ms", self.silence_dropdown.value or 900)))
            self.cont_timeout.value = str(float(payload.get("continuous_start_timeout", self.cont_timeout.value or 1.45)))
            self.wake_words.value = ", ".join(payload.get("wake_words", self.service.config().get("wake_words", ["pc", "pese", "wizz", "wiz"])))
            self._set_status(f"Preset aplicado: {preset}", ok=True)
            supdate(self)
        except Exception as exc:
            self._set_status(f"Error aplicando preset: {exc}", ok=False)

    def _unload_models(self, e=None):
        res = self.service.unload_models()
        self._set_status(res.get("message", "Modelos liberados"), ok=True)

    def _set_busy(self, busy: bool):
        self.busy_ring.visible = busy
        self.btn_listen.disabled = busy
        self.btn_load.disabled = busy
        self.btn_test.disabled = busy
        supdate(self)

    def _set_status(self, text: str, ok: bool = True):
        self.status_text.value = text
        self.status_dot.bgcolor = Theme.SUCCESS if ok else Theme.ERROR
        supdate(self.status_text)
        supdate(self.status_dot)

    def _refresh_speaker_status(self):
        if not hasattr(self, "speaker_status_text"):
            return
        st = self.service.speaker_status()
        count = int(st.get("sample_count") or 0)
        if st.get("trained"):
            txt = f"Perfil vocal entrenado: {count} muestra{'s' if count != 1 else ''}."
            col = Theme.SUCCESS
        else:
            txt = "Sin perfil vocal. En modo Libre no verifica voz; en Solo mi voz debes entrenar primero."
            col = Theme.MUTED
        self.speaker_status_text.value = txt
        self.speaker_status_text.color = col
        supdate(self.speaker_status_text)

    def _enroll_voice_sample(self, e=None):
        self._save_config()
        self._set_busy(True)
        self._set_status("Grabando muestra de voz…", ok=True)
        if hasattr(self, "speaker_status_text"):
            self.speaker_status_text.value = "Habla ahora: pc prende la luz al cincuenta"
            supdate(self.speaker_status_text)

        def worker():
            try:
                self._pending_result = self.service.enroll_speaker_sample()
            except Exception as exc:
                self._pending_result = {"ok": False, "message": f"Error entrenando voz: {exc}", "transcript": "perfil vocal"}
            self._schedule_finish()

        threading.Thread(target=worker, daemon=True).start()

    def _clear_voice_profile(self, e=None):
        st = self.service.clear_speaker_profile()
        self._refresh_speaker_status()
        self._pending_result = {"ok": True, "message": "Perfil vocal borrado", "transcript": "perfil vocal", **st}
        self._finish_sync()

    # ------------------------------------------------------------------ #
    # Push-to-talk
    # ------------------------------------------------------------------ #
    def _load_model(self, e=None):
        self._save_config()
        self._set_busy(True)
        self._set_status("Cargando modelo PTT…", ok=True)

        def worker():
            try:
                self._pending_result = self.service.load_model(continuous=False)
            except Exception as exc:
                self._pending_result = {"ok": False, "message": f"Error cargando modelo: {exc}"}
            self._schedule_finish()

        threading.Thread(target=worker, daemon=True).start()

    def _listen_once(self, e=None):
        self._save_config()
        self._set_busy(True)
        self._set_status("Escuchando…", ok=True)
        self.transcript.value = "Grabando audio…"
        self.intent.value = "Habla claro y corto."
        supdate(self.transcript)
        supdate(self.intent)

        def worker():
            try:
                self._pending_result = self.service.listen_once()
            except Exception as exc:
                self._pending_result = {"ok": False, "message": f"Error voz: {exc}", "transcript": ""}
            self._schedule_finish()

        threading.Thread(target=worker, daemon=True).start()

    def _test_text(self, e=None):
        text = (self.test_text.value or "").strip()
        if not text:
            self._set_status("Escribe un comando de prueba", ok=False)
            return
        self._pending_result = self.service.execute_text(text, source="manual")
        self._finish_sync()

    # ------------------------------------------------------------------ #
    # Escucha continua
    # ------------------------------------------------------------------ #
    def _sync_continuous_ui(self):
        running = self.service.is_continuous_running()
        self.continuous_dot.bgcolor = Theme.SUCCESS if running else Theme.FAINT
        self.continuous_text.value = "Escucha continua activa" if running else "Escucha continua detenida"
        self.continuous_text.color = Theme.SUCCESS if running else Theme.MUTED
        self.btn_continuous.text = "Detener escucha continua" if running else "Activar escucha continua"
        self.btn_continuous.bgcolor = Theme.ERROR if running else Theme.CARD_HI
        self.btn_continuous.color = "white" if running else Theme.TEXT
        supdate(self.continuous_dot)
        supdate(self.continuous_text)
        supdate(self.btn_continuous)

    def _toggle_continuous(self, e=None):
        self._save_config()
        if self.service.is_continuous_running():
            res = self.service.stop_continuous()
            self.runtime.remember_voice_active(False)
            self._set_status(res.get("message", "Detenido"), ok=True)
            self._sync_continuous_ui()
            return
        res = self.service.start_continuous(callback=self._on_continuous_event)
        if res.get("ok"):
            self.runtime.remember_voice_active(True)
        self._set_status(res.get("message", "Escucha continua"), ok=bool(res.get("ok")))
        self._sync_continuous_ui()

    def _on_continuous_event(self, result: dict[str, Any]):
        if result.get("event") == "idle":
            return
        self._pending_result = result
        try:
            if mounted(self):
                self.page.run_task(self._finish_async)
                return
        except Exception:
            pass
        self._finish_sync()

    # ------------------------------------------------------------------ #
    # Resultado / historial
    # ------------------------------------------------------------------ #
    def _schedule_finish(self):
        try:
            if mounted(self):
                self.page.run_task(self._finish_async)
                return
        except Exception:
            pass
        self._finish_sync()

    async def _finish_async(self):
        self._finish_sync()

    def _finish_sync(self):
        result = self._pending_result or {"ok": False, "message": "Sin resultado"}
        self._set_busy(False)
        self._render_result(result)
        self._sync_continuous_ui()
        self._refresh_speaker_status()

    def _render_result(self, result: dict[str, Any]):
        ok = bool(result.get("ok"))
        transcript = result.get("transcript") or result.get("text") or "—"
        message = result.get("message") or "Sin mensaje"
        conf = result.get("confidence")
        event = result.get("event")
        self.transcript.value = (str(transcript)[:420] + "…") if len(str(transcript)) > 420 else str(transcript)
        extra = []
        if isinstance(conf, float) and conf > 0:
            extra.append(f"confianza {conf:.2f}")
        if result.get("capture_seconds") is not None:
            extra.append(f"audio {result.get('capture_seconds')}s")
        if result.get("auto_stopped"):
            extra.append("corte por silencio")
        if result.get("rms_peak") is not None:
            extra.append(f"nivel {result.get('rms_peak')}")
        if result.get("elapsed") is not None:
            extra.append(f"total {result.get('elapsed')}s")
        if result.get("profile"):
            extra.append(f"perfil {result.get('profile')}")
        if result.get("speaker_similarity") is not None:
            extra.append(f"voz {result.get('speaker_similarity')}")
        if result.get("speaker_mode") and result.get("speaker_mode") != "open":
            extra.append(f"seguridad {result.get('speaker_mode')}")
        self.intent.value = f"{message}" + (" · " + " · ".join(extra) if extra else "")
        self._render_diagnostics(result)
        if event == "continuous_started":
            self._set_status("Escucha continua activa", ok=True)
        elif event == "continuous_stopped":
            self._set_status("Escucha continua detenida", ok=True)
        elif event == "transcribing":
            self._set_status("Verificando activador…", ok=True)
        elif event == "wake_ignored":
            self._set_status("Ignorado", ok=False)
        else:
            self._set_status("Ejecutado" if ok else "No ejecutado", ok=ok)
        if event not in ("continuous_started", "continuous_stopped", "transcribing", "wake_ignored"):
            self._push_log(transcript, self.intent.value, ok)
        supdate(self.transcript)
        supdate(self.intent)

    def _render_diagnostics(self, result: dict[str, Any]):
        if not hasattr(self, "diagnostic_col"):
            return
        self.diagnostic_col.controls.clear()
        try:
            lines = self.service.diagnostic_lines(result)
        except Exception as exc:
            lines = [f"No pude generar diagnóstico: {exc}"]
        for line in lines[:6]:
            self.diagnostic_col.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ICON_INFO, size=14, color=Theme.MUTED),
                            ft.Text(str(line), color=Theme.MUTED, size=11, expand=True),
                        ],
                        spacing=7,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    border_radius=Theme.R_SM,
                    bgcolor=ft.Colors.with_opacity(0.35, Theme.BG),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.55, Theme.STROKE)),
                )
            )
        supdate(self.diagnostic_col)

    def _push_log(self, transcript: str, message: str, ok: bool):
        item = ft.Container(
            content=ft.Column(
                [
                    ft.Text(str(transcript or "—"), color=Theme.TEXT, size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(message, color=Theme.SUCCESS if ok else Theme.ERROR, size=11, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ],
                spacing=2,
            ),
            padding=10,
            border_radius=Theme.R_SM,
            bgcolor=Theme.BG,
            border=ft.Border.all(1, Theme.STROKE),
        )
        self.log_col.controls.insert(0, item)
        del self.log_col.controls[6:]
        supdate(self.log_col)

    # ------------------------------------------------------------------ #
    # Entrenamiento
    # ------------------------------------------------------------------ #
    def _refresh_categories(self):
        self._actions = self.service.available_actions()
        categories = []
        for action in self._actions:
            cat = str(action.get("category") or "General")
            if cat not in categories:
                categories.append(cat)
        self.category_dropdown.options = [ft.DropdownOption(key=c, text=c) for c in categories]
        if categories and not self.category_dropdown.value:
            self.category_dropdown.value = categories[0]
        self._refresh_action_dropdown()

    def _refresh_action_dropdown(self, e=None):
        cat = self.category_dropdown.value
        actions = [a for a in self._actions if a.get("category") == cat]
        self.action_dropdown.options = [ft.DropdownOption(key=str(a.get("id")), text=str(a.get("name"))) for a in actions]
        self.action_dropdown.value = str(actions[0].get("id")) if actions else None
        supdate(self.action_dropdown)

    def _save_training(self, e=None):
        phrase = (self.train_phrase.value or "").strip()
        action_id = self.action_dropdown.value
        if not phrase or not action_id:
            self._set_status("Falta frase o acción", ok=False)
            return
        try:
            self.service.train_phrase(phrase, action_id)
            self.train_phrase.value = ""
            self._set_status("Frase guardada", ok=True)
            self._refresh_training_list()
            supdate(self.train_phrase)
        except Exception as exc:
            self._set_status(f"Error guardando frase: {exc}", ok=False)

    def _refresh_training_list(self):
        self.training_list.controls.clear()
        entries = self.service.training_manager.get_entries()
        if not entries:
            self.training_list.controls.append(ft.Text("Aún no hay frases entrenadas.", color=Theme.MUTED, size=12))
        else:
            for item in entries[-8:][::-1]:
                action = item.get("action") or {}
                self.training_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(str(item.get("phrase")), color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600),
                                        ft.Text(str(action.get("name") or action.get("id") or "Acción"), color=Theme.MUTED, size=11),
                                    ],
                                    spacing=2,
                                ),
                                ft.Container(expand=True),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, icon_size=18, on_click=lambda e, uid=item.get("id"): self._delete_training(uid)),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=10,
                        border_radius=Theme.R_SM,
                        bgcolor=Theme.BG,
                        border=ft.Border.all(1, Theme.STROKE),
                    )
                )
        supdate(self.training_list)

    def _delete_training(self, uid: str):
        self.service.training_manager.remove_entry(uid)
        self.service.parser = self.service.parser.__class__(self.wiz)
        self._refresh_training_list()
        self._set_status("Frase eliminada", ok=True)

    def sync_state(self, state: dict):
        if not mounted(self):
            return
        old_cat = self.category_dropdown.value
        old_action = self.action_dropdown.value
        self._actions = self.service.available_actions()
        cats = []
        for action in self._actions:
            cat = str(action.get("category") or "General")
            if cat not in cats:
                cats.append(cat)
        self.category_dropdown.options = [ft.DropdownOption(key=c, text=c) for c in cats]
        if old_cat in cats:
            self.category_dropdown.value = old_cat
        elif cats:
            self.category_dropdown.value = cats[0]
        self._refresh_action_dropdown()
        if old_action and any(str(a.get("id")) == old_action for a in self._actions):
            self.action_dropdown.value = old_action
        self._sync_continuous_ui()
        supdate(self)
