from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WindowActivationResult:
    """Resultado de intentar restaurar una ventana nativa de Windows."""

    found: bool
    activated: bool
    hwnd: int | None = None
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.found and self.activated


def restore_window(
    title: str,
    *,
    process_id: int | None = None,
) -> WindowActivationResult:
    """Muestra y trae al frente una ventana Win32 sin depender del loop de Flet.

    La función es deliberadamente nativa: los callbacks de ``pystray`` y del
    listener de instancia única ocurren fuera del loop de Flet. Invocar allí
    ``Window.to_front()`` puede crear coroutines que nunca llegan a ejecutarse
    cuando la sesión desktop ya cerró. Con Win32 podemos restaurar una ventana
    válida sin cruzar ese límite de threads.
    """

    if os.name != "nt":
        return WindowActivationResult(False, False, reason="Win32 no disponible")

    clean_title = str(title or "").strip()
    if not clean_title:
        return WindowActivationResult(False, False, reason="Título vacío")

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM,
        )

        user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
        user32.EnumWindows.restype = wintypes.BOOL
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int,
        ]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindow.restype = wintypes.BOOL
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.IsIconic.argtypes = [wintypes.HWND]
        user32.IsIconic.restype = wintypes.BOOL
        user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindowAsync.restype = wintypes.BOOL
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.BringWindowToTop.argtypes = [wintypes.HWND]
        user32.BringWindowToTop.restype = wintypes.BOOL
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        user32.GetForegroundWindow.argtypes = []
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.SetFocus.argtypes = [wintypes.HWND]
        user32.SetFocus.restype = wintypes.HWND
        user32.AttachThreadInput.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.BOOL,
        ]
        user32.AttachThreadInput.restype = wintypes.BOOL
        user32.FlashWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
        user32.FlashWindow.restype = wintypes.BOOL
        kernel32.GetCurrentThreadId.argtypes = []
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD

        candidates: list[tuple[int, int, int]] = []
        exact_title_fallbacks: list[tuple[int, int, int]] = []
        wanted_pid = int(process_id) if process_id else None
        wanted_pids: set[int] | None = None
        if wanted_pid is not None:
            wanted_pids = {wanted_pid}
            # En Flet desktop la ventana pertenece al proceso cliente de Flet,
            # que normalmente es hijo del proceso Python propietario del mutex.
            try:
                import psutil  # type: ignore

                root = psutil.Process(wanted_pid)
                wanted_pids.update(
                    int(child.pid) for child in root.children(recursive=True)
                )
            except Exception:
                pass
        wanted_folded = clean_title.casefold()

        @EnumWindowsProc
        def collect(hwnd, _lparam):
            try:
                if not user32.IsWindow(hwnd):
                    return True

                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                current_pid = int(pid.value)

                length = int(user32.GetWindowTextLengthW(hwnd))
                if length <= 0:
                    return True
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                current_title = str(buffer.value or "").strip()
                if not current_title:
                    return True

                folded = current_title.casefold()
                if folded == wanted_folded:
                    title_rank = 3
                elif folded.startswith(wanted_folded):
                    title_rank = 2
                elif wanted_folded in folded:
                    title_rank = 1
                else:
                    return True

                visible_rank = 1 if user32.IsWindowVisible(hwnd) else 0
                row = (title_rank, visible_rank, int(hwnd))
                if wanted_pids is None or current_pid in wanted_pids:
                    candidates.append(row)
                elif title_rank == 3:
                    # En un build nativo de Flet la ventana puede pertenecer al
                    # launcher padre y el mutex al runtime Python hijo. El
                    # título exacto es un fallback más seguro que incluir todo
                    # el árbol de Explorer/terminal.
                    exact_title_fallbacks.append(row)
            except Exception:
                pass
            return True

        if not user32.EnumWindows(collect, 0):
            error = int(ctypes.get_last_error())
            if error:
                return WindowActivationResult(
                    False,
                    False,
                    reason=f"EnumWindows falló ({error})",
                )

        if not candidates and exact_title_fallbacks:
            candidates = exact_title_fallbacks

        if not candidates:
            pid_text = (
                f" para el árbol del PID {wanted_pid}"
                if wanted_pid
                else ""
            )
            return WindowActivationResult(
                False,
                False,
                reason=f"No se encontró '{clean_title}'{pid_text}",
            )

        candidates.sort(reverse=True)
        hwnd = wintypes.HWND(candidates[0][2])

        SW_SHOW = 5
        SW_RESTORE = 9
        HWND_TOP = wintypes.HWND(0)
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_SHOWWINDOW = 0x0040

        command = SW_RESTORE if user32.IsIconic(hwnd) else SW_SHOW
        user32.ShowWindowAsync(hwnd, command)
        user32.SetWindowPos(
            hwnd,
            HWND_TOP,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
        )

        # Windows puede negar SetForegroundWindow desde un thread de fondo.
        # Adjuntar temporalmente las colas de entrada mejora la restauración sin
        # depender de hacks de teclado ni de APIs internas de Flet.
        current_tid = int(kernel32.GetCurrentThreadId())
        target_tid = int(user32.GetWindowThreadProcessId(hwnd, None))
        foreground = user32.GetForegroundWindow()
        foreground_tid = (
            int(user32.GetWindowThreadProcessId(foreground, None))
            if foreground
            else 0
        )

        attached: list[tuple[int, int]] = []
        try:
            for source_tid in {current_tid, foreground_tid}:
                if source_tid and target_tid and source_tid != target_tid:
                    if user32.AttachThreadInput(source_tid, target_tid, True):
                        attached.append((source_tid, target_tid))

            user32.BringWindowToTop(hwnd)
            foreground_ok = bool(user32.SetForegroundWindow(hwnd))
            user32.SetFocus(hwnd)
        finally:
            for source_tid, destination_tid in reversed(attached):
                try:
                    user32.AttachThreadInput(
                        source_tid,
                        destination_tid,
                        False,
                    )
                except Exception:
                    pass

        # Si Windows mantiene la política de foco, la ventana ya quedó visible;
        # un destello en la barra de tareas evita que la solicitud pase inadvertida.
        if not foreground_ok:
            try:
                user32.FlashWindow(hwnd, True)
            except Exception:
                pass

        return WindowActivationResult(
            True,
            True,
            int(hwnd.value or 0),
            "restaurada" if foreground_ok else "visible; Windows limitó el foco",
        )
    except Exception as exc:
        return WindowActivationResult(
            False,
            False,
            reason=f"Restauración Win32 falló: {exc}",
        )
