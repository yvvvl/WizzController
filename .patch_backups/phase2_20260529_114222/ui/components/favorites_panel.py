from __future__ import annotations

import flet as ft

from config.favorites_manager import FavoritesManager
from core import wiz_scenes
from ui.theme import Theme, mounted, supdate

COLOR_PRESETS = ["#ff0000", "#ff7f00", "#ffd000", "#00ff66", "#00b3ff", "#0040ff", "#7f00ff", "#ff00d4", "#ffffff"]


class FavoritesPanel(ft.Column):
    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.manager = FavoritesManager()
        self._build()

    def _build(self):
        header = ft.Row(
            [
                ft.Column([ft.Text("Favoritos", style=Theme.H1), ft.Text("Acciones rápidas: colores, blancos y escenas", color=Theme.MUTED, size=13)], spacing=2),
                ft.Container(expand=True),
                ft.OutlinedButton("Capturar estado", icon=ft.Icons.CONTROL_POINT_DUPLICATE_ROUNDED, on_click=self._capture_current),
                ft.ElevatedButton("Nuevo", icon=ft.Icons.ADD_ROUNDED, bgcolor=Theme.PRIMARY, color="white", on_click=lambda e: self._edit_dialog()),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.grid = ft.ResponsiveRow(spacing=12, run_spacing=12)
        self.controls = [header, self.grid]
        self._render()

    # ------------------------------------------------------------------ #
    def _render(self):
        self.manager = FavoritesManager()
        favs = self.manager.get_favorites()
        self.grid.controls.clear()
        if not favs:
            self.grid.controls.append(
                ft.Container(
                    col=12,
                    padding=40,
                    border_radius=Theme.R_MD,
                    bgcolor=Theme.CARD,
                    border=ft.Border.all(1, Theme.STROKE),
                    content=ft.Column(
                        [ft.Icon(ft.Icons.STAR_BORDER_ROUNDED, color=Theme.MUTED, size=36), ft.Text("Sin favoritos todavía.", color=Theme.MUTED, size=13)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                )
            )
        for fav in favs:
            self.grid.controls.append(self._card(fav))
        supdate(self.grid)

    def _card(self, fav: dict):
        ftype = fav.get("type")
        value = fav.get("value")
        color = self._preview_color(fav)
        icon = self._icon_for(ftype)
        sub = self._subtitle(fav)
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2},
            height=126,
            padding=14,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            shadow=Theme.SHADOW,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(content=ft.Icon(icon, color=color, size=20), width=38, height=38, border_radius=12, bgcolor=ft.Colors.with_opacity(0.16, color), alignment=ft.Alignment.CENTER),
                            ft.Container(expand=True),
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT_ROUNDED,
                                icon_color=Theme.MUTED,
                                items=[
                                    ft.PopupMenuItem(content="Editar", icon=ft.Icons.EDIT_ROUNDED, on_click=lambda e, x=fav: self._edit_dialog(x)),
                                    ft.PopupMenuItem(content="Eliminar", icon=ft.Icons.DELETE_OUTLINE_ROUNDED, on_click=lambda e, uid=fav.get("id"): self._delete(uid)),
                                ],
                            ),
                        ]
                    ),
                    ft.Container(expand=True),
                    ft.Text(fav.get("name") or "Favorito", color=Theme.TEXT, weight=ft.FontWeight.W_600, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(sub, color=Theme.MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ],
                spacing=4,
            ),
            on_click=lambda e, x=fav: self._apply(x),
            ink=True,
        )

    def _icon_for(self, ftype: str):
        return {"rgb": ft.Icons.PALETTE_ROUNDED, "white": ft.Icons.LIGHT_MODE_ROUNDED, "scene": ft.Icons.AUTO_AWESOME_ROUNDED}.get(ftype, ft.Icons.STAR_ROUNDED)

    def _preview_color(self, fav: dict) -> str:
        ftype = fav.get("type")
        value = fav.get("value")
        if ftype == "rgb" and str(value).startswith("#"):
            return str(value)
        if ftype == "white":
            try:
                k = int(value)
            except Exception:
                return "#ffffff"
            return "#ffc187" if k < 3300 else "#fff2df" if k < 5200 else "#cfe8ff"
        if ftype == "scene":
            sc = wiz_scenes.get(int(value)) if str(value).isdigit() else None
            return sc.color if sc else Theme.ACCENT
        return Theme.ACCENT

    def _subtitle(self, fav: dict) -> str:
        ftype = fav.get("type")
        value = fav.get("value")
        if ftype == "white":
            return f"Blanco · {value} K"
        if ftype == "scene":
            try:
                sc = wiz_scenes.get(int(value))
                return f"Escena · {sc.name if sc else value}"
            except Exception:
                return f"Escena · {value}"
        return f"RGB · {value}"

    # ------------------------------------------------------------------ #
    def _apply(self, fav: dict):
        self.wiz.apply_favorite(fav)

    def _delete(self, uid: str):
        self.manager.remove_favorite(uid)
        self._render()

    def _capture_current(self, e=None):
        st = self.wiz.get_state()
        if "sceneId" in st:
            sid = int(st.get("sceneId"))
            sc = wiz_scenes.get(sid)
            self.manager.add_favorite(sc.name if sc else f"Escena {sid}", "scene", sid, "AUTO_AWESOME")
        elif "temp" in st:
            k = int(st.get("temp"))
            self.manager.add_favorite(f"Blanco {k}K", "white", k, "LIGHT_MODE")
        elif all(k in st for k in ("r", "g", "b")):
            h = "#{:02x}{:02x}{:02x}".format(int(st["r"]), int(st["g"]), int(st["b"]))
            self.manager.add_favorite(f"Color {h}", "rgb", h, "PALETTE")
        else:
            self.manager.add_favorite("Blanco neutro", "white", 4000, "LIGHT_MODE")
        self._render()

    def _edit_dialog(self, fav: dict | None = None):
        if not mounted(self):
            return
        fav = fav or {}
        is_new = not fav.get("id")
        type_value = fav.get("type") or "rgb"
        value_default = fav.get("value") if fav else "#ff0000"

        name = ft.TextField(label="Nombre", value=fav.get("name") or "", autofocus=True, color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)
        type_dd = ft.Dropdown(
            label="Tipo",
            value=type_value,
            options=[ft.DropdownOption(key="rgb", text="Color RGB"), ft.DropdownOption(key="white", text="Blanco Kelvin"), ft.DropdownOption(key="scene", text="Escena")],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
        )
        value = ft.TextField(label="Valor", value=str(value_default), color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE, helper_text="RGB: #ff0000 · Blanco: 2700-6500 · Escena: 1-33")

        color_row = ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[
            ft.Container(width=30, height=30, border_radius=15, bgcolor=c, border=ft.Border.all(1, ft.Colors.with_opacity(0.4, "white")), on_click=lambda e, c=c: self._set_field(value, type_dd, "rgb", c)) for c in COLOR_PRESETS
        ])
        white_row = ft.Row(wrap=True, spacing=8, run_spacing=8, controls=[
            ft.OutlinedButton("2200K", on_click=lambda e: self._set_field(value, type_dd, "white", "2200")),
            ft.OutlinedButton("2700K", on_click=lambda e: self._set_field(value, type_dd, "white", "2700")),
            ft.OutlinedButton("4000K", on_click=lambda e: self._set_field(value, type_dd, "white", "4000")),
            ft.OutlinedButton("6500K", on_click=lambda e: self._set_field(value, type_dd, "white", "6500")),
        ])
        scene_dd = ft.Dropdown(
            label="Escena rápida",
            options=[ft.DropdownOption(key=str(s.id), text=f"{s.id} · {s.name}") for s in wiz_scenes.CATALOG.values()],
            color=Theme.TEXT,
            bgcolor=Theme.BG,
            border_color=Theme.STROKE,
            on_select=lambda e: self._set_field(value, type_dd, "scene", e.control.value),
        )

        def save(e):
            ftype = type_dd.value or "rgb"
            val = value.value or ("#ff0000" if ftype == "rgb" else "4000")
            icon = {"rgb": "PALETTE", "white": "LIGHT_MODE", "scene": "AUTO_AWESOME"}.get(ftype, "STAR")
            final_name = (name.value or "").strip() or f"Favorito {ftype}"
            if is_new:
                self.manager.add_favorite(final_name, ftype, val, icon)
            else:
                self.manager.update_favorite(fav["id"], final_name, ftype, val, icon)
            self.page.pop_dialog()
            self._render()

        dlg = ft.AlertDialog(
            title=ft.Text("Nuevo favorito" if is_new else "Editar favorito", color=Theme.TEXT),
            bgcolor=Theme.SURFACE,
            content=ft.Container(
                width=430,
                content=ft.Column([name, type_dd, value, ft.Text("COLORES", style=Theme.LABEL), color_row, ft.Text("BLANCOS", style=Theme.LABEL), white_row, scene_dd], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()), ft.ElevatedButton("Guardar", bgcolor=Theme.PRIMARY, color="white", on_click=save)],
        )
        self.page.show_dialog(dlg)

    def _set_field(self, value_field, type_dd, ftype, val):
        type_dd.value = ftype
        value_field.value = str(val)
        supdate(type_dd)
        supdate(value_field)

    def sync_state(self, state: dict):
        pass
