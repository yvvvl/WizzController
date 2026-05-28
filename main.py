import sys
import logging
import traceback
import flet as ft

from core.light_controller import LightController
from ui.app import WizzApp
from ui.theme import Theme

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def main(page: ft.Page):
    try:
        page.title = "WizZ Desktop"
        page.bgcolor = Theme.BG
        page.padding = 0
        page.theme_mode = ft.ThemeMode.DARK
        page.theme = ft.Theme(color_scheme_seed=Theme.PRIMARY)

        page.window.width = 1080
        page.window.height = 720
        page.window.min_width = 820
        page.window.min_height = 600

        # Backend
        wiz = LightController()

        # Frontend
        app = WizzApp(page, wiz)
        wiz.set_callback(lambda state: _safe(app.update_ui, state))

        page.add(app)
        page.update()

        wiz.start()
        logging.info("WizZ listo.")

    except Exception:
        traceback.print_exc()


def _safe(fn, *args):
    try:
        fn(*args)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        ft.app(target=main)
    except KeyboardInterrupt:
        sys.exit()
