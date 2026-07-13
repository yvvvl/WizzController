from __future__ import annotations

import os
import re
import threading
from typing import Any, Callable


class WindowsNativeHotkeyBackend:
    """Backend global basado en ``RegisterHotKey`` de Windows.

    Registra cada combinación de forma independiente y conserva un resultado
    estructurado por atajo. Esto permite mantener activas las combinaciones que
    sí fueron aceptadas y usar el fallback ``keyboard`` solo para las que
    Windows rechazó.
    """

    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    MOD_NOREPEAT = 0x4000

    _VK_BY_KEY: dict[str, int] = {
        "backspace": 0x08,
        "tab": 0x09,
        "enter": 0x0D,
        "esc": 0x1B,
        "escape": 0x1B,
        "space": 0x20,
        "page up": 0x21,
        "pageup": 0x21,
        "page down": 0x22,
        "pagedown": 0x22,
        "end": 0x23,
        "home": 0x24,
        "left": 0x25,
        "up": 0x26,
        "right": 0x27,
        "down": 0x28,
        "insert": 0x2D,
        "delete": 0x2E,
        "plus": 0xBB,
        "+": 0xBB,
        "=": 0xBB,
        "minus": 0xBD,
        "-": 0xBD,
        "comma": 0xBC,
        ",": 0xBC,
        "period": 0xBE,
        ".": 0xBE,
        "slash": 0xBF,
        "/": 0xBF,
        "semicolon": 0xBA,
        ";": 0xBA,
        "quote": 0xDE,
        "'": 0xDE,
        "backtick": 0xC0,
        "`": 0xC0,
        "[": 0xDB,
        "]": 0xDD,
        "\\": 0xDC,
    }

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._registered: dict[int, str] = {}
        self._callbacks: dict[int, Callable[[], Any]] = {}
        self._successful_entries: list[dict[str, Any]] = []
        self._failed_entries: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.started = False

    @property
    def supported(self) -> bool:
        return os.name == "nt"

    @property
    def registered_count(self) -> int:
        with self._lock:
            return len(self._registered)

    @property
    def registered_labels(self) -> list[str]:
        with self._lock:
            return list(self._registered.values())

    @property
    def successful_entries(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(entry) for entry in self._successful_entries]

    @property
    def failed_entries(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(entry) for entry in self._failed_entries]

    def start(self, entries: list[dict[str, Any]]) -> bool:
        self.stop()
        with self._lock:
            self.errors = []
            self._successful_entries = []
            self._failed_entries = []
            self.started = False
        self._ready.clear()
        self._stop.clear()
        self._thread_id = None

        if not self.supported:
            self.errors.append("RegisterHotKey solo está disponible en Windows.")
            return False

        prepared: list[dict[str, Any]] = []
        for idx, source in enumerate(entries, start=1):
            action_id = str(source.get("id") or "").strip()
            combo = str(source.get("combo") or "").strip()
            callback = source.get("callback")
            if not combo or not callable(callback):
                continue
            parsed = self.parse_combo(combo)
            if not parsed:
                self._record_preflight_failure(
                    action_id=action_id,
                    combo=combo,
                    callback=callback,
                    error="tecla no soportada por el backend nativo",
                )
                continue
            modifiers, vk = parsed
            prepared.append(
                {
                    "native_id": 0x5700 + idx,
                    "id": action_id,
                    "combo": combo,
                    "modifiers": modifiers,
                    "vk": vk,
                    "callback": callback,
                }
            )

        if not prepared:
            if not self.errors:
                self.errors.append("No hay hotkeys válidas para registrar.")
            return False

        self._thread = threading.Thread(
            target=self._run,
            args=(prepared,),
            name="WizZNativeHotkeys",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=2.5):
            self.errors.append("Windows no respondió al registrar las hotkeys.")
            self.stop()
            return False
        return self.registered_count > 0

    def _record_preflight_failure(
        self,
        *,
        action_id: str,
        combo: str,
        callback: Callable[[], Any],
        error: str,
    ) -> None:
        row = {"id": action_id, "combo": combo, "callback": callback, "error": error}
        with self._lock:
            self._failed_entries.append(row)
            self.errors.append(f"{combo}: {error}")

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread_id = self._thread_id
            if thread_id:
                try:
                    import ctypes
                    from ctypes import wintypes

                    user32 = ctypes.WinDLL("user32", use_last_error=True)
                    user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
                    user32.PostThreadMessageW.restype = wintypes.BOOL
                    user32.PostThreadMessageW(int(thread_id), self.WM_QUIT, 0, 0)
                except Exception:
                    pass
            if thread is not threading.current_thread():
                thread.join(timeout=2.0)
        self._thread = None
        self._thread_id = None
        self._ready.clear()
        with self._lock:
            self._registered.clear()
            self._callbacks.clear()
        self.started = False

    @classmethod
    def parse_combo(cls, combo: str) -> tuple[int, int] | None:
        parts = [p.strip().lower() for p in str(combo or "").split("+") if p.strip()]
        if not parts:
            return None
        modifiers = 0
        keys: list[str] = []
        for part in parts:
            if part in {"ctrl", "control"}:
                modifiers |= cls.MOD_CONTROL
            elif part == "alt":
                modifiers |= cls.MOD_ALT
            elif part == "shift":
                modifiers |= cls.MOD_SHIFT
            elif part in {"win", "windows", "cmd", "command"}:
                modifiers |= cls.MOD_WIN
            else:
                keys.append(part)
        if len(keys) != 1:
            return None
        vk = cls._vk_for_key(keys[0])
        if vk is None:
            return None
        return modifiers | cls.MOD_NOREPEAT, vk

    @classmethod
    def _vk_for_key(cls, key: str) -> int | None:
        k = key.strip().lower()
        if len(k) == 1 and "a" <= k <= "z":
            return ord(k.upper())
        if len(k) == 1 and "0" <= k <= "9":
            return ord(k)
        m = re.fullmatch(r"f(\d{1,2})", k)
        if m:
            number = int(m.group(1))
            if 1 <= number <= 24:
                return 0x70 + number - 1
        m = re.fullmatch(r"num(?:pad)?\s*([0-9])", k)
        if m:
            return 0x60 + int(m.group(1))
        return cls._VK_BY_KEY.get(k)

    def _run(self, prepared: list[dict[str, Any]]) -> None:
        try:
            self._run_windows(prepared)
        except Exception as exc:
            message = f"backend nativo falló: {exc}"
            with self._lock:
                registered_ids = set(self._registered)
                known_failed = {str(row.get("combo")) for row in self._failed_entries}
                for row in prepared:
                    if int(row["native_id"]) in registered_ids or str(row["combo"]) in known_failed:
                        continue
                    self._failed_entries.append(
                        {
                            "id": row.get("id", ""),
                            "combo": row.get("combo", ""),
                            "callback": row.get("callback"),
                            "error": message,
                        }
                    )
                self.errors.append(message)
                self.started = bool(self._registered)
            self._ready.set()

    def _run_windows(self, prepared: list[dict[str, Any]]) -> None:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM),
                ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD),
                ("pt", POINT),
            ]

        user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.UnregisterHotKey.restype = wintypes.BOOL
        user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.restype = ctypes.c_int
        user32.PeekMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
        user32.PeekMessageW.restype = wintypes.BOOL

        self._thread_id = int(kernel32.GetCurrentThreadId())
        msg = MSG()
        # Fuerza la cola del thread antes de que stop() use PostThreadMessageW.
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        registered_ids: list[int] = []
        local_callbacks: dict[int, Callable[[], Any]] = {}
        successful: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []

        for row in prepared:
            native_id = int(row["native_id"])
            combo = str(row["combo"])
            callback = row["callback"]
            ctypes.set_last_error(0)
            ok = bool(user32.RegisterHotKey(None, native_id, int(row["modifiers"]), int(row["vk"])))
            if ok:
                registered_ids.append(native_id)
                local_callbacks[native_id] = callback
                successful.append(
                    {
                        "id": row.get("id", ""),
                        "combo": combo,
                        "callback": callback,
                        "native_id": native_id,
                    }
                )
            else:
                code = int(ctypes.get_last_error())
                try:
                    detail = ctypes.FormatError(code).strip()
                except Exception:
                    detail = f"error Windows {code}"
                failed.append(
                    {
                        "id": row.get("id", ""),
                        "combo": combo,
                        "callback": callback,
                        "error": detail,
                        "error_code": code,
                    }
                )

        with self._lock:
            self._registered = {
                int(row["native_id"]): str(row["combo"])
                for row in prepared
                if int(row["native_id"]) in registered_ids
            }
            self._callbacks = dict(local_callbacks)
            self._successful_entries.extend(successful)
            self._failed_entries.extend(failed)
            self.errors.extend(f"{row['combo']}: {row['error']}" for row in failed)
            self.started = bool(registered_ids)
        self._ready.set()

        if not registered_ids:
            return

        try:
            while not self._stop.is_set():
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result == 0 or result == -1:
                    break
                if int(msg.message) == self.WM_HOTKEY:
                    callback = local_callbacks.get(int(msg.wParam))
                    if callback:
                        try:
                            callback()
                        except Exception:
                            pass
        finally:
            for native_id in registered_ids:
                try:
                    user32.UnregisterHotKey(None, native_id)
                except Exception:
                    pass
            with self._lock:
                self._registered.clear()
                self._callbacks.clear()
                self.started = False
