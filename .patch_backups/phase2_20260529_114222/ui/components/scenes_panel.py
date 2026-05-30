from __future__ import annotations

import time

import flet as ft

from core import wiz_scenes
from ui.theme import Theme, supdate

EO = ft.AnimationCurve.EASE_OUT


class ScenesPanel(ft.Column):
    def __init__(self, wiz):
        super().__init__(scroll=ft.ScrollMode.AUTO, spacing=18, expand=True)
        self.wiz = wiz
        self.selected_id = None
        self.speed = 100
        self._last_speed_send = 0.0
        self._build()

    def _build(self):
        header = ft.Row([
            ft.Column([ft.Text("Escenas", style=Theme.H1), ft.Text("Modos de luz dinámicos y estáticos", color=Theme.MUTED, size=13)], spacing=2),
        ])

        self.speed_label = ft.Text("Velocidad 100", size=12, color=Theme.MUTED)
        self.speed_slider = ft.Slider(
            min=20,
            max=200,
            value=100,
            divisions=18,
            active_color=Theme.ACCENT,
            thumb_color="white",
            on_change=self._on_speed,
            on_change_end=self._on_speed_end,
            expand=True,
        )
        speed_card = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.SPEED_ROUNDED, color=Theme.ACCENT, size=18),
                    self.speed_slider,
                    self.speed_label,
                    ft.TextButton("Restaurar", icon=ft.Icons.RESTART_ALT_ROUNDED, style=ft.ButtonStyle(color=Theme.MUTED), on_click=self._reset_speed),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
                run_spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=18, vertical=8),
            bgcolor=Theme.CARD,
            border_radius=Theme.R_MD,
            border=ft.Border.all(1, Theme.STROKE),
        )

        sections = []
        for group_name, ids in wiz_scenes.GROUPS.items():
            grid = ft.ResponsiveRow(spacing=12, run_spacing=12, controls=[self._scene_card(sid) for sid in ids])
            sections.append(ft.Text(group_name.upper(), style=Theme.LABEL))
            sections.append(grid)

        self.controls = [header, speed_card, *sections]

    def _scene_card(self, scene_id):
        sc = wiz_scenes.get(scene_id)
        if not sc:
            return ft.Container()
        return ft.Container(
            key=f"sc{scene_id}",
            col={"xs": 6, "sm": 4, "md": 3, "lg": 2},
            height=104,
            padding=12,
            border_radius=Theme.R_MD,
            bgcolor=Theme.CARD,
            border=ft.Border.all(1, Theme.STROKE),
            content=ft.Column(
                [
                    ft.Container(content=ft.Text(sc.glyph, size=22), width=42, height=42, border_radius=12, bgcolor=ft.Colors.with_opacity(0.16, sc.color), alignment=ft.Alignment.CENTER),
                    ft.Text(sc.name, color=Theme.TEXT, size=12, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text("dinámica" if sc.dynamic else "estática", color=Theme.FAINT, size=9),
                ],
                spacing=6,
            ),
            on_click=lambda e, s=sc: self._activate(s),
            ink=True,
            animate=ft.Animation(120, EO),
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
        for ctrl in self.controls:
            if isinstance(ctrl, ft.ResponsiveRow):
                for card in ctrl.controls:
                    if isinstance(card, ft.Container) and getattr(card, "key", None):
                        active = card.key == f"sc{sc.id}"
                        card.border = ft.Border.all(2 if active else 1, sc.color if active else Theme.STROKE)
                        card.bgcolor = Theme.CARD_HI if active else Theme.CARD
                        supdate(card)

    def _send_speed(self, force=False):
        if self.selected_id is None:
            return
        now = time.monotonic()
        if not force and now - self._last_speed_send < 0.08:
            return
        self._last_speed_send = now
        sc = wiz_scenes.get(self.selected_id)
        if sc and sc.dynamic:
            self.wiz.set_scene(sc.id, speed=self.speed)

    def _on_speed(self, e):
        self.speed = int(self.speed_slider.value)
        self.speed_label.value = f"Velocidad {self.speed}"
        supdate(self.speed_label)
        self._send_speed(force=False)

    def _on_speed_end(self, e):
        self.speed = int(self.speed_slider.value)
        self.speed_label.value = f"Velocidad {self.speed}"
        supdate(self.speed_label)
        self._send_speed(force=True)

    def _reset_speed(self, e=None):
        self.speed = 100
        self.speed_slider.value = 100
        self.speed_label.value = "Velocidad 100"
        supdate(self.speed_slider)
        supdate(self.speed_label)
        self._send_speed(force=True)
