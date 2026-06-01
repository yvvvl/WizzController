import sys
import logging
import traceback
import flet as ft

from core.light_controller import LightController
from ui.app import WizzApp
from ui.theme import Theme
from config.app_runtime_manager import AppRuntimeManager
from core.background.tray_service import TrayService, install_window_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def main(page: ft.Page):
    try:
        page.title = "WizZ Desktop"
        page.bgcolor = Theme.BG
        page.padding = 0
        page.theme_mode = ft.ThemeMode.DARK
        page.theme = ft.Theme(color_scheme_seed=Theme.PRIMARY)

        page.window.width = 1080
        page.window.height = 720
        page.window.min_width = 820
        page.window.min_height = 600

        wiz = LightController()
        app = WizzApp(page, wiz)
        # PHASE32_RUNTIME_TRAY_SAFE
        runtime = AppRuntimeManager()
        tray = None
        tray_started = False
        if runtime.get('tray_enabled', True):
            try:
                tray = TrayService(page, wiz, app, runtime)
                tray_started = tray.start()
                if tray_started:
                    logging.info('[Tray] Icono de bandeja iniciado. X => ocultar a bandeja. Salir real desde menú de bandeja.')  # PHASE33_TRAY_NOTE
                else:
                    logging.warning(f"[Tray] No disponible: {getattr(tray, 'last_error', 'sin detalle')}. La X cerrará normal.")
            except Exception as _tray_error:
                tray = None
                tray_started = False
                logging.warning(f'[Tray] no iniciado: {_tray_error}. La X cerrará normal.')
        install_window_handlers(page, tray if tray_started else None, runtime)
        try:
            page._wizz_runtime = runtime
            page._wizz_tray = tray if tray_started else None
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
        logging.info("WizZ listo.")

    except Exception:
        traceback.print_exc()


def _safe(fn, *args):
    try:
        fn(*args)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        ft.run(main)
    except KeyboardInterrupt:
        sys.exit()
