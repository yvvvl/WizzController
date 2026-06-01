from __future__ import annotations

import asyncio
import inspect
import os
import threading
import time
from typing import Any, Callable


class TrayService:
    """Bandeja segura para WizZ Controller.

    Fase 37:
    - Corrige el botón X de Flet 0.85: Window.destroy()/to_front() son async.
    - X => ocultar a bandeja si pystray está activo y minimize_to_tray=True.
    - Menú Salir => cierre real, esperando correctamente el destroy async.
    - Click/doble click tray => mostrar ventana principal.
    """

    def __init__(self, page: Any, wiz: Any, app: Any, runtime: Any) -> None:
        self.page = page
        self.wiz = wiz
        self.app = app
        self.runtime = runtime
        self.icon = None
        self._thread: threading.Thread | None = None
        self.available = False
        self.started = False
        self.last_error: str | None = None
        self._exiting = False
        self._hidden = False
        self._close_lock = threading.Lock()
        self._pystray = None
        self._Image = None
        self._ImageDraw = None
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

    def _run_async(self, coro) -> None:
        """Ejecuta un coroutine de Flet desde cualquier thread."""
        if coro is None:
            return
        try:
            if not inspect.isawaitable(coro):
                return
            async def runner():
                try:
                    await coro
                except Exception as exc:
                    self.last_error = str(exc)
                    self._log(f"Error async: {exc}")
            self.page.run_task(runner)
        except Exception as exc:
            self.last_error = f"No se pudo programar async: {exc}"
            self._log(self.last_error)

    def _call_window_async_method(self, name: str) -> None:
        w = self._window()
        if w is None:
            return
        method = getattr(w, name, None)
        if not callable(method):
            return
        try:
            res = method()
            if inspect.isawaitable(res):
                self._run_async(res)
        except Exception as exc:
            self.last_error = f"window.{name} falló: {exc}"
            self._log(self.last_error)

    def _page_update(self) -> None:
        try:
            self.page.update()
        except Exception:
            pass

    def _window(self):
        return getattr(self.page, "window", None)

    # ------------------------------------------------------------------ #
    # Bandeja
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
            open_item = pystray.MenuItem(
                "Mostrar WizZ",
                lambda icon, item: self.show_window(),
                default=True,
            )
            self.icon = pystray.Icon(
                "WizZController",
                self._make_icon(),
                "WizZ Controller",
                menu=pystray.Menu(
                    open_item,
                    pystray.MenuItem("Ocultar a bandeja", lambda icon, item: self.hide_window()),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Encender", lambda icon, item: self._safe(self.wiz.turn_on)),
                    pystray.MenuItem("Apagar", lambda icon, item: self._safe(self.wiz.turn_off)),
                    pystray.MenuItem("Alternar", lambda icon, item: self._safe(self.wiz.toggle)),
                    pystray.MenuItem("TV / Cine", lambda icon, item: self._safe(lambda: self.wiz.set_scene(18))),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Pausar/Reanudar voz", lambda icon, item: self.toggle_voice()),
                    pystray.MenuItem("Salir", lambda icon, item: self.exit_app()),
                ),
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

    def _make_icon(self):
        Image = self._Image
        ImageDraw = self._ImageDraw
        assert Image is not None and ImageDraw is not None
        img = Image.new("RGBA", (64, 64), (13, 19, 38, 255))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((10, 10, 54, 54), radius=12, fill=(91, 140, 255, 255))
        d.ellipse((24, 15, 40, 33), fill=(255, 255, 255, 255))
        d.rounded_rectangle((27, 32, 37, 46), radius=4, fill=(255, 255, 255, 255))
        d.rectangle((22, 45, 42, 49), fill=(255, 255, 255, 255))
        return img

    def is_running(self) -> bool:
        return bool(self.started and self.icon is not None and not self._exiting)

    def _safe(self, fn: Callable[[], Any]) -> None:
        try:
            fn()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Ventana
    # ------------------------------------------------------------------ #
    def show_window(self) -> None:
        self._log("Mostrar WizZ solicitado")
        w = self._window()
        try:
            if w is not None:
                try:
                    w.visible = True
                except Exception:
                    pass
                try:
                    w.skip_task_bar = False
                except Exception:
                    pass
                try:
                    w.minimized = False
                except Exception:
                    pass
                try:
                    w.focused = True
                except Exception:
                    pass
                self._call_window_async_method("to_front")
            self._hidden = False
            self._page_update()
        except Exception as exc:
            self.last_error = f"No se pudo mostrar ventana: {exc}"
            self._log(self.last_error)

    def hide_window(self) -> bool:
        """Oculta la ventana solo si la bandeja está viva."""
        if not self.is_running():
            self._log("No puedo ocultar: bandeja no está corriendo")
            return False
        w = self._window()
        if w is None:
            self._log("No puedo ocultar: window no disponible")
            return False
        try:
            w.visible = False
            # Esto ayuda a que no quede fantasma en taskbar cuando visible=False no aplica de inmediato.
            try:
                w.skip_task_bar = True
            except Exception:
                pass
            self._hidden = True
            self._page_update()
            self._log("Ventana ocultada a bandeja")
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
        """Cierre real robusto, respetando métodos async de Flet."""
        if self._exiting:
            return
        self._exiting = True
        try:
            self.page.window.prevent_close = False
        except Exception:
            pass
        try:
            vp = self._voice_panel()
            if vp is not None and vp.service.is_continuous_running():
                vp.service.stop_continuous()
                self.runtime.remember_voice_active(False)
        except Exception:
            pass
        try:
            self.wiz.stop()
        except Exception:
            pass
        self.stop()

        async def destroy_later():
            try:
                await asyncio.sleep(0.05)
                await self.page.window.destroy()
            except Exception:
                os._exit(0)

        try:
            self.page.run_task(destroy_later)
        except Exception:
            os._exit(0)

    # ------------------------------------------------------------------ #
    # Voz / cierre
    # ------------------------------------------------------------------ #
    def _voice_panel(self):
        for p in getattr(self.app, "panels", []):
            if hasattr(p, "service") and hasattr(p.service, "start_continuous"):
                return p
        return None

    def toggle_voice(self) -> None:
        vp = self._voice_panel()
        if vp is None:
            return
        try:
            if vp.service.is_continuous_running():
                vp.service.stop_continuous()
                self.runtime.remember_voice_active(False)
            else:
                vp.service.start_continuous(callback=getattr(vp, "_on_continuous_event", None))
                self.runtime.remember_voice_active(True)
            if hasattr(vp, "_sync_continuous_ui"):
                vp._sync_continuous_ui()
        except Exception:
            pass

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


def install_window_handlers(page: Any, tray: TrayService | None, runtime: Any) -> None:
    """Instala X => bandeja de forma robusta.

    Regla:
    - Si pystray está activo y minimize_to_tray=True: X oculta a bandeja.
    - Si pystray no está activo o minimize_to_tray=False: X cierra real.
    """
    try:
        if hasattr(runtime, "set"):
            runtime.set("tray_enabled", True)
            runtime.set("minimize_to_tray", True)
    except Exception:
        pass

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
                # Mantener prevent_close, porque la app queda viva en bandeja.
                try:
                    page.window.prevent_close = True
                except Exception:
                    pass
                return

        # Si no hay tray o falló ocultar, cerrar de verdad. No dejar app atrapada.
        try:
            page.window.prevent_close = False
        except Exception:
            pass
        if tray is not None:
            tray.real_close()
        else:
            async def destroy_later():
                try:
                    await page.window.destroy()
                except Exception:
                    os._exit(0)
            try:
                page.run_task(destroy_later)
            except Exception:
                os._exit(0)

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
