import flet as ft
import keyboard
import threading
import time
import logging
from ui.styles import Theme
from ui.wiz_constants import ALL_SCENES_MAP
from config.favorites_manager import FavoritesManager

class HotkeysPanel(ft.Container):
    def __init__(self, page: ft.Page, hotkeys_manager):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.page_ref = page
        self.manager = hotkeys_manager
        self.fav_manager = FavoritesManager()
        self.expand = True
        self.padding = 30
        self.recording_id = None
        self._current_tab_index = 0
        
        # --- HEADER ---
        header = ft.Row([
            ft.Icon(ft.icons.KEYBOARD_ROUNDED, color=Theme.PRIMARY, size=32),
            ft.Column([
                ft.Text("Atajos de Teclado", style=Theme.H1),
                ft.Text("Automatiza acciones con una sola tecla", style=Theme.BODY, size=12),
            ], spacing=2)
        ], alignment=ft.MainAxisAlignment.START)

        # --- Selector de pestañas (Flet 0.80.x compatible) ---
        self._tab_selector = ft.SegmentedButton(
            segments=[
                ft.Segment("0", icon=ft.icons.SETTINGS_ETHERNET_ROUNDED, label="General"),
                ft.Segment("1", icon=ft.icons.PALETTE_OUTLINED, label="Colores"),
                ft.Segment("2", icon=ft.icons.AUTO_AWESOME_OUTLINED, label="Escenas"),
                ft.Segment("3", icon=ft.icons.STAR_BORDER_ROUNDED, label="Favoritos"),
            ],
            selected=["0"],
            allow_multiple_selection=False,
            allow_empty_selection=False,
            style=getattr(Theme, "BUTTON_STYLE_SECONDARY", None),
            on_change=self._on_tab_change,
        )
        
        self.tabs_content = ft.Column(expand=True, scroll="hidden") # Content area dynamic
        
        self.content = ft.Column([
            header,
            ft.Container(height=20),
            self._tab_selector,
            ft.Divider(color=ft.Colors.with_opacity(0.1, "white"), height=1),
            ft.Container(height=10),
            self.tabs_content
        ], expand=True)

        self._refresh_tab_content(0)

    def _on_tab_change(self, e):
        try:
            selected = list(getattr(e.control, "selected", []) or [])
            idx = int(selected[0]) if selected else 0
        except Exception:
            idx = 0

        self._current_tab_index = idx
        self._refresh_tab_content(idx)

    def _refresh_tab_content(self, index):
        self.tabs_content.controls.clear()
        
        controls = []
        if index == 0: # General
            acts = [("Encender", "on", ft.icons.POWER_SETTINGS_NEW), 
                    ("Apagar", "off", ft.icons.POWER_OFF), 
                    ("Alternar", "toggle", ft.icons.SWAP_HORIZ),
                    ("Brillo +", "bri_up", ft.icons.BRIGHTNESS_HIGH), 
                    ("Brillo -", "bri_down", ft.icons.BRIGHTNESS_LOW)]
            controls = self._build_rows(acts)
            
        elif index == 1: # Colores
            acts = [("Rojo", "color_red", ft.icons.CIRCLE, "red"), 
                    ("Verde", "color_green", ft.icons.CIRCLE, "green"), 
                    ("Azul", "color_blue", ft.icons.CIRCLE, "blue")]
            controls = self._build_rows(acts)
            
        elif index == 2: # Escenas
            acts = [(f"{d['name']}", f"scene_{i}", ft.icons.AUTO_AWESOME) for i, d in ALL_SCENES_MAP.items()]
            controls = self._build_rows(acts)
            
        elif index == 3: # Favoritos
            favs = self.fav_manager.get_favorites()
            acts = []
            for fav in favs:
                icon = ft.icons.STAR_ROUNDED
                acts.append((fav["name"], f"fav_{fav['id']}", icon))
            controls = self._build_rows(acts)

        self.tabs_content.controls = controls
        try:
            # En Flet 0.80, llamar update() antes de montar el control rompe.
            if self.page_ref:
                self.tabs_content.update()
        except Exception:
            pass

    def _build_rows(self, acts):
        return [self._row(item) for item in acts]

    def _row(self, item):
        # Unpack
        label = item[0]
        aid = item[1]
        icon = item[2]
        icon_color = item[3] if len(item) > 3 else Theme.TEXT_MUTED
        
        current_key = self.manager.get("hotkeys", {}).get(aid)
        is_rec = (self.recording_id == aid)
        
        # Determine status visuals
        if is_rec:
            status_text = "Presiona una tecla..."
            status_color = Theme.ACCENT
            bg_color = ft.Colors.with_opacity(0.1, Theme.ACCENT)
            border_color = Theme.ACCENT
        elif current_key:
            status_text = current_key.upper()
            status_color = Theme.TEXT_MAIN
            bg_color = Theme.CARD_BG
            border_color = Theme.CARD_BORDER
        else:
            status_text = "Sin asignar"
            status_color = Theme.TEXT_MUTED
            bg_color = Theme.CARD_BG
            border_color = "transparent"

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=20, vertical=15),
            bgcolor=bg_color,
            border=ft.border.all(1, border_color) if is_rec else Theme.CARD_BORDER,
            border_radius=Theme.CARD_RADIUS,
            content=ft.Row([
                ft.Row([
                    ft.Icon(icon, color=icon_color),
                    ft.Text(label, style=Theme.H3),
                ]),
                
                ft.Container(expand=True),
                
                # Keycap visualization
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.KEYBOARD_ALT_OUTLINED if not is_rec else ft.icons.RADIO_BUTTON_CHECKED, 
                               size=16, color=status_color),
                        ft.Text(status_text, color=status_color, weight="bold", size=12)
                    ], spacing=5),
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    bgcolor=ft.Colors.with_opacity(0.1, status_color) if current_key or is_rec else "transparent",
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.2, status_color)) if current_key else None
                )
            ]),
            on_click=lambda _: self._on_item_click(aid),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            ink=True
        )

    def _on_item_click(self, aid):
        if self.recording_id == aid:
            # Cancel
            self.recording_id = None
            self._refresh_current_view()
            return
            
        self.recording_id = aid
        self._refresh_current_view()
        
        # Start listener thread
        threading.Thread(target=self._record_key, args=(aid,), daemon=True).start()

    def _refresh_current_view(self):
        # Refresh current tab blindly
        self._refresh_tab_content(int(self._current_tab_index))

    def _record_key(self, aid):
        time.sleep(0.2)
        try:
            key_event = keyboard.read_event(suppress=True)
            if key_event.event_type == keyboard.KEY_DOWN:
                key_name = key_event.name
                if key_name == 'esc':
                    # Cancel
                    pass
                elif key_name == 'backspace':
                    # Delete
                    self.manager.set_hotkey(aid, None)
                else:
                    # Set
                    self.manager.set_hotkey(aid, key_name)
                    
        except Exception as e:
            self.logger.error(f"Error recording key: {e}")
        finally:
            self.recording_id = None
            if self.page_ref:
                self.page_ref.run_task(self._update_ui_safe)

    async def _update_ui_safe(self, *args):
        try:
            self._refresh_current_view()
        except:
            pass
