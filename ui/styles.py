import flet as ft

class Theme:
    # --- PALETA DE COLORES (Dark Modern) ---
    BG_DARK = "#0f172a"      # Fondo principal (Slate 900)
    BG_CARD = "#1e293b"      # Fondo tarjetas (Slate 800)
    PRIMARY = "#3b82f6"      # Azul vibrante (Blue 500)
    SECONDARY = "#64748b"    # Gris azulado
    ACCENT  = "#8b5cf6"      # Violeta
    ERROR   = "#ef4444"      # Rojo alerta
    SUCCESS = "#22c55e"      # Verde éxito
    
    TEXT_MAIN = "#f1f5f9"    # Blanco casi puro
    TEXT_MUTED = "#94a3b8"   # Gris texto secundario

    # --- TIPOGRAFÍA ---
    H1 = ft.TextStyle(size=28, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)
    H2 = ft.TextStyle(size=22, weight=ft.FontWeight.W_600, color=TEXT_MAIN)
    
    BODY = ft.TextStyle(size=14, color=TEXT_MAIN)
    LABEL = ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED, letter_spacing=1.5)

    # --- ESTILOS VISUALES ---
    # CORRECCIÓN AQUÍ: Usamos ft.Alignment(-1, -1) en vez de .top_left
    MAIN_GRADIENT = ft.LinearGradient(
        begin=ft.Alignment(-1.0, -1.0),  # Arriba Izquierda
        end=ft.Alignment(1.0, 1.0),      # Abajo Derecha
        colors=[BG_DARK, "#1e1b4b"]
    )
    
    CARD_SHADOW = ft.BoxShadow(
        blur_radius=10,
        spread_radius=1,
        color=ft.Colors.with_opacity(0.3, "black"),
        offset=ft.Offset(0, 4)
    )