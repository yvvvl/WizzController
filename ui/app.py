import flet as ft
from ui.styles import Theme
from ui.components.voice_dashboard import VoiceDashboard
from ui.components.home_panel import HomePanel
from ui.components.color_panel import ColorPanel
from ui.components.hotkeys_panel import HotkeysPanel
from config.hotkeys_manager import HotkeysManager

class WizzApp:
    def __init__(self, page: ft.Page, wiz_manager, voice_controller):
        self.page = page
        self.wiz = wiz_manager
        self.voice = voice_controller
        self.hk_manager = HotkeysManager(self.wiz)
        
        self.current_index = 0
        
        self._setup_page()
        self._init_components()
        self._build_layout()
        
    def _setup_page(self):
        self.page.title = "Wizz AI"
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = Theme.BG_DARK
        
        self.page.window.min_width = 950
        self.page.window.min_height = 700
        self.page.window.width = 1100
        self.page.window.height = 800
        
        self.page.fonts = {
            "Roboto": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"
        }

    def _init_components(self):
        self.home_panel = HomePanel(self.wiz)
        self.voice_dashboard = VoiceDashboard(self.voice)
        self.color_panel = ColorPanel(self.wiz, on_bg_change=self._update_bg_accent)
        self.hotkeys_panel = HotkeysPanel(self.page, self.hk_manager)

        self.destinations = [
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD_ROUNDED, selected_icon=ft.Icons.DASHBOARD, label="Control"),
            ft.NavigationRailDestination(icon=ft.Icons.COLOR_LENS_OUTLINED, selected_icon=ft.Icons.COLOR_LENS, label="Estudio"),
            ft.NavigationRailDestination(icon=ft.Icons.RECORD_VOICE_OVER_OUTLINED, selected_icon=ft.Icons.RECORD_VOICE_OVER, label="Voz AI"),
            ft.NavigationRailDestination(icon=ft.Icons.KEYBOARD_OUTLINED, selected_icon=ft.Icons.KEYBOARD, label="Atajos"),
        ]

        # Barra Lateral (Desktop)
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=180,
            bgcolor=ft.Colors.with_opacity(0.02, "white"),
            group_alignment=-0.9,
            destinations=self.destinations,
            on_change=self._on_nav_change
        )

        # Barra Inferior (Mobile/Compact)
        self.nav_bar = ft.NavigationBar(
            selected_index=0,
            destinations=[
                ft.NavigationBarDestination(
                    icon=d.icon, 
                    selected_icon=getattr(d, "selected_icon", d.icon), 
                    label=d.label
                ) 
                for d in self.destinations
            ],
            on_change=self._on_nav_change,
            bgcolor="#111827",
            height=70,
            visible=False 
        )

    def _build_layout(self):
        self.content_area = ft.Container(
            content=self.home_panel,
            expand=True,
            padding=ft.padding.all(20),
            gradient=Theme.MAIN_GRADIENT,
            alignment=ft.alignment.top_left
        )

        self.sidebar_container = ft.Container(
            content=self.nav_rail,
            visible=True,
            border=ft.border.only(right=ft.border.BorderSide(1, "#262626")),
        )

        self.layout = ft.Row(
            controls=[self.sidebar_container, self.content_area],
            expand=True,
            spacing=0
        )
        
        self.page.add(self.layout)
        self.page.on_resized = self.handle_resize
        self.handle_resize(None)

    def _on_nav_change(self, e):
        idx = e.control.selected_index
        self.current_index = idx
        
        self.nav_rail.selected_index = idx
        self.nav_bar.selected_index = idx
        
        self.content_area.content = self._get_view_for_index(idx)
        self.page.update()

    def _get_view_for_index(self, index):
        views = [self.home_panel, self.color_panel, self.voice_dashboard, self.hotkeys_panel]
        if 0 <= index < len(views):
            return views[index]
        return ft.Container(content=ft.Text("En construcción", color="white"))

    def _update_bg_accent(self, color):
        if not color: return
        try:
            accent_color = ft.Colors.with_opacity(0.1, color)
        except:
            accent_color = "#1A" + color.lstrip("#")
            
        self.content_area.gradient = ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[Theme.BG_DARK, accent_color, Theme.BG_DARK],
        )
        self.content_area.update()

    def handle_resize(self, e):
        width = self.page.window.width
        if width < 800:
            self.sidebar_container.visible = False
            self.nav_bar.visible = True
            self.page.navigation_bar = self.nav_bar
            self.page.padding = 0
        else:
            self.sidebar_container.visible = True
            self.nav_bar.visible = False
            self.page.navigation_bar = None
            self.page.padding = 0
        self.page.update()
        
    def update_ui(self, state):
        if isinstance(self.content_area.content, HomePanel):
            self.content_area.content.sync_state(state)