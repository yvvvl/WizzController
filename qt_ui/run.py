from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QMetaObject, QSize, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication

from app_meta import APP_ID, APP_NAME
from config.app_runtime_manager import AppRuntimeManager
from core.light_controller import LightController
from core.single_instance import SingleInstanceGuard
from qt_ui.bridge import WizzBridge
from qt_ui.runtime import QtDesktopRuntime, activate_existing_instance


def create_controller() -> LightController:
    """The official desktop shell always controls the user's real WiZ devices."""
    return LightController()


def _apply_qa_overrides(window, *, screenshot_path: str | None) -> tuple[bool, str | None]:
    """Keep visual-QA hooks outside normal desktop startup."""
    qa_width = os.environ.get("WIZZ_QT_WIDTH")
    qa_height = os.environ.get("WIZZ_QT_HEIGHT")
    if qa_width or qa_height:
        try:
            window.resize(int(qa_width or window.width()), int(qa_height or window.height()))
        except (TypeError, ValueError):
            print("[QT] Ignoring invalid QA window dimensions.")
    if title := os.environ.get("WIZZ_QT_TITLE"):
        window.setProperty("title", title)
    if os.environ.get("WIZZ_QT_FAVORITE_EDITOR") == "1":
        window.setProperty("qaOpenFavoriteEditor", True)
    kind = os.environ.get("WIZZ_QT_FAVORITE_EDITOR_KIND")
    if kind in {"rgb", "white", "brightness", "scene"}:
        window.setProperty("qaFavoriteEditorKind", kind)
    if os.environ.get("WIZZ_QT_SCENE_EDITOR") == "1":
        window.setProperty("qaOpenSceneEditor", True)
    if os.environ.get("WIZZ_QT_ROUTINE_EDITOR") == "1":
        window.setProperty("qaOpenRoutineEditor", True)
    if preview_page := os.environ.get("WIZZ_QT_PAGE"):
        try:
            window.setProperty("currentPage", max(0, min(6, int(preview_page))))
            window.setProperty("pageVisible", True)
        except (TypeError, ValueError):
            print(f"[QT] Ignoring invalid preview page: {preview_page}")
    quick_panel = os.environ.get("WIZZ_QT_QUICK_PANEL") == "1"
    if quick_panel:
        QMetaObject.invokeMethod(window, "showQuickPanel")
    scroll_value = os.environ.get("WIZZ_QT_SCROLL_Y")
    if scroll_value:
        def apply_scroll() -> None:
            page_scroll = window.findChild(QQuickItem, "pageScroll")
            if page_scroll is None:
                return
            try:
                requested = max(0.0, float(scroll_value))
                maximum = max(0.0, float(page_scroll.property("contentHeight") or 0.0) - float(page_scroll.property("height") or 0.0))
                page_scroll.setProperty("contentY", min(requested, maximum))
            except ValueError:
                print(f"[QT] Ignoring invalid preview scroll: {scroll_value}")
        QTimer.singleShot(600, apply_scroll)
    return quick_panel, screenshot_path


def _schedule_screenshot(app, window, screenshot_path: str, quick_panel: bool) -> None:
    def save_screenshot() -> None:
        target = window
        if quick_panel:
            panels = [candidate for candidate in QGuiApplication.topLevelWindows()
                      if candidate.isVisible() and "Quick Panel" in candidate.title()]
            if panels:
                target = panels[0]
        content = target.contentItem()
        if content is None:
            print("[QT] QQuickWindow content item is unavailable for QA capture.")
            app.quit()
            return
        def finish(result) -> None:
            image = result.image()
            saved = image.save(str(Path(screenshot_path)), "PNG")
            print(f"[QT] Screenshot {image.width()}x{image.height()} {'saved' if saved else 'failed'}: {screenshot_path}")
            app.quit()
        result = content.grabToImage(QSize(int(target.width()), int(target.height())))
        if result is None:
            print("[QT] Scene graph capture could not be started.")
            app.quit()
            return
        target._qa_grab_result = result
        result.ready.connect(lambda: finish(result))
    QTimer.singleShot(1400, save_screenshot)


def main() -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    guard = SingleInstanceGuard(APP_ID)
    if not guard.acquire():
        activate_existing_instance(guard)
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("yvvvl")
    screenshot_path = os.environ.get("WIZZ_QT_SCREENSHOT")
    if screenshot_path:
        app.setQuitOnLastWindowClosed(False)
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    app.setWindowIcon(QIcon(str(root / "assets" / "icon_windows.png")))

    controller = create_controller()
    bridge: WizzBridge | None = None
    desktop_runtime: QtDesktopRuntime | None = None
    try:
        print("[QT] Real WiZ LAN control enabled.")
        controller.start()
        bridge = WizzBridge(controller)
        if theme := os.environ.get("WIZZ_QT_THEME"):
            bridge.setTheme(theme)

        engine = QQmlApplicationEngine()
        engine.warnings.connect(lambda warnings: [print(f"[QML] {warning.toString()}") for warning in warnings])
        engine.addImportPath(str(root / "qt_ui" / "qml"))
        engine.rootContext().setContextProperty("wizz", bridge)
        engine.load(QUrl.fromLocalFile(str(root / "qt_ui" / "qml" / "Main.qml")))
        if not engine.rootObjects():
            print("[QT] Main.qml did not create a root window.")
            return 1

        window = engine.rootObjects()[0]
        bridge.setMainWindow(window)
        quick_panel, screenshot_path = _apply_qa_overrides(window, screenshot_path=screenshot_path)
        window.show()
        window.raise_()
        window.requestActivate()
        desktop_runtime = QtDesktopRuntime(
            app, window, bridge, AppRuntimeManager(), guard,
            icon_path=root / "assets" / "tray_icon.png",
        )
        desktop_runtime.start_single_instance_listener()
        desktop_runtime.start_initial_visibility()
        if screenshot_path:
            _schedule_screenshot(app, window, screenshot_path, quick_panel)
        app.aboutToQuit.connect(bridge.shutdown)
        app.aboutToQuit.connect(controller.stop)
        app.aboutToQuit.connect(desktop_runtime.shutdown)
        return app.exec()
    finally:
        if desktop_runtime is not None:
            desktop_runtime.shutdown()
        if bridge is not None:
            bridge.shutdown()
        controller.stop()
        guard.close()


if __name__ == "__main__":
    raise SystemExit(main())
