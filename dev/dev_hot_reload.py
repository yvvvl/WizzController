"""
Script para desarrollo con hot reload automático
Ejecuta: python dev/dev_hot_reload.py
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path de Python
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import flet as ft
import threading
from core.light_manager import LightManager
from ui.app import WizzApp

def main(page: ft.Page):
    wiz = LightManager()
    threading.Thread(target=wiz.startup_sequence, daemon=True).start()
    app = WizzApp(page, wiz)

if __name__ == "__main__":
    # El parámetro view=ft.AppView.WEB_BROWSER abre en el navegador para mejor hot reload
    ft.app(target=main, view=ft.AppView.FLET_APP)
