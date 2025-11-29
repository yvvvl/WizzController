"""
Mapeo de Escenas Nativas de WiZ a sus IDs.
Referencia: Documentación WiZ Pro y UDP.
"""

# Estructura para la UI: Categoría -> Lista de (Nombre, ID, Icono)
SCENES_DATA = {
    "Blancos & Funcional": [
        ("Blanco Cálido", 11, "☕"),
        ("Luz de Día", 12, "☀️"),
        ("Blanco Frío", 13, "❄️"),
        ("Luz Nocturna", 14, "🌙"),
        ("Acogedor", 6, "🛋️"),
        ("Relax", 16, "🧘"),
        ("Concentración", 15, "👓"),
        ("TV Time", 18, "📺"),
        ("Cultivo Plantas", 19, "🌱")
    ],
    "Dinámico - Ambiente": [
        ("Océano", 1, "🌊"),
        ("Romance", 2, "❤️"),
        ("Atardecer", 3, "🌅"),
        ("Fiesta", 4, "🎉"),
        ("Chimenea", 5, "🔥"),
        ("Bosque", 7, "🌲"),
        ("Colores Pastel", 8, "🎨"),
        ("Despertar", 9, "⏰"),
        ("A Dormir", 10, "🛏️"),
        ("Mojito", 21, "🍹"),
        ("Club", 22, "🕺"),
        ("Navidad", 23, "🎄"),
        ("Halloween", 24, "🎃"),
        ("Luz de Vela", 29, "🕯️"),
        ("Golden White", 30, "✨"),
        ("Pulse", 31, "💓"),
        ("Steampunk", 32, "⚙️")
    ]
}