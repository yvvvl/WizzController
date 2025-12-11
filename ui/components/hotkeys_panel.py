import flet as ft
import keyboard
import threading
import time
from ui.styles import Theme
from ui.wiz_constants import ALL_SCENES_MAP
from config.favorites_manager import FavoritesManager

class HotkeysPanel(ft.Container):
    def __init__(self, page: ft.Page, hotkeys_manager):
        super().__init__()
        self.page_ref = page
        self.manager = hotkeys_manager
        self.fav_manager = FavoritesManager()
        self.expand = True
        self.padding = 30
        self.recording_id = None
        
        self.header = ft.Column([
            ft.Text("CONFIGURACIÓN DE ATAJOS", style=Theme.H1),
            ft.Text("Haz clic para asignar. ESC para cancelar.", style=Theme.LABEL),
            ft.Divider(height=10, color="transparent"),
        ])

        self.tabs = ft.Tabs(
            selected_index=0, 
            indicator_color=Theme.ACCENT, 
            divider_color="transparent", 
            expand=True,
            label_color="white",
            unselected_label_color="grey"
        )
        self.content = ft.Column([self.header, self.tabs], expand=True)
        self._refresh_tabs(initial=True)

    def _refresh_tabs(self, initial=False):
        gen_acts = [("Encender", "on"), ("Apagar", "off"), ("Alternar", "toggle"), ("Brillo +", "bri_up"), ("Brillo -", "bri_down")]
        col_acts = [("🔴 Rojo", "color_red"), ("🟢 Verde", "color_green"), ("🔵 Azul", "color_blue")]
        scene_acts = [(f"✨ {d['name']}", f"scene_{i}") for i, d in ALL_SCENES_MAP.items()]

        fav_rgb, fav_white = [], []
        for fav in self.fav_manager.get_favorites():
            name, uid, ftype, val = fav["name"], fav["id"], fav["type"], fav["value"]
            aid = f"fav_{uid}"
            if ftype == "rgb": fav_rgb.append((name, aid, val if str(val).startswith("#") else "#ffffff"))
            elif ftype == "white": fav_white.append((name, aid, "#ffffff"))

        self.tabs.tabs = [
            ft.Tab(text="GENERAL", content=self._list(self._rows(gen_acts))),
            ft.Tab(text="COLORES", content=self._list(self._rows(col_acts))),
            ft.Tab(text="ESCENAS", content=self._list(self._rows(scene_acts))),
            ft.Tab(text="FAVORITOS", content=self._list(self._fav_rows(fav_rgb, fav_white))),
        ]
        if not initial and self.page_ref: self.update()

    def _list(self, controls): return ft.ListView(controls=controls, spacing=5, padding=10, expand=True)
    def _rows(self, acts): return [self._row(l, i) for l, i in acts]

    def _fav_rows(self, rgb, white):
        rows = []
        if rgb:
            rows.append(ft.Text("COLORES", color=Theme.ACCENT, weight="bold"))
            rows.extend([self._row(n, i, c) for n, i, c in rgb])
        if white:
            rows.append(ft.Text("BLANCOS", color="orange", weight="bold"))
            rows.extend([self._row(n, i, c) for n, i, c in white])
        return rows

    def _row(self, label, aid, color_preview=None):
        key = self.manager.get("hotkeys", {}).get(aid)
        is_rec = (self.recording_id == aid)
        
        btn_txt = "GRABANDO..." if is_rec else (key.upper() if key else "ASIGNAR")
        btn_col = Theme.ERROR if is_rec else (Theme.ACCENT if key else "grey")
        btn_bg = ft.Colors.with_opacity(0.1, Theme.ERROR) if is_rec else (ft.Colors.with_opacity(0.1, Theme.ACCENT) if key else ft.Colors.with_opacity(0.1, "grey"))

        left = [ft.Text(label, size=14, color="white")]
        if color_preview: left.insert(0, ft.Container(width=16, height=16, bgcolor=color_preview, border_radius=4))

        return ft.Container(
            bgcolor=Theme.BG_CARD, padding=10, border_radius=8,
            content=ft.Row([
                ft.Row(left, spacing=10),
                ft.Container(
                    content=ft.Row([ft.Icon(ft.Icons.KEYBOARD, size=14, color=btn_col), ft.Text(btn_txt, weight="bold", color=btn_col, size=12)], spacing=5),
                    bgcolor=btn_bg, padding=ft.padding.symmetric(horizontal=12, vertical=8), border_radius=6,
                    on_click=lambda e, x=aid: self._start_rec(x)
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

    def _start_rec(self, aid):
        self.recording_id = aid
        self._refresh_tabs()
        threading.Thread(target=self._rec_thread, args=(aid,), daemon=True).start()

    def _rec_thread(self, aid):
        try:
            time.sleep(0.2)
            k = keyboard.read_hotkey(suppress=False)
            if k != "esc": self.manager.set_hotkey(aid, k)
        except: pass
        finally:
            self.recording_id = None
            try: self.page_ref.run_task(self._finish_rec)
            except: pass

    async def _finish_rec(self, *args):
        self._refresh_tabs()
        self.page_ref.update()