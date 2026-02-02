import flet as ft
import logging
from config.favorites_manager import FavoritesManager
from ui.wiz_constants import STATIC_SCENES, DYNAMIC_SCENES, RICH_RAINBOW
from ui import flet_overlays as overlays
from ui.styles import Theme

class FavoritesPanel(ft.Container):
    def __init__(self, wiz_manager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.wiz = wiz_manager
        self.fav_manager = FavoritesManager()
        
        # Estilo del contenedor principal
        self.padding = 0
        self.bgcolor = ft.Colors.TRANSPARENT
        self.border = None
        self.border_radius = 0
        
        
        # Grid responsive
        self.grid = ft.GridView(
            expand=True,
            runs_count=5,
            max_extent=180,
            child_aspect_ratio=1.1,
            spacing=15,
            run_spacing=15,
        )
        
        self.content = ft.Column([
            self._build_header(),
            ft.Divider(height=20, color="transparent"),
            self.grid
        ])

    def did_mount(self):
        self._refresh_favorites()

    def _build_header(self):
        return ft.Row(
            [
                ft.Row([
                    ft.Icon(ft.icons.FLASH_ON_ROUNDED, color=Theme.WARNING, size=24),
                    ft.Text("Quick Actions", style=Theme.H2),
                ], spacing=10),
                
                ft.Container(expand=True),
                
                ft.IconButton(
                    icon=ft.icons.ADD_ROUNDED,
                    icon_color=Theme.TEXT_MAIN,
                    style=Theme.BUTTON_STYLE_ICON,
                    tooltip="Crear Nueva Acción",
                    on_click=lambda e: self._open_visual_editor(is_new=True)
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

    def _refresh_favorites(self):
        self.grid.controls.clear()
        favs = self.fav_manager.get_favorites()
        
        # Botón "Crear nuevo" como primera tarjeta
        self.grid.controls.append(self._build_add_card())

        for fav in favs:
            self.grid.controls.append(self._build_fav_card(fav))
        self.update()

    def _build_add_card(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.ADD_CIRCLE_OUTLINE_ROUNDED, color=Theme.TEXT_MUTED, size=32),
                    ft.Text("Crear", color=Theme.TEXT_MUTED, weight="bold")
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            bgcolor=ft.Colors.with_opacity(0.03, "white"),
            border=ft.border.all(1, ft.Colors.with_opacity(0.05, "white")),
            border_radius=Theme.CARD_RADIUS,
            ink=True,
            on_click=lambda e: self._open_visual_editor(is_new=True)
        )

    def _build_fav_card(self, fav):
        color = fav.get("value")
        # Detectar tipo para icono/color
        icon = ft.icons.LIGHTBULB_OUTLINE
        icon_color = Theme.TEXT_MAIN
        bg_indicator = "transparent"

        ftype = fav.get("type")
        if ftype == "scene":
            icon = ft.icons.AUTO_AWESOME
            icon_color = Theme.ACCENT
        elif ftype == "rgb":
            icon = ft.icons.PALETTE
            # Intentar usar el color real como punto
            bg_indicator = color if str(color).startswith("#") else Theme.PRIMARY
        
        return ft.Container(
            content=ft.Stack([
                # Background glow si es color
                ft.Container(
                    bgcolor=bg_indicator,
                    opacity=0.15,
                    border_radius=Theme.CARD_RADIUS,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(icon, color=icon_color),
                                    ft.Container(expand=True),
                                    # Menu contextual simplificado
                                    ft.PopupMenuButton(
                                        icon=ft.icons.MORE_VERT_ROUNDED,
                                        icon_color=Theme.TEXT_MUTED,
                                        items=[
                                            ft.PopupMenuItem(content="Editar", icon=ft.icons.EDIT),
                                            ft.PopupMenuItem(content="Eliminar", icon=ft.icons.DELETE_OUTLINE),
                                        ]
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            ft.Container(expand=True),
                            ft.Text(
                                fav.get("name", "Sin nombre"),
                                style=Theme.H3,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS
                            ),
                        ]
                    ),
                    padding=15,
                )
            ]),
            bgcolor=Theme.CARD_BG,
            border=Theme.CARD_BORDER,
            border_radius=Theme.CARD_RADIUS,
            shadow=Theme.SHADOW_CARD,
            ink=True,
            on_click=lambda _: self._activate_fav(fav)
        )

    def _activate_fav(self, fav):
        uid = fav["id"]
        self.fav_manager.apply_favorite(uid, self.wiz)
        if self.page:
            overlays.show_snackbar(self.page, f"Activado: {fav['name']}", bgcolor=Theme.SUCCESS)

    def _open_visual_editor(self, is_new=False, force_advanced=False):
        # TODO: Implementar Editor Modal con nuevo diseño
        pass
