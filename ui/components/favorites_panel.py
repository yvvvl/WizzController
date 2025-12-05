import flet as ft
from config.favorites_manager import FavoritesManager
from core.actions import get_action_func

class FavoritesPanel(ft.Container):
    def __init__(self, wiz_manager):
        super().__init__()
        self.wiz = wiz_manager
        self.fav_manager = FavoritesManager()
        
        self.expand = True
        self.padding = 20
        self.bgcolor = ft.Colors.TRANSPARENT
        
        self.grid = ft.GridView(
            runs_count=2, # 2 columnas de botones
            spacing=10,
            run_spacing=10,
            child_aspect_ratio=2.5, # Botones rectangulares anchos
        )
        
        self.content = ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.FLASH_ON, color="#facc15"), 
                ft.Text("ACCIONES RÁPIDAS", size=14, weight="bold", color="#facc15")
            ]),
            ft.Container(height=10),
            ft.Container(content=self.grid, expand=True)
        ])
        
        self._load_favorites()

    def _load_favorites(self):
        self.grid.controls.clear()
        favs = self.fav_manager.get_favorites()
        
        if not favs:
            self.grid.controls.append(ft.Text("No hay acciones configuradas", color="grey"))
        else:
            for item in favs:
                self.grid.controls.append(self._create_action_btn(item))
        
        if self.grid.page: self.grid.update()

    def _create_action_btn(self, item):
        label = item.get("label", "Acción")
        action_id = item.get("action")
        param = item.get("param")
        
        return ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, size=16, color="white"),
                ft.Text(label, size=12, weight="bold")
            ], alignment=ft.MainAxisAlignment.CENTER),
            style=ft.ButtonStyle(
                bgcolor="#334155",
                color="white",
                shape=ft.RoundedRectangleBorder(radius=8),
                elevation=2,
            ),
            on_click=lambda e: self._execute(action_id, param, label)
        )

    def _execute(self, action_id, param, label):
        func = get_action_func(action_id)
        if func:
            try:
                if action_id in ["color_custom", "set_color_custom"] and param:
                    func(self.wiz, param)
                else:
                    func(self.wiz)
                self.page.open(ft.SnackBar(ft.Text(f"Activado: {label}"), duration=1000, bgcolor="#22c55e"))
            except Exception as e:
                print(f"Error action: {e}")