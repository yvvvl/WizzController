import flet as ft
import threading
import time
import os
import sys

# Ensure project root is on sys.path when running this file directly
try:
    _THIS_DIR = os.path.dirname(__file__)
    _ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, '..'))
    if _ROOT_DIR not in sys.path:
        sys.path.insert(0, _ROOT_DIR)
except Exception:
    pass

from ui.components.header import Header
from ui.components.color_panel import ColorPanel
from ui.components.controls import ControlPanel

class WizzApp:
    def __init__(self, page: ft.Page, wiz_manager):
        self.page = page
        self.wiz = wiz_manager
        
        # Inicializar Componentes
        self.header = Header()
        
        # Instanciar paneles (pero no los agregamos directo, los envolvemos abajo)
        self._raw_color_panel = ColorPanel(self.wiz)
        self._raw_controls = ControlPanel(self.wiz)
        
        # Ajustar estilos de los paneles para que sean "transparentes" 
        # y dejen que la tarjeta del app maneje el fondo
        self._raw_color_panel.bgcolor = ft.Colors.TRANSPARENT
        self._raw_controls.bgcolor = ft.Colors.TRANSPARENT
        
        # Estado de sincronización
        self._sync_running = False
        self._sync_thread = None
        
        self._build_ui()
        # Hacer una sincronización inicial inmediata para reflejar el estado real
        try:
            initial_state = self.wiz.get_pilot_state(timeout_sec=0.2)
            if initial_state and isinstance(initial_state, dict):
                self._update_ui_from_state(initial_state)
        except Exception:
            pass
        # Iniciar polling continuo
        self._start_state_sync()

    def _build_ui(self):
        # --- TARJETA IZQUIERDA: CROMATICIDAD ---
        # Ocupa 7 columnas en PC (md), 12 en móvil (sm)
        card_color = ft.Container(
            content=self._raw_color_panel,
            bgcolor="#1e293b", # Gris azulado oscuro
            border_radius=20,
            padding=10,
            shadow=ft.BoxShadow(blur_radius=15, color="#00000055", offset=ft.Offset(0, 5)),
            border=ft.border.all(1, "#334155"),
            col={"sm": 12, "md": 7, "xl": 8} # Responsividad
        )

        # --- TARJETA DERECHA: CONTROLES ---
        # Ocupa 5 columnas en PC (md), 12 en móvil (sm)
        card_controls = ft.Container(
            content=self._raw_controls,
            bgcolor="#1e293b",
            border_radius=20,
            padding=10,
            shadow=ft.BoxShadow(blur_radius=15, color="#00000055", offset=ft.Offset(0, 5)),
            border=ft.border.all(1, "#334155"),
            col={"sm": 12, "md": 5, "xl": 4} # Responsividad
        )

        # --- GRID MAESTRO ---
        # ResponsiveRow organiza las columnas automáticamente
        layout_grid = ft.ResponsiveRow(
            controls=[
                card_color,
                card_controls
            ],
            spacing=20, # Espacio entre tarjetas
            run_spacing=20,
        )

        # Contenedor principal con scroll (por si la ventana es muy baja)
        main_container = ft.Container(
            content=layout_grid,
            padding=20,
            expand=True,
            alignment=ft.alignment.top_center
        )

        # Estructura Final
        self.page.add(
            ft.Column([
                self.header,
                main_container
            ], expand=True, spacing=0)
        )
        
        # Hook para detectar resize y ajustar el anillo si es necesario
        self.page.on_resize = self._on_page_resize
        
    def _on_page_resize(self, e):
        # Ajustar modo del anillo según ancho disponible
        w = self.page.window_width
        if w < 700:
            self._raw_color_panel.set_mode(compact=True)
        elif w > 1200:
            self._raw_color_panel.set_mode(wide=True)
        else:
            self._raw_color_panel.set_mode(compact=False, wide=False)
    
    def _start_state_sync(self):
        """Inicia polling de estado para sincronizar con cambios externos."""
        self._sync_running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
    
    def _sync_loop(self):
        """Loop que consulta getPilot cada 100ms y actualiza UI."""
        while self._sync_running:
            try:
                state = self.wiz.get_pilot_state(timeout_sec=0.05)
                if state and isinstance(state, dict):
                    # Actualizar UI de forma segura
                    try:
                        self._update_ui_from_state(state)
                    except Exception:
                        pass  # Silenciar errores de UI durante sync
            except Exception:
                pass  # Silenciar errores de red/timeout
            time.sleep(0.1)  # 10 veces por segundo
    
    def _update_ui_from_state(self, state: dict):
        """Actualiza sliders según estado de la bombilla."""
        if not state or not isinstance(state, dict):
            return
        
        try:
            # Actualizar temperatura si está presente
            if "temp" in state and hasattr(self._raw_controls, 'sync_temperature'):
                temp = int(state["temp"])
                self._raw_controls.sync_temperature(temp)
        except Exception:
            pass
        
        try:
            # Actualizar brillo si está presente
            if "dimming" in state and hasattr(self._raw_controls, 'sync_brightness'):
                dim = int(state["dimming"])
                self._raw_controls.sync_brightness(dim)
        except Exception:
            pass
        
        try:
            # Actualizar color RGB si está presente
            if "r" in state and "g" in state and "b" in state and hasattr(self._raw_color_panel, 'sync_color_rgb'):
                r = int(state.get("r", 0))
                g = int(state.get("g", 0))
                b = int(state.get("b", 0))
                self._raw_color_panel.sync_color_rgb(r, g, b)
        except Exception:
            pass
    
    def stop_sync(self):
        """Detiene el polling de estado."""
        self._sync_running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=1.0)