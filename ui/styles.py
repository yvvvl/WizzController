import flet as ft

class Theme:
    # --- Paleta Base ---
    BG_DARK = "#0a0f1c"      
    BG_CARD = "#161b2c"      
    
    # Alias de compatibilidad
    BG_PANEL = BG_CARD 
    
    PRIMARY = "#3b82f6"      
    PRIMARY_GLOW = "#3b82f640" 
    
    ACCENT = "#06b6d4"       
    ERROR = "#ef4444"
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    
    TEXT_MAIN = "#ffffff"
    TEXT_MUTED = "#94a3b8"
    TEXT_SUBTLE = "#64748b"

    SHADOW = "#000000"

    # --- Alineaciones (compat con Flet 0.80.x) ---
    # Flet expone la clase Alignment, pero no siempre trae constantes como `ft.alignment.top_left`.
    ALIGN_TOP_LEFT = ft.Alignment(-1, -1)
    ALIGN_BOTTOM_RIGHT = ft.Alignment(1, 1)
    ALIGN_CENTER_LEFT = ft.Alignment(-1, 0)
    ALIGN_CENTER_RIGHT = ft.Alignment(1, 0)
    ALIGN_CENTER = ft.Alignment(0, 0)

    # --- Gradientes de Fondo ---
    MAIN_GRADIENT = ft.LinearGradient(
        begin=ALIGN_TOP_LEFT,
        end=ALIGN_BOTTOM_RIGHT,
        colors=["#0f172a", "#020617"]
    )

    SIDEBAR_GRADIENT = ft.LinearGradient(
        begin=ALIGN_TOP_LEFT,
        end=ALIGN_BOTTOM_RIGHT,
        colors=["#0b1220", "#0a0f1c"],
        stops=[0.0, 1.0],
    )
    
    # --- Gradientes para Sliders (NUEVO) ---
    GRADIENT_HUE = ft.LinearGradient(
        colors=[
            "#ff0000", "#ffff00", "#00ff00", 
            "#00ffff", "#0000ff", "#ff00ff", "#ff0000"
        ],
        begin=ALIGN_CENTER_LEFT,
        end=ALIGN_CENTER_RIGHT
    )
    
    GRADIENT_KELVIN = ft.LinearGradient(
        colors=["#ff8a12", "#ffc489", "#ffffff", "#cbebfd", "#9acbfb"],
        begin=ALIGN_CENTER_LEFT,
        end=ALIGN_CENTER_RIGHT
    )

    # --- Estilos de Componentes ---
    CARD_BG = ft.Colors.with_opacity(0.5, "#1e293b")
    CARD_BORDER = ft.border.all(1, ft.Colors.with_opacity(0.2, "#475569"))
    CARD_RADIUS = 16

    SHADOW_CARD = ft.BoxShadow(
        blur_radius=24,
        spread_radius=0,
        color=ft.Colors.with_opacity(0.25, "black"),
        offset=ft.Offset(0, 10),
    )

    INPUT_BG = ft.Colors.with_opacity(0.35, "#0b1220")
    INPUT_BORDER = ft.border.all(1, ft.Colors.with_opacity(0.14, "white"))
    
    GLASS_BORDER = CARD_BORDER
    border_radius = CARD_RADIUS

    # --- Botones ---
    BUTTON_STYLE_PRIMARY = ft.ButtonStyle(
        color="white",
        bgcolor=PRIMARY,
        overlay_color=PRIMARY_GLOW,
        shape=ft.RoundedRectangleBorder(radius=12),
        elevation=10,
        shadow_color=PRIMARY_GLOW,
        animation_duration=200
    )

    BUTTON_STYLE_SECONDARY = ft.ButtonStyle(
        color="white",
        bgcolor=ft.Colors.with_opacity(0.55, "#334155"),
        overlay_color=ft.Colors.with_opacity(0.12, "white"),
        shape=ft.RoundedRectangleBorder(radius=12),
        elevation=0,
        animation_duration=200,
    )

    BUTTON_STYLE_DANGER = ft.ButtonStyle(
        color="white",
        bgcolor=ERROR,
        overlay_color=ft.Colors.with_opacity(0.2, ERROR),
        shape=ft.RoundedRectangleBorder(radius=12),
        elevation=0,
        animation_duration=200,
    )

    BUTTON_STYLE_ICON = ft.ButtonStyle(
        color=TEXT_MAIN,
        bgcolor=ft.Colors.TRANSPARENT,
        overlay_color=ft.Colors.with_opacity(0.12, "white"),
        shape=ft.RoundedRectangleBorder(radius=12),
        elevation=0,
        animation_duration=150,
    )

    # --- Textos ---
    H1 = ft.TextStyle(size=24, weight=ft.FontWeight.BOLD, color=TEXT_MAIN, font_family="Roboto")
    H2 = ft.TextStyle(size=18, weight=ft.FontWeight.W_600, color=TEXT_MAIN)
    H3 = ft.TextStyle(size=14, weight=ft.FontWeight.W_600, color=TEXT_MAIN)
    BODY = ft.TextStyle(size=13, weight=ft.FontWeight.W_400, color=TEXT_MUTED)
    LABEL = ft.TextStyle(size=12, weight=ft.FontWeight.W_500, color=TEXT_MUTED, letter_spacing=1)
