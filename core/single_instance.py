from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Callable

from app_meta import APP_ID, APP_NAME


class SingleInstanceGuard:
    """Impide que WizZ Desktop se ejecute dos veces.

    En Windows usa objetos del kernel con nombre. La segunda instancia puede:

    1. solicitar que la primera restaure su ventana;
    2. pedir un relevo controlado cuando la primera quedó viva pero perdió su
       sesión/ventana de Flet (el conocido proceso "zombie" de modo dev).

    En otros sistemas se usa un lock de archivo como fallback para desarrollo.
    """

    ERROR_ALREADY_EXISTS = 183
    EVENT_MODIFY_STATE = 0x0002
    WAIT_OBJECT_0 = 0x00000000
    WAIT_TIMEOUT = 0x00000102

    def __init__(
        self,
        app_id: str = APP_ID,
        *,
        lock_path: str | os.PathLike[str] | None = None,
    ) -> None:
        safe_id = "".join(ch if ch.isalnum() else "_" for ch in app_id).strip("_") or APP_ID
        self.app_id = safe_id
        self.mutex_name = rf"Local\{safe_id}.SingleInstance.v1"
        self.event_name = rf"Local\{safe_id}.Activate.v1"
        self.takeover_event_name = rf"Local\{safe_id}.Takeover.v1"
        self.lock_path = Path(lock_path) if lock_path is not None else Path(tempfile.gettempdir()) / f"{safe_id}.lock"
        self.owner_path = self.lock_path.with_name(f"{self.lock_path.name}.owner.json")

        self._mutex_handle = None
        self._event_handle = None
        self._takeover_event_handle = None
        self._lock_file = None
        self._listener: threading.Thread | None = None
        self._listener_stop = threading.Event()
        self._state_lock = threading.RLock()
        self._owner = False

    @property
    def is_owner(self) -> bool:
        with self._state_lock:
            return bool(self._owner)

    @property
    def supported_activation(self) -> bool:
        return os.name == "nt"

    def acquire(self) -> bool:
        """Toma el bloqueo. Devuelve ``False`` si ya existe otra instancia."""
        with self._state_lock:
            if self._owner:
                return True
            if os.name == "nt":
                acquired = self._acquire_windows()
            else:
                acquired = self._acquire_file_lock()
            if acquired:
                self._write_owner_metadata()
            return acquired

    def _acquire_windows(self) -> bool:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateEventW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        ctypes.set_last_error(0)
        mutex = kernel32.CreateMutexW(None, False, self.mutex_name)
        if not mutex:
            return False
        if ctypes.get_last_error() == self.ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(mutex)
            return False

        event = kernel32.CreateEventW(None, False, False, self.event_name)
        takeover_event = kernel32.CreateEventW(None, False, False, self.takeover_event_name)
        if not event or not takeover_event:
            if event:
                kernel32.CloseHandle(event)
            if takeover_event:
                kernel32.CloseHandle(takeover_event)
            kernel32.CloseHandle(mutex)
            return False

        self._mutex_handle = mutex
        self._event_handle = event
        self._takeover_event_handle = takeover_event
        self._owner = True
        return True

    def _acquire_file_lock(self) -> bool:
        try:
            import fcntl

            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            fh = self.lock_path.open("a+", encoding="utf-8")
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                fh.close()
                return False
            fh.seek(0)
            fh.truncate()
            fh.write(str(os.getpid()))
            fh.flush()
            self._lock_file = fh
            self._owner = True
            return True
        except Exception:
            # No debe impedir el desarrollo en una plataforma sin flock.
            self._owner = True
            return True

    def _write_owner_metadata(self) -> None:
        try:
            self.owner_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.owner_path.with_name(f"{self.owner_path.name}.{os.getpid()}.tmp")
            temporary.write_text(
                json.dumps({"pid": os.getpid(), "app_id": self.app_id}),
                encoding="utf-8",
            )
            temporary.replace(self.owner_path)
        except Exception:
            pass

    def owner_pid(self) -> int | None:
        """Devuelve el PID publicado por la instancia propietaria, si existe."""
        try:
            payload = json.loads(self.owner_path.read_text(encoding="utf-8"))
            pid = int(payload.get("pid", 0))
            return pid if pid > 0 else None
        except Exception:
            return None

    def _remove_owner_metadata(self) -> None:
        try:
            payload = json.loads(self.owner_path.read_text(encoding="utf-8"))
            if int(payload.get("pid", 0)) != os.getpid():
                return
            self.owner_path.unlink(missing_ok=True)
        except Exception:
            pass

    def signal_existing(self) -> bool:
        """Pide a la instancia activa que muestre su ventana."""
        return self._signal_named_event(self.event_name)

    def request_takeover(self) -> bool:
        """Solicita cerrar una instancia sin ventana para permitir un reinicio."""
        return self._signal_named_event(self.takeover_event_name)

    def _signal_named_event(self, name: str) -> bool:
        if os.name != "nt":
            return False
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.OpenEventW.restype = wintypes.HANDLE
            kernel32.SetEvent.argtypes = [wintypes.HANDLE]
            kernel32.SetEvent.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL

            handle = kernel32.OpenEventW(self.EVENT_MODIFY_STATE, False, name)
            if not handle:
                return False
            try:
                return bool(kernel32.SetEvent(handle))
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False

    def start_listener(
        self,
        callback: Callable[[], object],
        takeover_callback: Callable[[], object] | None = None,
    ) -> bool:
        """Escucha activación y, opcionalmente, relevo de instancia."""
        if not callable(callback) or not self.is_owner or os.name != "nt" or not self._event_handle:
            return False
        with self._state_lock:
            if self._listener and self._listener.is_alive():
                return True
            self._listener_stop.clear()
            self._listener = threading.Thread(
                target=self._listen_windows,
                args=(callback, takeover_callback),
                name="WizZSingleInstance",
                daemon=True,
            )
            self._listener.start()
            return True

    def _listen_windows(
        self,
        callback: Callable[[], object],
        takeover_callback: Callable[[], object] | None,
    ) -> None:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.WaitForMultipleObjects.argtypes = [
            wintypes.DWORD,
            ctypes.POINTER(wintypes.HANDLE),
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.WaitForMultipleObjects.restype = wintypes.DWORD

        while not self._listener_stop.is_set():
            activation = self._event_handle
            takeover = self._takeover_event_handle
            if not activation or not takeover:
                return
            handles = (wintypes.HANDLE * 2)(activation, takeover)
            result = int(kernel32.WaitForMultipleObjects(2, handles, False, 350))
            if self._listener_stop.is_set():
                return
            if result == self.WAIT_OBJECT_0:
                try:
                    callback()
                except Exception:
                    pass
            elif result == self.WAIT_OBJECT_0 + 1:
                if callable(takeover_callback):
                    try:
                        takeover_callback()
                    except Exception:
                        pass
                return
            elif result != self.WAIT_TIMEOUT:
                return

    def stop_listener(self) -> None:
        self._listener_stop.set()
        if os.name == "nt":
            for handle in (self._event_handle, self._takeover_event_handle):
                if not handle:
                    continue
                try:
                    import ctypes
                    from ctypes import wintypes

                    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                    kernel32.SetEvent.argtypes = [wintypes.HANDLE]
                    kernel32.SetEvent.restype = wintypes.BOOL
                    kernel32.SetEvent(handle)
                except Exception:
                    pass
        thread = self._listener
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._listener = None

    def close(self) -> None:
        """Libera listener y bloqueo. Es seguro llamarlo varias veces."""
        with self._state_lock:
            was_owner = self._owner
            self.stop_listener()
            if os.name == "nt":
                self._close_windows_handles()
            else:
                self._close_file_lock()
            self._owner = False
            if was_owner:
                self._remove_owner_metadata()

    def _close_windows_handles(self) -> None:
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            for handle in (
                self._takeover_event_handle,
                self._event_handle,
                self._mutex_handle,
            ):
                if handle:
                    kernel32.CloseHandle(handle)
        except Exception:
            pass
        self._takeover_event_handle = None
        self._event_handle = None
        self._mutex_handle = None

    def _close_file_lock(self) -> None:
        fh = self._lock_file
        self._lock_file = None
        if fh is None:
            return
        try:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            fh.close()
        except Exception:
            pass

    @staticmethod
    def show_already_running_message() -> None:
        """Fallback visual cuando no se pudo activar la ventana existente."""
        message = f"{APP_NAME} ya se está ejecutando. Revisa el área de notificación de Windows."
        if os.name == "nt":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x40)
                return
            except Exception:
                pass
        try:
            print(message)
        except Exception:
            pass

    def __enter__(self) -> "SingleInstanceGuard":
        if not self.acquire():
            raise RuntimeError(f"Ya existe otra instancia de {APP_NAME}.")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
