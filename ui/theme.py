import flet as ft


class Theme:
    BG = "#0b1020"
    SURFACE = "#141a2e"
    CARD = "#1b2238"
    CARD_HI = "#222c46"
    STROKE = "#2c3654"

    PRIMARY = "#5b8cff"
    PRIMARY_D = "#3b6fe0"
    ACCENT = "#a78bfa"
    SUCCESS = "#34d399"
    WARNING = "#fbbf24"
    ERROR = "#f87171"

    TEXT = "#f1f5fb"
    MUTED = "#8b95b3"
    FAINT = "#5b6688"

    R_SM = 10
    R_MD = 16
    R_LG = 22

    H1 = ft.TextStyle(size=26, weight=ft.FontWeight.BOLD, color=TEXT)
    H2 = ft.TextStyle(size=18, weight=ft.FontWeight.W_600, color=TEXT)
    BODY = ft.TextStyle(size=14, color=TEXT)
    LABEL = ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=MUTED, letter_spacing=1.5)

    GRADIENT = ft.LinearGradient(begin=ft.Alignment(-1.0, -1.0), end=ft.Alignment(1.0, 1.0), colors=["#0b1020", "#141033"])

    SHADOW = ft.BoxShadow(blur_radius=24, spread_radius=0, color=ft.Colors.with_opacity(0.35, "black"), offset=ft.Offset(0, 8))

    @staticmethod
    def GLOW(hex_color):
        return ft.BoxShadow(blur_radius=40, spread_radius=2, color=ft.Colors.with_opacity(0.45, hex_color), offset=ft.Offset(0, 0))


def mounted(control) -> bool:
    try:
        return control.page is not None
    except Exception:
        return False


def supdate(control) -> None:
    try:
        control.update()
    except Exception:
        pass
