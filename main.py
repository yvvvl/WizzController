import atexit
import os
import sys
import time
import logging
import threading
import traceback
from typing import Callable

import flet as ft

from app_meta import APP_ID, APP_NAME, display_version

from core.light_controller import LightController
from ui.app import WizzApp
from ui.theme import Theme
from config.app_runtime_manager import AppRuntimeManager
from config.hotkeys_manager import HotkeysManager
from core.background.tray_service import TrayService, install_window_handlers
from core.single_instance import SingleInstanceGuard
from core.windows_window import restore_window
from core.logging_setup import configure_logging
from config.paths import assets_dir, config_dir, logs_dir

_APP_TITLE = APP_NAME
_INSTANCE_GUARD = SingleInstanceGuard(APP_ID)
_RUNTIME_LOCK = threading.RLock()
_RUNTIME_SHUTDOWN_CALLBACK: Callable[[], None] | None = None


configure_logging()


def main(page: ft.Page):
    wiz = None
    hotkeys = None
    try:
        page.title = _APP_TITLE
        page.bgcolor = Theme.BG
        page.padding = 0
        page.theme_mode = ft.ThemeMode.DARK
        page.theme = ft.Theme(color_scheme_seed=Theme.PRIMARY)

        page.window.width = 1080
        page.window.height = 720
        page.window.min_width = 720
        page.window.min_height = 540

        wiz = LightController()
        hotkeys = HotkeysManager(wiz)
        logging.info("[Hotkeys] %s", hotkeys.backend_status())

        shutdown_lock = threading.Lock()
        shutdown_done = False

        def shutdown_services():
            nonlocal shutdown_done
            with shutdown_lock:
                if shutdown_done:
                    return
                shutdown_done = True
            _safe(_INSTANCE_GUARD.stop_listener)
            _safe(hotkeys.stop)
            _safe(wiz.stop)

        app = WizzApp(page, wiz, hotkeys_manager=hotkeys)
        page.on_resize = app.handle_page_resize
        # PHASE32_RUNTIME_TRAY_SAFE
        runtime = AppRuntimeManager()
        tray = None
        tray_started = False
        if runtime.get('tray_enabled', True):
            try:
                tray = TrayService(page, wiz, runtime, hotkeys_manager=hotkeys, on_shutdown=shutdown_services)
                tray_started = tray.start()
                if tray_started:
                    logging.info('[Tray] Icono de bandeja iniciado. X => ocultar a bandeja. Salir real desde menú de bandeja.')  # PHASE33_TRAY_NOTE
                else:
                    logging.warning(f"[Tray] No disponible: {getattr(tray, 'last_error', 'sin detalle')}. La X cerrará normal.")
            except Exception as _tray_error:
                tray = None
                tray_started = False
                logging.warning(f'[Tray] no iniciado: {_tray_error}. La X cerrará normal.')
        install_window_handlers(page, tray if tray_started else None, runtime, on_shutdown=shutdown_services)

        def stop_this_runtime() -> None:
            shutdown_services()
            if tray is not None:
                _safe(tray.stop)

        _register_runtime_shutdown(stop_this_runtime)

        def activate_existing_instance() -> bool:
            if tray is not None and tray_started:
                return bool(tray.show_window())
            return _show_page_window(page)

        def takeover_stale_instance() -> None:
            """Entrega el control cuando Flet cerró pero el tray quedó vivo."""

            logging.warning(
                "[Instance] La sesión desktop no tiene una ventana restaurable; "
                "reiniciando la instancia activa."
            )
            _stop_runtime_services()
            _safe(_INSTANCE_GUARD.close)
            os._exit(0)

        _INSTANCE_GUARD.start_listener(
            activate_existing_instance,
            takeover_stale_instance,
        )
        try:
            page._wizz_runtime = runtime
            page._wizz_tray = tray if tray_started else None
            page._wizz_hotkeys = hotkeys
        except Exception:
            pass
        wiz.set_callback(lambda state: _safe(app.update_ui, state))

        page.add(app)
        page.update()
        # PHASE32_OPEN_MINIMIZED_SAFE
        try:
            if runtime.get('open_minimized', False) and tray is not None and tray_started:
                tray.hide_window()
        except Exception:
            pass

        wiz.start()
        logging.info("%s listo · %s", APP_NAME, display_version())

    except Exception:
        traceback.print_exc()
        _stop_runtime_services()
        if hotkeys is not None:
            _safe(hotkeys.stop)
        if wiz is not None:
            _safe(wiz.stop)


def _register_runtime_shutdown(callback: Callable[[], None]) -> None:
    global _RUNTIME_SHUTDOWN_CALLBACK
    with _RUNTIME_LOCK:
        _RUNTIME_SHUTDOWN_CALLBACK = callback


def _stop_runtime_services() -> None:
    global _RUNTIME_SHUTDOWN_CALLBACK
    with _RUNTIME_LOCK:
        callback = _RUNTIME_SHUTDOWN_CALLBACK
        _RUNTIME_SHUTDOWN_CALLBACK = None
    if callable(callback):
        _safe(callback)


def _finalize_process() -> None:
    _stop_runtime_services()
    _safe(_INSTANCE_GUARD.close)


def _show_page_window(page: ft.Page) -> bool:
    """Restaura una ventana sin crear coroutines desde el listener nativo."""

    native = restore_window(_APP_TITLE, process_id=os.getpid())
    updated = False
    try:
        page.window.visible = True
        page.window.skip_task_bar = False
        page.window.minimized = False
        page.window.focused = True
        page.update()
        updated = True
    except Exception:
        pass
    return bool(native.ok or updated)


def _acquire_or_activate_instance() -> bool:
    """Obtiene la instancia o restaura/reemplaza la que ya existe.

    La segunda ejecución intenta restaurar la ventana directamente con Win32.
    Si el proceso propietario sigue vivo pero ya no posee ninguna ventana Flet
    (tray zombie de modo dev), solicita un relevo y arranca de nuevo.
    """

    if _INSTANCE_GUARD.acquire():
        return True

    owner_pid = _INSTANCE_GUARD.owner_pid()
    _INSTANCE_GUARD.signal_existing()

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        restored = restore_window(_APP_TITLE, process_id=owner_pid)
        if restored.ok:
            logging.info("[Instance] Ventana existente restaurada; no se abre otra instancia.")
            return False
        if _INSTANCE_GUARD.acquire():
            logging.info("[Instance] La instancia anterior terminó durante la activación.")
            return True
        time.sleep(0.12)

    if os.name == "nt" and _INSTANCE_GUARD.request_takeover():
        logging.warning(
            "[Instance] Proceso activo sin ventana restaurable; solicitando reinicio seguro."
        )
        takeover_deadline = time.monotonic() + 5.0
        while time.monotonic() < takeover_deadline:
            if _INSTANCE_GUARD.acquire():
                logging.info("[Instance] Relevo completado; iniciando una sesión limpia.")
                return True
            time.sleep(0.12)

    _INSTANCE_GUARD.show_already_running_message()
    return False


def _safe(fn, *args):
    try:
        fn(*args)
    except Exception:
        pass


if __name__ == "__main__":
    logging.info("Iniciando %s · %s", APP_NAME, display_version())
    logging.info(
        "[Paths] config=%s · logs=%s · assets=%s",
        config_dir(),
        logs_dir(),
        assets_dir(),
    )
    if not _acquire_or_activate_instance():
        sys.exit(0)

    atexit.register(_finalize_process)
    try:
        ft.run(main, assets_dir=str(assets_dir()))
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        _finalize_process()
