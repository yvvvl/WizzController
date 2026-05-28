import flet as ft
from ui.theme import Theme
from core import wiz_scenes


class ScenesPanel(ft.Column):
    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.selected_id: int | None = None
        self.speed = 100
        self._build()

    def _build(self):
        header = ft.Row(
            [
                ft.Column(
                    [ft.Text("Escenas", style=Theme.H1),
                     ft.Text("Modos de luz dinámicos y estáticos", color=Theme.MUTED, size=13)],
                    spacing=2,
                ),
            ]
        )

        # Control de velocidad (solo afecta escenas dinámicas)
        self.speed_label = ft.Text("Velocidad 100", size=12, color=Theme.MUTED)
        self.speed_slider = ft.Slider(
            min=20, max=200, value=100, divisions=18,
            active_color=Theme.ACCENT, thumb_color="white",
            on_change=self._on_speed, expand=True,
        )
        speed_card = ft.Container(
            content=ft.Row(
                [ft.Icon(ft.Icons.SPEED_ROUNDED, color=Theme.ACCENT, size=18),
                 self.speed_slider, self.speed_label],
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
            ),
            padding=ft.padding.symmetric(horizontal=18, vertical=8),
            bgcolor=Theme.CARD, border_radius=Theme.R_MD,
            border=ft.border.all(1, Theme.STROKE),
        )

        sections = []
        for group_name, ids in wiz_scenes.GROUPS.items():
            grid = ft.Row(wrap=True, spacing=12, run_spacing=12,
                          controls=[self._scene_card(sid) for sid in ids])
            sections.append(ft.Text(group_name.upper(), style=Theme.LABEL))
            sections.append(grid)

        self.controls = [header, speed_card, *sections]

    def _scene_card(self, scene_id):
        sc = wiz_scenes.get(scene_id)
        if not sc:
            return ft.Container()
        return ft.Container(
            key=f"sc{scene_id}",
            width=110, height=104, padding=12, border_radius=Theme.R_MD,
            bgcolor=Theme.CARD, border=ft.border.all(1, Theme.STROKE),
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(sc.glyph, size=22),
                        width=42, height=42, border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.16, sc.color),
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(sc.name, color=Theme.TEXT, size=12, weight="w600",
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text("dinámica" if sc.dynamic else "estática",
                            color=Theme.FAINT, size=9),
                ],
                spacing=6,
            ),
            on_click=lambda e, s=sc: self._activate(s), ink=True,
            animate=ft.Animation(140, "easeOut"),
            data=sc.color,
        )

    # ------------------------------------------------------------------ #
    def _activate(self, sc):
        if sc.dynamic:
            self.wiz.set_scene(sc.id, speed=int(self.speed))
        else:
            self.wiz.set_scene(sc.id)
        self.selected_id = sc.id
        self._highlight(sc)

    def _highlight(self, sc):
        # resalta la tarjeta activa recorriendo el árbol
        for ctrl in self.controls:
            if isinstance(ctrl, ft.Row):
                for card in ctrl.controls:
                    if isinstance(card, ft.Container) and getattr(card, "key", None):
                        active = card.key == f"sc{sc.id}"
                        card.border = ft.border.all(
                            2 if active else 1,
                            sc.color if active else Theme.STROKE)
                        card.bgcolor = Theme.CARD_HI if active else Theme.CARD
                        if card.page:
                            card.update()

    def _on_speed(self, e):
        self.speed = int(self.speed_slider.value)
        self.speed_label.value = f"Velocidad {self.speed}"
        if self.speed_label.page:
            self.speed_label.update()
        # re-aplicar en vivo si la escena activa es dinámica
        if self.selected_id is not None:
            sc = wiz_scenes.get(self.selected_id)
            if sc and sc.dynamic:
                self.wiz.set_scene(sc.id, speed=self.speed)
