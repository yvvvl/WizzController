from __future__ import annotations

import flet as ft
from config.favorites_manager import FavoritesManager
from ui.theme import Theme, mounted, supdate


def _parse_rgb(hex_color: str) -> tuple[int, int, int] | None:
    h = str(hex_color or "").strip().lstrip("#")
    if len(h) != 6:
        return None
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


class FavoritesPanel(ft.Column):
    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.manager = FavoritesManager()
        self._build()

    def _build(self):
        self.manager.seed_defaults()
        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Favoritos", style=Theme.H1),
                        ft.Text("Colores, blancos, escenas y brillo guardados", color=Theme.MUTED, size=13),
                    ],
                    spacing=2,
                ),
                ft.Container(expand=True),
                ft.OutlinedButton(
                    "Nuevo",
                    icon=ft.Icons.ADD_ROUNDED,
                    style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
                    on_click=lambda e: self._new_dialog(),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.grid = ft.Row(wrap=True, spacing=12, run_spacing=12)
        self.controls = [header, self.grid]
        self._render()

    def _render(self):
        self.manager = FavoritesManager()
        favs = self.manager.get_favorites()
        self.grid.controls.clear()
        if not favs:
            self.grid.controls.append(
                ft.Container(
                    width=420,
                    padding=32,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.STAR_BORDER_ROUNDED, color=Theme.MUTED, size=38),
                            ft.Text("Aún no hay favoritos.", color=Theme.MUTED),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        else:
            for fav in favs:
                self.grid.controls.append(self._card(fav))
        supdate(self.grid)

    def _card(self, fav: dict):
        ftype = fav.get("type")
        value = fav.get("value")
        color = Theme.PRIMARY
        icon = ft.Icons.STAR_ROUNDED
        subtitle = str(value)
        if ftype == "rgb":
            color = str(value)
            icon = ft.Icons.PALETTE_ROUNDED
            subtitle = str(value).upper()
        elif ftype == "white":
            color = "#fbbf24"
            icon = ft.Icons.LIGHT_MODE_ROUNDED
            subtitle = f"{value}K"
        elif ftype == "scene":
            color = "#8b5cf6"
            icon = ft.Icons.AUTO_AWESOME_ROUNDED
            if isinstance(value, dict):
                subtitle = f"Escena {value.get('sceneId')} · vel {value.get('speed', '—')}"
            else:
                subtitle = f"Escena {value}"
        elif ftype == "brightness":
            color = Theme.ACCENT
            icon = ft.Icons.BRIGHTNESS_6_ROUNDED
            subtitle = f"{value}%"

        return ft.Container(
            width=176,
            padding=14,
            height=128,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
            on_click=lambda e, f=fav: self._apply(f),
            ink=True,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(icon, color="white", size=20),
                                width=40,
                                height=40,
                                border_radius=12,
                                bgcolor=color,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Container(expand=True),
                            ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Theme.PRIMARY, tooltip="Editar", icon_size=18, on_click=lambda e, f=fav: self._edit_dialog(f)),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, tooltip="Borrar", icon_size=18, on_click=lambda e, uid=fav.get("id"): self._delete(uid)),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(fav.get("name", "Favorito"), color=Theme.TEXT, weight=ft.FontWeight.W_600, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(subtitle, color=Theme.MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=2,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )

    def _apply(self, fav: dict):
        ftype = fav.get("type")
        value = fav.get("value")
        if hasattr(self.wiz, "apply_favorite"):
            self.wiz.apply_favorite(fav)
            return
        if ftype == "rgb":
            rgb = _parse_rgb(value)
            if rgb:
                self.wiz.set_rgb(*rgb)
        elif ftype == "white":
            self.wiz.set_white(int(value))
        elif ftype == "brightness":
            self.wiz.set_brightness(int(value))
        elif ftype == "scene":
            if isinstance(value, dict):
                self.wiz.set_scene(int(value.get("sceneId", 1)), value.get("speed"))
            else:
                self.wiz.set_scene(int(value))

    def _delete(self, uid: str):
        self.manager.remove_favorite(uid)
        self._render()

    def _new_dialog(self):
        self._favorite_dialog()

    def _edit_dialog(self, fav: dict):
        self._favorite_dialog(fav)

    def _favorite_dialog(self, fav: dict | None = None):
        if not mounted(self):
            return
        editing = fav is not None
        fav = fav or {"name": "Nuevo favorito", "type": "rgb", "value": "#ff0000"}
        value_obj = fav.get("value")
        if isinstance(value_obj, dict):
            raw_value = str(value_obj.get("sceneId", 18))
        else:
            raw_value = str(value_obj)

        name = ft.TextField(label="Nombre", value=fav.get("name", "Nuevo favorito"), color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        kind = ft.Dropdown(
            label="Tipo",
            value=fav.get("type", "rgb"),
            options=[
                ft.DropdownOption(key="rgb", text="Color HEX"),
                ft.DropdownOption(key="white", text="Blanco Kelvin"),
                ft.DropdownOption(key="scene", text="Escena"),
                ft.DropdownOption(key="brightness", text="Brillo"),
            ],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
        value = ft.TextField(label="Valor", value=raw_value, hint_text="#ff0000 / 4000 / 18 / 80", color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        def save(e):
            raw = (value.value or "").strip()
            ftype = kind.value or "rgb"
            val: object = raw
            try:
                if ftype == "white":
                    val = max(1000, min(10000, int(raw)))
                elif ftype == "brightness":
                    val = max(10, min(100, int(raw)))
                elif ftype == "scene":
                    val = {"sceneId": int(raw), "speed": 100}
                elif ftype == "rgb":
                    val = raw if raw.startswith("#") else "#" + raw
            except ValueError:
                return

            if editing:
                self.manager.update_favorite(fav.get("id"), name.value, ftype, val, fav.get("icon", "STAR"))
            else:
                self.manager.add_favorite(name.value, ftype, val)
            self.page.pop_dialog()
            self._render()

        dlg = ft.AlertDialog(
            title=ft.Text("Editar favorito" if editing else "Nuevo favorito", color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=ft.Column([name, kind, value], tight=True, spacing=10, width=360),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton("Guardar", bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    def sync_state(self, state: dict):
        # No necesita refrescar en cada tick de slider; evita CPU extra.
        pass
