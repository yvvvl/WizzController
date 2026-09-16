import flet as ft


class Theme:
    """Semantic Flet tokens for the desktop themes.

    Controls consume these semantic names instead of product colours inline.
    ``configure`` runs before the shell is built, making the selection
    persistent across source and packaged starts.
    """
    BG = "#060914"
    SURFACE = "#0c1326"
    CARD = "#101a30"
    CARD_HI = "#151f37"
    STROKE = "#24324d"

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

    GRADIENT = ft.LinearGradient(begin=ft.Alignment(-1.0, -1.0), end=ft.Alignment(1.0, 1.0), colors=["#060914", "#0d1530"])
    RAIL_GRADIENT = ft.LinearGradient(begin=ft.Alignment(-1.0, -1.0), end=ft.Alignment(0.2, 1.0), colors=["#111a35", "#080d1c"])
    MASTER_ON_GRADIENT = ft.LinearGradient(begin=ft.Alignment(-1.0, -1.0), end=ft.Alignment(1.0, 1.0), colors=["#182d5c", "#111d3a"])

    SHADOW = ft.BoxShadow(blur_radius=24, spread_radius=0, color=ft.Colors.with_opacity(0.35, "black"), offset=ft.Offset(0, 8))
    NAME = "midnight"
    REDUCED_MOTION = False

    _PALETTES = {
        "midnight": {"BG": "#060914", "SURFACE": "#0b1225", "CARD": "#10192e", "CARD_HI": "#151f37", "STROKE": "#24324d", "PRIMARY": "#5f91ff", "PRIMARY_D": "#416fe5", "ACCENT": "#ad8cff", "TEXT": "#f4f7ff", "MUTED": "#a4b0ca", "FAINT": "#697899"},
        "dark": {"BG": "#111318", "SURFACE": "#181c25", "CARD": "#1c2230", "CARD_HI": "#252d3d", "STROKE": "#303b50", "PRIMARY": "#5b96ff", "PRIMARY_D": "#3d73dc", "ACCENT": "#a287ff", "TEXT": "#f6f7fb", "MUTED": "#adb4c4", "FAINT": "#778197"},
        "ocean": {"BG": "#061418", "SURFACE": "#0a2027", "CARD": "#102a33", "CARD_HI": "#153842", "STROKE": "#24505a", "PRIMARY": "#42c5dc", "PRIMARY_D": "#249db6", "ACCENT": "#82e1d0", "TEXT": "#effdff", "MUTED": "#a6c8ca", "FAINT": "#668d93"},
        "violet": {"BG": "#10091a", "SURFACE": "#1a1030", "CARD": "#231642", "CARD_HI": "#2d1d52", "STROKE": "#47316d", "PRIMARY": "#a577ff", "PRIMARY_D": "#8054dc", "ACCENT": "#ff91c6", "TEXT": "#fcf6ff", "MUTED": "#c7b5d9", "FAINT": "#8d77a6"},
        "aurora": {"BG": "#07111f", "SURFACE": "#0b1d31", "CARD": "#102842", "CARD_HI": "#143655", "STROKE": "#24547a", "PRIMARY": "#58c9ff", "PRIMARY_D": "#319bd4", "ACCENT": "#92f0d2", "TEXT": "#effaff", "MUTED": "#a8c7d8", "FAINT": "#668da6"},
        "forest": {"BG": "#07160f", "SURFACE": "#0c2419", "CARD": "#123222", "CARD_HI": "#19422d", "STROKE": "#286144", "PRIMARY": "#58d69a", "PRIMARY_D": "#2da86d", "ACCENT": "#b7ee71", "TEXT": "#f0fff5", "MUTED": "#a7cdb4", "FAINT": "#668e76"},
        "ember": {"BG": "#1a0d0b", "SURFACE": "#2a1210", "CARD": "#3a1915", "CARD_HI": "#4c211b", "STROKE": "#753329", "PRIMARY": "#ff8663", "PRIMARY_D": "#d85b3f", "ACCENT": "#ffc06b", "TEXT": "#fff6f1", "MUTED": "#e0b9aa", "FAINT": "#a47668"},
        "sapphire": {"BG": "#071027", "SURFACE": "#0b1938", "CARD": "#10244c", "CARD_HI": "#17305f", "STROKE": "#294a87", "PRIMARY": "#5d9dff", "PRIMARY_D": "#3676dc", "ACCENT": "#b4a5ff", "TEXT": "#f3f7ff", "MUTED": "#b2c4e6", "FAINT": "#748bb4"},
        "rose": {"BG": "#1b0917", "SURFACE": "#2a1028", "CARD": "#3b1638", "CARD_HI": "#512047", "STROKE": "#783968", "PRIMARY": "#fa72bb", "PRIMARY_D": "#d64d99", "ACCENT": "#f5bd72", "TEXT": "#fff4fb", "MUTED": "#e3b7d2", "FAINT": "#a77898"},
        "oled": {"BG": "#000000", "SURFACE": "#050506", "CARD": "#0a0b0f", "CARD_HI": "#10121a", "STROKE": "#1b2030", "PRIMARY": "#6192ff", "PRIMARY_D": "#3d6ed9", "ACCENT": "#bd9cff", "TEXT": "#f7f8fc", "MUTED": "#a7afc0", "FAINT": "#667087"},
        "light": {"BG": "#f6f8fc", "SURFACE": "#ffffff", "CARD": "#ffffff", "CARD_HI": "#eef3ff", "STROKE": "#d8e0ee", "PRIMARY": "#2667da", "PRIMARY_D": "#1f56bd", "ACCENT": "#7057da", "TEXT": "#14213a", "MUTED": "#60708c", "FAINT": "#8290a8"},
    }

    @classmethod
    def configure(cls, name: str | None, *, reduced_motion: bool = False) -> str:
        requested = str(name or "system").lower()
        # Flet does not expose a stable desktop system-theme query on every
        # platform; system starts in the safe high-contrast dark family.
        resolved = "dark" if requested == "system" else requested
        if resolved not in cls._PALETTES:
            resolved = "midnight"
        for key, value in cls._PALETTES[resolved].items():
            setattr(cls, key, value)
        cls.NAME = requested
        cls.REDUCED_MOTION = bool(reduced_motion)
        cls.GRADIENT = ft.LinearGradient(
            begin=ft.Alignment(-1.0, -1.0),
            end=ft.Alignment(1.0, 1.0),
            colors=[cls.BG, cls.SURFACE, cls.BG],
        )
        cls.RAIL_GRADIENT = ft.LinearGradient(
            begin=ft.Alignment(-1.0, -1.0),
            end=ft.Alignment(0.0, 1.0),
            colors=[cls.CARD_HI, cls.BG],
        )
        cls.MASTER_ON_GRADIENT = ft.LinearGradient(
            begin=ft.Alignment(-1.0, -1.0),
            end=ft.Alignment(1.0, 1.0),
            colors=[cls.CARD_HI, cls.SURFACE],
        )
        cls.SHADOW = [
            ft.BoxShadow(
                blur_radius=0 if cls.REDUCED_MOTION else 18,
                spread_radius=0,
                color=ft.Colors.with_opacity(0.16 if resolved == "light" else 0.32, "#061127"),
                offset=ft.Offset(0, 6),
            ),
            ft.BoxShadow(
                blur_radius=0 if cls.REDUCED_MOTION else 22,
                spread_radius=-4,
                color=ft.Colors.with_opacity(0.08 if resolved == "light" else 0.14, cls.PRIMARY),
                offset=ft.Offset(0, 8),
            ),
        ]
        cls.H1 = ft.TextStyle(size=26, weight=ft.FontWeight.BOLD, color=cls.TEXT)
        cls.H2 = ft.TextStyle(size=18, weight=ft.FontWeight.W_600, color=cls.TEXT)
        cls.BODY = ft.TextStyle(size=14, color=cls.TEXT)
        cls.LABEL = ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=cls.MUTED, letter_spacing=1.5)
        return resolved

    @classmethod
    def animation(cls, duration: int = 240, curve=ft.AnimationCurve.EASE_IN_OUT_CUBIC):
        """Premium, non-blocking UI motion; commands still execute immediately."""
        smooth_duration = max(200, int(duration))
        return ft.Animation(0 if cls.REDUCED_MOTION else smooth_duration, curve)

    @classmethod
    def press_ink(cls, strength: float = 0.28) -> str:
        """A restrained, theme-tinted Material wave for intentional taps.

        Using this instead of the platform default avoids the white flash that
        looked like a second selection state in the dark and ocean palettes.
        """
        return ft.Colors.with_opacity(0.0 if cls.REDUCED_MOTION else strength, cls.PRIMARY)

    @classmethod
    def flet_theme(cls) -> ft.Theme:
        """The common interaction language for every native Flet button.

        Containers that act as large controls opt into ``press_ink()``
        themselves. Native Text/Elevated/Outlined/Icon buttons share this
        theme, so their press wave has the same colour and relaxed duration.
        """
        duration = 0 if cls.REDUCED_MOTION else 320
        style = ft.ButtonStyle(
            animation_duration=duration,
            overlay_color=cls.press_ink(0.18),
        )
        return ft.Theme(
            color_scheme_seed=cls.PRIMARY,
            splash_color=cls.press_ink(0.30),
            highlight_color=cls.press_ink(0.16),
            hover_color=ft.Colors.with_opacity(0.05, cls.PRIMARY),
            focus_color=ft.Colors.with_opacity(0.10, cls.PRIMARY),
            button_theme=ft.ButtonTheme(style=style),
            outlined_button_theme=ft.OutlinedButtonTheme(style=style),
            text_button_theme=ft.TextButtonTheme(style=style),
            filled_button_theme=ft.FilledButtonTheme(style=style),
            icon_button_theme=ft.IconButtonTheme(style=style),
        )

    @staticmethod
    def GLOW(hex_color, strength: float = 0.32):
        """Localized lamp glow; it never changes a full selected surface."""
        return ft.BoxShadow(blur_radius=28, spread_radius=0, color=ft.Colors.with_opacity(strength, hex_color), offset=ft.Offset(0, 0))


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
