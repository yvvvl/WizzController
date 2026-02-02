import flet as ft


def _safe_page_update(page: ft.Page) -> None:
    try:
        page.update()
    except Exception:
        pass


def show_snackbar(
    page: ft.Page | None,
    message: str,
    *,
    bgcolor: str | None = None,
    duration_ms: int = 2500,
) -> bool:
    """Muestra un SnackBar compatible con Flet 0.80.x.

    En Flet recientes ya no existe `page.show_snack_bar()` ni `page.open()`.
    Este helper usa `page.overlay` y abre el SnackBar.
    """

    if page is None:
        return False

    try:
        # Limpia snackbars viejos para que overlay no crezca sin lÃ­mite
        page.overlay = [c for c in page.overlay if not isinstance(c, ft.SnackBar)]
    except Exception:
        pass

    try:
        sb = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=bgcolor,
            duration=duration_ms,
        )
        try:
            page.overlay.append(sb)
        except Exception:
            # si overlay no es list o falla por tipo, reintenta estableciendo lista
            page.overlay = list(getattr(page, "overlay", []) or [])
            page.overlay.append(sb)
        sb.open = True
        _safe_page_update(page)
        return True
    except Exception:
        return False


def show_dialog(page: ft.Page | None, dialog: ft.AlertDialog) -> bool:
    if page is None:
        return False

    try:
        page.show_dialog(dialog)
        return True
    except Exception:
        try:
            if dialog not in page.overlay:
                page.overlay.append(dialog)
            dialog.open = True
            _safe_page_update(page)
            return True
        except Exception:
            return False


def close_dialog(page: ft.Page | None, dialog: ft.AlertDialog | None = None) -> bool:
    if page is None:
        return False

    try:
        page.pop_dialog()
        return True
    except Exception:
        if dialog is None:
            return False
        try:
            dialog.open = False
            _safe_page_update(page)
            return True
        except Exception:
            return False
