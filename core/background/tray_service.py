from __future__ import annotations

import asyncio
import inspect
import os
import threading
import time
from typing import Any, Callable

from app_meta import APP_ID, APP_PRODUCT, display_version
from config.paths import assets_dir
from core.windows_window import restore_window


class TrayService:
    """Bandeja segura para WizZ Controller.

    El tray queda como wrapper de sistema: no toca paneles internos de Flet y
    ejecuta acciones por ActionSequenceExecutor. Así el menú puede controlar la
    luz aunque la ventana esté oculta y sin acoplarse a la UI.
    """

    def __init__(
        self,
        page: Any,
        wiz: Any,
        runtime: Any,
        hotkeys_manager: Any | None = None,
        on_shutdown: Callable[[], Any] | None = None,
    ) -> None:
        self.page = page
        self.wiz = wiz
        self.runtime = runtime
        self.hotkeys_manager = hotkeys_manager
        self.on_shutdown = on_shutdown
        self.icon = None
        self._thread: threading.Thread | None = None
        self.available = False
        self.started = False
        self.last_error: str | None = None
        self._exiting = False
        self._hidden = False
        self._executor = None
        self._pystray = None
        self._Image = None
        self._ImageDraw = None
        self._show_lock = threading.Lock()
        self._last_show_request = 0.0
        self._last_show_ok = False
        try:
            import pystray  # type: ignore
            from PIL import Image, ImageDraw  # type: ignore

            self._pystray = pystray
            self._Image = Image
            self._ImageDraw = ImageDraw
            self.available = True
        except Exception as exc:
            self.available = False
            self.last_error = f"pystray/Pillow no disponible: {exc}"

    # ------------------------------------------------------------------ #
    # Helpers Flet async/sync
    # ------------------------------------------------------------------ #
    def _log(self, msg: str) -> None:
        try:
            print(f"[Tray] {msg}")
        except Exception:
            pass

    def _schedule_page_coroutine(
        self,
        coroutine_factory: Callable[[], Any],
        *,
        label: str,
    ) -> bool:
        """Programa trabajo en el loop de Flet sin filtrar coroutines huérfanas.

        ``Page.run_task()`` construye el coroutine antes de comprobar que el loop
        siga abierto. En modo desktop dev una sesión cerrada puede dejar vivo el
        tray; en ese caso aparecía ``coroutine was never awaited``. Aquí primero
        verificamos el loop y cerramos explícitamente el coroutine si hay una
        carrera durante el scheduling.
        """

        try:
            session = getattr(self.page, "session", None)
            connection = getattr(session, "connection", None)
            loop = getattr(connection, "loop", None)
            if loop is None or loop.is_closed() or not loop.is_running():
                return False

            coroutine = coroutine_factory()
            if not inspect.isawaitable(coroutine):
                return False
            try:
                future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            except Exception:
                try:
                    coroutine.close()
                except Exception:
                    pass
                return False

            def completed(done) -> None:
                try:
                    error = done.exception()
                except Exception:
                    return
                if error is not None and not self._exiting:
                    self.last_error = f"{label}: {error}"
                    self._log(self.last_error)

            future.add_done_callback(completed)
            return True
        except Exception:
            return False

    def _page_update(self) -> bool:
        try:
            self.page.update()
            return True
        except Exception:
            return False

    def _window(self):
        return getattr(self.page, "window", None)

    # ------------------------------------------------------------------ #
    # Bandeja / menú
    # ------------------------------------------------------------------ #
    def start(self) -> bool:
        if self.started and self.icon is not None:
            return True
        if not self.available:
            self._log(f"No disponible: {self.last_error or 'pystray/Pillow no instalado'}")
            return False
        if self.icon is not None:
            return bool(self.started)

        pystray = self._pystray
        assert pystray is not None
        try:
            self.icon = pystray.Icon(
                APP_ID,
                self._make_icon(),
                APP_PRODUCT,
                menu=self._build_menu(),
            )

            if hasattr(self.icon, "run_detached"):
                self.icon.run_detached()
            else:
                self._thread = threading.Thread(target=self.icon.run, name="WizZTray", daemon=True)
                self._thread.start()

            self.started = True
            self.last_error = None
            self._log("Icono de bandeja iniciado. X => ocultar a bandeja. Salir real desde menú.")
            return True
        except Exception as exc:
            self.last_error = f"No se pudo iniciar bandeja: {exc}"
            self.started = False
            self.icon = None
            self._log(self.last_error)
            return False

    def _build_menu(self):
        pystray = self._pystray
        assert pystray is not None
        item = pystray.MenuItem
        menu = pystray.Menu
        sep = pystray.Menu.SEPARATOR

        control_items = [
            item("Encender", lambda icon, it: self._execute({"type": "turn_on"})),
            item("Apagar", lambda icon, it: self._execute({"type": "turn_off"})),
            item("Alternar", lambda icon, it: self._execute({"type": "toggle"})),
        ]

        brightness_menu = menu(
            item("+10%", lambda icon, it: self._execute({"type": "brightness_delta", "value": 10})),
            item("-10%", lambda icon, it: self._execute({"type": "brightness_delta", "value": -10})),
            sep,
            item("25%", lambda icon, it: self._execute({"type": "brightness", "value": 25})),
            item("50%", lambda icon, it: self._execute({"type": "brightness", "value": 50})),
            item("75%", lambda icon, it: self._execute({"type": "brightness", "value": 75})),
            item("100%", lambda icon, it: self._execute({"type": "brightness", "value": 100})),
        )

        colors_menu = menu(
            item("Rojo", lambda icon, it: self._execute({"type": "rgb", "value": "#ff0000"})),
            item("Naranjo", lambda icon, it: self._execute({"type": "rgb", "value": "#ff7f00"})),
            item("Amarillo", lambda icon, it: self._execute({"type": "rgb", "value": "#ffd000"})),
            item("Verde", lambda icon, it: self._execute({"type": "rgb", "value": "#00ff40"})),
            item("Cian", lambda icon, it: self._execute({"type": "rgb", "value": "#00d5ff"})),
            item("Azul", lambda icon, it: self._execute({"type": "rgb", "value": "#0055ff"})),
            item("Morado", lambda icon, it: self._execute({"type": "rgb", "value": "#7f00ff"})),
            item("Rosa", lambda icon, it: self._execute({"type": "rgb", "value": "#ff4fa3"})),
            sep,
            item("Blanco cálido", lambda icon, it: self._execute({"type": "white_percent", "value": 10})),
            item("Blanco neutro", lambda icon, it: self._execute({"type": "white_percent", "value": 50})),
            item("Blanco frío", lambda icon, it: self._execute({"type": "white_percent", "value": 100})),
        )

        scenes_menu = menu(*self._scene_items(limit=9))
        favorites_items = self._favorite_items(limit=8)
        routines_items = self._routine_items(limit=8)
        target_menu = menu(
            item("Una ampolleta", lambda icon, it: self._execute({"type": "target_mode", "value": "single"})),
            item("Todas", lambda icon, it: self._execute({"type": "target_mode", "value": "all"})),
        )

        dynamic_sections = [
            item("Brillo", brightness_menu),
            item("Colores / blanco", colors_menu),
            item("Escenas WiZ", scenes_menu),
        ]
        if favorites_items:
            dynamic_sections.append(item("Favoritos", menu(*favorites_items)))
        if routines_items:
            dynamic_sections.append(item("Rutinas", menu(*routines_items)))
        dynamic_sections.append(item("Destino", target_menu))

        hotkey_items = self._hotkey_menu_items()

        return menu(
            item("Mostrar WizZ", lambda icon, it: self.show_window(), default=True),
            item("Ocultar a bandeja", lambda icon, it: self.hide_window()),
            item("Actualizar menú", lambda icon, it: self.refresh_menu()),
            sep,
            item(self._status_label(), self._noop, enabled=False),
            item(self._target_label(), self._noop, enabled=False),
            sep,
            *control_items,
            *dynamic_sections,
            sep,
            *hotkey_items,
            sep,
            item(display_version(), self._noop, enabled=False),
            item("Salir", lambda icon, it: self.exit_app()),
        )

    def _scene_items(self, limit: int = 9):
        pystray = self._pystray
        assert pystray is not None
        item = pystray.MenuItem
        try:
            from core import wiz_scenes

            ids = [18, 16, 14, 11, 12, 13, 4, 1, 5]
            out = []
            for scene_id in ids[:limit]:
                scene = wiz_scenes.get(scene_id)
                if scene:
                    out.append(item(scene.name, lambda icon, it, sid=scene.id: self._execute({"type": "scene", "value": {"sceneId": sid, "speed": 100}})))
            return out
        except Exception:
            return [item("TV / Cine", lambda icon, it: self._execute({"type": "scene", "value": {"sceneId": 18, "speed": 100}}))]

    def _favorite_items(self, limit: int = 8):
        pystray = self._pystray
        assert pystray is not None
        item = pystray.MenuItem
        try:
            from config.favorites_manager import FavoritesManager

            out = []
            for fav in FavoritesManager().get_favorites()[:limit]:
                uid = fav.get("id")
                if uid:
                    name = str(fav.get("name") or "Favorito")[:36]
                    out.append(item(name, lambda icon, it, x=str(uid): self._execute({"type": "favorite", "value": x})))
            return out
        except Exception:
            return []

    def _routine_items(self, limit: int = 8):
        pystray = self._pystray
        assert pystray is not None
        item = pystray.MenuItem
        try:
            from config.routines_manager import RoutinesManager

            out = []
            for routine in RoutinesManager().get_routines()[:limit]:
                uid = routine.get("id")
                if uid:
                    name = str(routine.get("name") or "Rutina")[:36]
                    out.append(item(name, lambda icon, it, x=str(uid): self._execute({"type": "routine", "value": x})))
            return out
        except Exception:
            return []

    def _hotkey_menu_items(self):
        pystray = self._pystray
        assert pystray is not None
        item = pystray.MenuItem
        if self.hotkeys_manager is None:
            return []
        status = "Hotkeys: " + self._safe_str(lambda: self.hotkeys_manager.backend_status(), "sin estado")
        return [
            item(status, self._noop, enabled=False),
            item("Re-registrar hotkeys", lambda icon, it: self._rehook_hotkeys()),
        ]

    def refresh_menu(self) -> None:
        try:
            if self.icon is not None:
                self.icon.menu = self._build_menu()
                update = getattr(self.icon, "update_menu", None)
                if callable(update):
                    update()
        except Exception as exc:
            self.last_error = f"No se pudo actualizar menú: {exc}"
            self._log(self.last_error)

    def _make_icon(self):
        Image = self._Image
        ImageDraw = self._ImageDraw
        assert Image is not None and ImageDraw is not None

        for filename in ("tray_icon.png", "icon_windows.png", "icon.png"):
            try:
                path = assets_dir() / filename
                if not path.is_file():
                    continue
                source = Image.open(path).convert("RGBA")
                resampling = getattr(Image, "Resampling", Image)
                return source.resize((64, 64), resampling.LANCZOS)
            except Exception:
                continue

        # Fallback autocontenido si el asset no está disponible.
        img = Image.new("RGBA", (64, 64), (13, 19, 38, 255))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((9, 9, 55, 55), radius=14, fill=(16, 23, 45, 255), outline=(91, 140, 255, 255), width=3)
        d.ellipse((22, 13, 42, 35), fill=(255, 255, 255, 255))
        d.rounded_rectangle((26, 33, 38, 48), radius=4, fill=(91, 140, 255, 255))
        d.rectangle((22, 47, 42, 51), fill=(167, 139, 250, 255))
        return img

    def is_running(self) -> bool:
        return bool(self.started and self.icon is not None and not self._exiting)

    def _noop(self, *args, **kwargs) -> None:
        return None

    def _safe_str(self, fn: Callable[[], Any], fallback: str) -> str:
        try:
            return str(fn())
        except Exception:
            return fallback

    def _executor_instance(self):
        if self._executor is None:
            from core.action_sequence import ActionSequenceExecutor

            self._executor = ActionSequenceExecutor(self.wiz)
        return self._executor

    def _execute(self, payload: dict[str, Any]) -> None:
        try:
            self._executor_instance().execute(payload, threaded=True)
            # Refrescar el texto de estado después de una acción sin forzar UI.
            timer = threading.Timer(0.35, self.refresh_menu)
            timer.daemon = True
            timer.start()
        except Exception as exc:
            self.last_error = f"Acción tray falló: {exc}"
            self._log(self.last_error)

    def _rehook_hotkeys(self) -> None:
        try:
            if self.hotkeys_manager is not None:
                self.hotkeys_manager.apply_hooks()
            self.refresh_menu()
        except Exception as exc:
            self.last_error = f"No se pudieron re-registrar hotkeys: {exc}"
            self._log(self.last_error)

    def _tray_status(self) -> dict[str, Any]:
        try:
            fn = getattr(self.wiz, "get_tray_status", None)
            if callable(fn):
                status = fn()
                return status if isinstance(status, dict) else {}
        except Exception:
            pass
        return {}

    def _status_label(self) -> str:
        status = self._tray_status()
        state = status.get("state") if isinstance(status.get("state"), dict) else {}
        online = bool(status.get("online"))
        power = "encendida" if bool(state.get("state", True)) else "apagada"
        dimming = state.get("dimming")
        bri = f" · {int(dimming)}%" if isinstance(dimming, (int, float)) else ""
        name = str(status.get("name") or "Ampolleta")[:28]
        conn = "online" if online else "sin respuesta"
        return f"{name}: {power}{bri} · {conn}"

    def _target_label(self) -> str:
        status = self._tray_status()
        mode = "1 luz" if status.get("mode") == "single" else "todas"
        ip = status.get("ip") or "—"
        return f"Destino: {mode} · {ip}"

    # ------------------------------------------------------------------ #
    # Ventana
    # ------------------------------------------------------------------ #
    def show_window(self) -> bool:
        """Restaura la ventana desde tray o instancia única.

        La restauración visual se hace primero con Win32, por lo que no depende
        del event loop de Flet ni llama ``Window.to_front()`` desde un thread de
        pystray. Después se sincroniza el modelo de Flet de forma oportunista.
        """

        now = time.monotonic()
        if now - self._last_show_request < 0.12:
            return self._last_show_ok
        if not self._show_lock.acquire(blocking=False):
            return self._last_show_ok

        try:
            self._last_show_request = now
            self._log("Mostrar WizZ solicitado")
            title = str(getattr(self.page, "title", "") or APP_PRODUCT)
            native = restore_window(title, process_id=os.getpid())

            async def sync_flet_window() -> None:
                w = self._window()
                if w is None:
                    return
                w.visible = True
                w.skip_task_bar = False
                w.minimized = False
                w.focused = True
                self._hidden = False
                self.page.update()

            scheduled = self._schedule_page_coroutine(
                sync_flet_window,
                label="No se pudo sincronizar la ventana",
            )
            self._hidden = False
            self._last_show_ok = bool(native.ok or scheduled)

            if not self._last_show_ok:
                self.last_error = native.reason or "La sesión Flet ya no está disponible"
                self._log(f"No se pudo restaurar: {self.last_error}")
            elif native.found and native.reason != "restaurada":
                self._log(native.reason)
            return self._last_show_ok
        finally:
            self._show_lock.release()

    def hide_window(self) -> bool:
        """Oculta la ventana solo si la bandeja está viva."""
        if not self.is_running():
            self._log("No puedo ocultar: bandeja no está corriendo")
            return False
        if self._window() is None:
            self._log("No puedo ocultar: window no disponible")
            return False

        async def sync_hidden_window() -> None:
            w = self._window()
            if w is None:
                return
            w.visible = False
            w.skip_task_bar = True
            self._hidden = True
            self.page.update()

        if self._schedule_page_coroutine(
            sync_hidden_window,
            label="No se pudo ocultar la ventana",
        ):
            self._hidden = True
            self._log("Ventana ocultada a bandeja")
            return True

        # Fallback sync para sesiones antiguas/fakes donde no hay loop expuesto.
        w = self._window()
        try:
            w.visible = False
            w.skip_task_bar = True
            self._hidden = True
            self._page_update()
            self._log("Ventana ocultada a bandeja (fallback)")
            return True
        except Exception as exc:
            self.last_error = f"visible=False falló: {exc}"
            self._log(self.last_error)
        try:
            w.minimized = True
            self._hidden = True
            self._page_update()
            self._log("Ventana minimizada como fallback")
            return True
        except Exception as exc:
            self.last_error = f"minimized=True falló: {exc}"
            self._log(self.last_error)
            return False

    def real_close(self) -> None:
        """Cierre real robusto, respetando métodos async/sync de Flet."""
        if self._exiting:
            return
        self._exiting = True
        try:
            self.page.window.prevent_close = False
        except Exception:
            pass
        try:
            if callable(self.on_shutdown):
                self.on_shutdown()
            else:
                self.wiz.stop()
        except Exception:
            pass
        self.stop()

        async def destroy_later():
            try:
                await asyncio.sleep(0.05)
                destroy = getattr(self.page.window, "destroy", None)
                if callable(destroy):
                    res = destroy()
                    if inspect.isawaitable(res):
                        await res
            except Exception:
                os._exit(0)

        if not self._schedule_page_coroutine(
            destroy_later,
            label="No se pudo cerrar la ventana",
        ):
            os._exit(0)

    # ------------------------------------------------------------------ #
    # Cierre
    # ------------------------------------------------------------------ #
    def stop(self) -> None:
        try:
            if self.icon:
                self.icon.stop()
        except Exception:
            pass
        self.icon = None
        self.started = False

    def exit_app(self) -> None:
        """Salida real desde el menú de bandeja."""
        self._log("Salir solicitado")
        self.real_close()


def _is_close_event(e: Any) -> bool:
    t = getattr(e, "type", None)
    if t is not None:
        value = str(getattr(t, "value", t)).lower()
        if value == "close" or "close" in value:
            return True
    data = str(
        getattr(e, "data", "")
        or getattr(e, "name", "")
        or ""
    ).lower()
    return "close" in data


def _destroy_window(page: Any, on_shutdown: Callable[[], Any] | None = None) -> None:
    try:
        if callable(on_shutdown):
            on_shutdown()
    except Exception:
        pass

    async def destroy_later():
        try:
            destroy = getattr(page.window, "destroy", None)
            if callable(destroy):
                res = destroy()
                if inspect.isawaitable(res):
                    await res
        except Exception:
            os._exit(0)

    coroutine = None
    try:
        session = getattr(page, "session", None)
        connection = getattr(session, "connection", None)
        loop = getattr(connection, "loop", None)
        if loop is None or loop.is_closed() or not loop.is_running():
            os._exit(0)
        coroutine = destroy_later()
        asyncio.run_coroutine_threadsafe(coroutine, loop)
    except Exception:
        if coroutine is not None:
            try:
                coroutine.close()
            except Exception:
                pass
        os._exit(0)


def install_window_handlers(
    page: Any,
    tray: TrayService | None,
    runtime: Any,
    on_shutdown: Callable[[], Any] | None = None,
) -> None:
    """Instala X => bandeja de forma robusta.

    Regla:
    - Si pystray está activo y minimize_to_tray=True: X oculta a bandeja.
    - Si pystray no está activo o minimize_to_tray=False: X cierra real.
    """
    def set_prevent_close() -> None:
        try:
            page.window.prevent_close = bool(tray is not None and tray.is_running())
        except Exception:
            pass

    set_prevent_close()

    def on_window_event(e):
        if not _is_close_event(e):
            return
        minimize = True
        try:
            minimize = bool(runtime.get("minimize_to_tray", True))
        except Exception:
            pass

        if minimize and tray is not None and tray.is_running():
            if tray.hide_window():
                try:
                    page.window.prevent_close = True
                except Exception:
                    pass
                return

        try:
            page.window.prevent_close = False
        except Exception:
            pass
        if tray is not None:
            tray.real_close()
        else:
            _destroy_window(page, on_shutdown=on_shutdown)

    try:
        page.window.on_event = on_window_event
    except Exception:
        pass
    try:
        page.on_window_event = on_window_event
    except Exception:
        pass
    try:
        page.update()
    except Exception:
        pass

    try:
        print("[Tray] Handler X instalado: X => bandeja si tray activo; Salir => cierre real.")
    except Exception:
        pass
