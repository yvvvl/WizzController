import flet as ft
from ui.theme import Theme, mounted, supdate


class SettingsPanel(ft.Column):
    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self):
        self.btn_scan = ft.ElevatedButton(
            "Buscar ampolletas", icon=ft.Icons.WIFI_FIND_ROUNDED,
            bgcolor=Theme.PRIMARY, color="white", on_click=self._scan,
        )
        self.btn_add = ft.OutlinedButton(
            "Agregar por IP", icon=ft.Icons.ADD_ROUNDED,
            style=ft.ButtonStyle(color=Theme.TEXT, side=ft.BorderSide(1, Theme.STROKE)),
            on_click=lambda e: self._add_dialog(),
        )
        self.scan_ring = ft.ProgressRing(width=18, height=18, stroke_width=2,
                                         color=Theme.PRIMARY, visible=False)

        header = ft.Row(
            [
                ft.Column([ft.Text("Ajustes", style=Theme.H1),
                           ft.Text("Gestión de ampolletas en tu red", color=Theme.MUTED, size=13)],
                          spacing=2),
                ft.Container(expand=True),
                self.scan_ring, self.btn_add, self.btn_scan,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.list_view = ft.Column(spacing=12)
        self.controls = [header, ft.Text("AMPOLLETAS", style=Theme.LABEL), self.list_view]
        self._render_list()

    # ------------------------------------------------------------------ #
    def _render_list(self):
        self.list_view.controls.clear()
        bulbs = self.wiz.get_bulbs_detailed()

        if not bulbs:
            self.list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        [ft.Icon(ft.Icons.LIGHTBULB_OUTLINE_ROUNDED, color=Theme.MUTED, size=36),
                         ft.Text("No hay ampolletas. Pulsa «Buscar».", color=Theme.MUTED, size=13)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    alignment=ft.Alignment.CENTER, padding=40,
                )
            )
        else:
            for b in bulbs:
                self.list_view.controls.append(self._bulb_card(b))

        supdate(self.list_view)

    def _bulb_card(self, b):
        online = b["online"]
        return ft.Container(
            padding=16, border_radius=Theme.R_MD, bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(ft.Icons.LIGHTBULB_ROUNDED,
                                        color=Theme.SUCCESS if online else Theme.MUTED, size=22),
                        width=44, height=44, border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.14, Theme.SUCCESS if online else Theme.MUTED),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(b["name"], color=Theme.TEXT, weight=ft.FontWeight.W_600, size=15),
                            ft.Text(f"{b['ip']}   ·   {b['mac'] or 'sin MAC'}", color=Theme.MUTED, size=11),
                            ft.Text(("● en línea · " + b["label"]) if online else "○ sin respuesta",
                                    color=Theme.SUCCESS if online else Theme.FAINT, size=11),
                        ], spacing=2, expand=True,
                    ),
                    ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Theme.PRIMARY, icon_size=20,
                                  tooltip="Renombrar", on_click=lambda e, x=b: self._rename_dialog(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Theme.ERROR, icon_size=20,
                                  tooltip="Quitar", on_click=lambda e, ip=b["ip"]: self._remove(ip)),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
            ),
        )

    # ------------------------------------------------------------------ #
    def _scan(self, e):
        self.scan_ring.visible = True
        self.btn_scan.disabled = True
        supdate(self)
        self.wiz.rescan()

    def _remove(self, ip):
        self.wiz.remove_bulb(ip)
        self._render_list()

    def _rename_dialog(self, b):
        if not mounted(self):
            return
        field = ft.TextField(label="Nombre", value=b["name"], autofocus=True,
                             color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        def save(e):
            self.wiz.rename_bulb(b["ip"], (field.value or "").strip() or b["ip"])
            self.page.pop_dialog()
            self._render_list()

        dlg = ft.AlertDialog(
            title=ft.Text("Renombrar ampolleta", color=Theme.TEXT),
            bgcolor=Theme.SURFACE, content=field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton("Guardar", bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    def _add_dialog(self):
        if not mounted(self):
            return
        field = ft.TextField(label="Dirección IP", hint_text="192.168.1.20", autofocus=True,
                             color=Theme.TEXT, bgcolor=Theme.BG, border_color=Theme.STROKE)

        def save(e):
            ip = (field.value or "").strip()
            if ip:
                self.wiz.add_bulb_manual(ip)
                self.page.pop_dialog()
                self._render_list()

        dlg = ft.AlertDialog(
            title=ft.Text("Agregar por IP", color=Theme.TEXT),
            bgcolor=Theme.SURFACE, content=field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.ElevatedButton("Agregar", bgcolor=Theme.PRIMARY, color="white", on_click=save),
            ],
        )
        self.page.show_dialog(dlg)

    # ------------------------------------------------------------------ #
    def sync_state(self, state: dict):
        if not mounted(self):
            return
        self.scan_ring.visible = False
        self.btn_scan.disabled = False
        self._render_list()
        supdate(self)
