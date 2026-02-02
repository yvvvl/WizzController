import sys
import logging
import flet as ft
import threading

# Compatibilidad Flet: en versiones nuevas los iconos están en `ft.Icons.*`
# pero el proyecto usa `ft.icons.*` en muchos sitios.
from ui.flet_compat import patch_flet

patch_flet(ft)

try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover
    pystray = None
    Image = None
    ImageDraw = None

from config.config_manager import ConfigManager
from core.logging_setup import setup_logging

# Controladores
from core.light_controller import LightController
from ui.wizz_app import WizzApp

setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

def main(page: ft.Page):
    cfg = ConfigManager()

    perf_cfg = None
    tray_cfg = None
    try:
        perf_cfg = cfg.get_performance()
        tray_cfg = cfg.get_tray()
    except Exception:
        perf_cfg = cfg.get("performance", {})
        tray_cfg = cfg.get("tray", {})

    # --- 1. CONFIGURACION DE VENTANA ---
    page.title = "WizZ Desktop AI"
    page.bgcolor = "#0f172a"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK

    # Tamaño inicial (restaurado desde config si existe)
    geo = cfg.get_window_geometry()
    page.window.width = int(geo.get("width", 1100))
    page.window.height = int(geo.get("height", 700))
    top = int(geo.get("top", -1))
    left = int(geo.get("left", -1))
    if top >= 0:
        page.window.top = top
    if left >= 0:
        page.window.left = left
    page.window.maximized = bool(geo.get("maximized", False))
    page.window.min_width = 800
    page.window.min_height = 600

    logger.info("Iniciando servicios...")

    # --- 2. INICIALIZAR BACKEND ---
    wiz = LightController()
    try:
        if hasattr(wiz, "apply_performance_config"):
            wiz.apply_performance_config(perf_cfg)
    except Exception:
        logger.exception("No se pudo aplicar config de performance")

    # --- 3. INICIALIZAR FRONTEND ---
    app = WizzApp(page, wiz)
    page.add(app)

    # Callbacks de sincronización Backend -> Frontend
    def on_bulb_update(state):
        try:
            app.sync_state(state)
        except Exception:
            logger.exception("Error actualizando UI desde LightController")

    wiz.set_callback(on_bulb_update)

    # --- 3.1 Segundo plano / bandeja (Windows) ---
    tray_icon = None
    tray_enabled = False
    user_paused = False
    hidden = False

    def _update_poll_pause():
        try:
            wiz.set_polling_paused(bool(user_paused or hidden))
        except Exception:
            pass

    def _ui_call(fn):
        async def _runner(*_args):
            try:
                fn()
            except Exception:
                logger.exception("Error en acción UI desde bandeja")

        try:
            page.run_task(_runner)
        except Exception:
            try:
                fn()
            except Exception:
                pass

    def _hide_to_tray():
        nonlocal hidden
        hidden = True
        _update_poll_pause()
        try:
            if hasattr(app, "set_background_mode"):
                app.set_background_mode(True)
        except Exception:
            pass
        try:
            page.window.visible = False
            page.update()
        except Exception:
            pass

    def _show_from_tray():
        nonlocal hidden
        hidden = False
        _update_poll_pause()
        try:
            if hasattr(app, "set_background_mode"):
                app.set_background_mode(False)
        except Exception:
            pass
        try:
            page.window.visible = True
            page.window.minimized = False
            page.update()
        except Exception:
            pass

    def _toggle_user_pause():
        nonlocal user_paused
        user_paused = not user_paused
        _update_poll_pause()

    def _exit_app():
        # Permitir cerrar y ejecutar shutdown real
        try:
            page.window.prevent_close = False
        except Exception:
            pass
        try:
            if tray_icon:
                tray_icon.stop()
        except Exception:
            pass
        try:
            _shutdown()
        finally:
            try:
                page.window.close()
            except Exception:
                pass

    def _make_tray_image() -> object | None:
        if not Image or not ImageDraw:
            return None
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((6, 6, 58, 58), radius=14, fill=(15, 23, 42, 255))
        d.ellipse((16, 16, 48, 48), fill=(56, 189, 248, 255))
        return img

    tray_enabled_by_cfg = True
    try:
        tray_enabled_by_cfg = bool((tray_cfg or {}).get("enabled", True))
    except Exception:
        tray_enabled_by_cfg = True

    if pystray is not None and tray_enabled_by_cfg:
        try:
            tray_icon = pystray.Icon(
                "WizzController",
                _make_tray_image(),
                "WizzController",
                menu=pystray.Menu(
                    pystray.MenuItem("Mostrar", lambda _i, _it: _ui_call(_show_from_tray)),
                    pystray.MenuItem("Ocultar", lambda _i, _it: _ui_call(_hide_to_tray)),
                    pystray.MenuItem(
                        "Pausar polling",
                        lambda _i, _it: _ui_call(_toggle_user_pause),
                        checked=lambda _i: bool(user_paused),
                    ),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Salir", lambda _i, _it: _ui_call(_exit_app)),
                ),
            )

            t = threading.Thread(target=tray_icon.run, daemon=True)
            t.start()
            tray_enabled = True
        except Exception:
            logger.exception("No se pudo iniciar la bandeja (pystray)")
            tray_icon = None
            tray_enabled = False

    def _shutdown(*_):
        """Detiene hilos y persiste tamaño/posición de ventana."""
        try:
            cfg.set_window_geometry(
                width=page.window.width,
                height=page.window.height,
                top=getattr(page.window, "top", None),
                left=getattr(page.window, "left", None),
                maximized=getattr(page.window, "maximized", False),
            )
        except Exception:
            logger.exception("No se pudo guardar geometría de ventana")

        try:
            # Hotkeys (keyboard hooks)
            if getattr(app, "hk_manager", None) and hasattr(app.hk_manager, "stop"):
                app.hk_manager.stop()
        except Exception:
            logger.exception("Error deteniendo hotkeys")

        try:
            if hasattr(wiz, "stop"):
                wiz.stop()
        except Exception:
            logger.exception("Error deteniendo LightController")

    page.on_close = _shutdown
    page.on_disconnect = _shutdown

    if tray_enabled:
        try:
            page.window.prevent_close = True
        except Exception:
            pass

        def _on_window_event(e: ft.WindowEvent):
            # Minimizar/ocultar en lugar de cerrar
            try:
                if e.type in (ft.WindowEventType.CLOSE, ft.WindowEventType.MINIMIZE, ft.WindowEventType.HIDE):
                    _hide_to_tray()
                elif e.type in (ft.WindowEventType.SHOW, ft.WindowEventType.RESTORE):
                    _show_from_tray()
                elif e.type == ft.WindowEventType.BLUR:
                    # Si pierde foco, opcionalmente podríamos bajar polling; lo dejamos sólo si está oculto.
                    _update_poll_pause()
                elif e.type == ft.WindowEventType.FOCUS:
                    _update_poll_pause()
            except Exception:
                logger.exception("Error manejando evento de ventana")

        try:
            page.window.on_event = _on_window_event
        except Exception:
            pass

    # --- 4. ARRANQUE FINAL ---
    # Primero renderizamos la página para que los controles existan ("se monten")
    page.update()
    
    logger.info("Interfaz lista. Arrancando motores...")
    
    # AHORA es seguro arrancar los hilos de fondo
    wiz.start()   # Busca luces

if __name__ == "__main__":
    try:
        ft.run(main)
    except KeyboardInterrupt:
        sys.exit()
    except Exception:
        logger.exception("Error fatal ejecutando la app")
        raise
