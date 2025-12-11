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
    
    TEXT_MAIN = "#ffffff"
    TEXT_MUTED = "#94a3b8"

    # --- Gradientes de Fondo ---
    MAIN_GRADIENT = ft.LinearGradient(
        begin=ft.alignment.top_left,
        end=ft.alignment.bottom_right,
        colors=["#0f172a", "#020617"]
    )
    
    # --- Gradientes para Sliders (NUEVO) ---
    GRADIENT_HUE = ft.LinearGradient(
        colors=[
            "#ff0000", "#ffff00", "#00ff00", 
            "#00ffff", "#0000ff", "#ff00ff", "#ff0000"
        ],
        begin=ft.alignment.center_left,
        end=ft.alignment.center_right
    )
    
    GRADIENT_KELVIN = ft.LinearGradient(
        colors=["#ff8a12", "#ffc489", "#ffffff", "#cbebfd", "#9acbfb"],
        begin=ft.alignment.center_left,
        end=ft.alignment.center_right
    )

    # --- Estilos de Componentes ---
    CARD_BG = ft.Colors.with_opacity(0.5, "#1e293b")
    CARD_BORDER = ft.border.all(1, ft.Colors.with_opacity(0.2, "#475569"))
    CARD_RADIUS = 16
    
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

    # --- Textos ---
    H1 = ft.TextStyle(size=24, weight=ft.FontWeight.BOLD, color=TEXT_MAIN, font_family="Roboto")
    H2 = ft.TextStyle(size=18, weight=ft.FontWeight.W_600, color=TEXT_MAIN)
    LABEL = ft.TextStyle(size=12, weight=ft.FontWeight.W_500, color=TEXT_MUTED, letter_spacing=1)