from __future__ import annotations

import os
import sys
import tempfile
from ctypes.util import find_library
from pathlib import Path

from PySide6.QtCore import QMetaObject, QSize, QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication

from app_meta import APP_ID, APP_NAME
from config.app_runtime_manager import AppRuntimeManager
from core.dev_virtual_lights import (
    VirtualLightController,
    virtual_bulb_count_from_environment,
)
from core.light_controller import LightController
from core.single_instance import SingleInstanceGuard
from core.update_installer import update_is_applying
from qt_ui.bridge import WizzBridge
from qt_ui.runtime import QtDesktopRuntime, activate_existing_instance


def create_controller() -> LightController:
    """Use real WiZ devices unless source-run QA explicitly requests fakes."""
    virtual_count = virtual_bulb_count_from_environment()
    if virtual_count:
        return VirtualLightController(virtual_count)
    return LightController()


def _watch_update_completion(app: QApplication, bridge: WizzBridge) -> QTimer:
    """Wait for the detached helper's health check without racing its result."""
    timer = QTimer(app)
    timer.setInterval(1000)
    checks = 0

    def check() -> None:
        nonlocal checks
        checks += 1
        if bridge.loadUpdateCompletion() or checks >= 120:
            timer.stop()

    timer.timeout.connect(check)
    timer.start()
    return timer


def _prefer_xcb_for_wayland() -> bool:
    """Use XWayland on Linux so movable panels can be positioned after drag.

    Qt's Wayland backend does not support setting a top-level window position;
    the compositor owns that geometry. XWayland preserves native drag support
    while allowing the Quick Panel to snap to and remember screen edges.
    Respect explicit backend choices and stay on Wayland if XCB requirements
    are missing, rather than preventing the app from starting.
    """
    if (
        sys.platform != "linux"
        or os.environ.get("QT_QPA_PLATFORM")
        or not os.environ.get("WAYLAND_DISPLAY")
        or not os.environ.get("DISPLAY")
    ):
        return False

    required_libraries = {
        "xcb-cursor": "libxcb-cursor0",
        "xcb-icccm": "libxcb-icccm4",
        "xcb-keysyms": "libxcb-keysyms1",
    }
    missing = [
        package for library, package in required_libraries.items()
        if find_library(library) is None
    ]
    if missing:
        print(
            "[QT] XWayland positioning unavailable; missing XCB libraries: "
            + ", ".join(missing)
            + ". Install the listed packages to enable Quick Panel edge snapping."
        )
        return False

    os.environ["QT_QPA_PLATFORM"] = "xcb"
    print("[QT] Using XWayland for reliable Quick Panel positioning and edge snapping.")
    return True


def _prepare_virtual_profile(virtual_count: int) -> None:
    """Keep QA routines/settings out of the user's real app profile."""
    if virtual_count:
        os.environ["WIZZ_CONFIG_DIR"] = str(
            Path(tempfile.gettempdir()) / "WizZDesktop-virtual-qt"
        )


def _prepare_virtual_runtime_settings(settings: AppRuntimeManager, virtual_count: int) -> None:
    """Exercise the tray with virtual lights without overriding startup choices."""
    if virtual_count:
        # Earlier QA builds persisted tray_enabled=False in the isolated
        # profile. Override that value so existing test installs recover too.
        settings.update(tray_enabled=True)


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
    _prefer_xcb_for_wayland()
    virtual_count = virtual_bulb_count_from_environment()
    _prepare_virtual_profile(virtual_count)
    # Never let a manually reopened old copy lock the app files while the
    # detached helper is extracting and replacing an update.
    if update_is_applying():
        print("[QT] Update is still being applied; startup is temporarily deferred.")
        return 0
    guard = SingleInstanceGuard(f"{APP_ID}.virtual" if virtual_count else APP_ID)
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
    font_path = root / "assets" / "fonts" / "InterVariable.ttf"
    strong_font_path = root / "assets" / "fonts" / "WizZInterStrong.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    strong_font_id = QFontDatabase.addApplicationFont(str(strong_font_path))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    strong_families = QFontDatabase.applicationFontFamilies(strong_font_id) if strong_font_id >= 0 else []
    if families:
        ui_font = QFont(families[0], 11)
        # Variable Inter can sit between semibold and bold: compact labels
        # gain presence without flattening the hierarchy of bold headings.
        ui_font.setWeight(QFont.Weight(650))
        app.setFont(ui_font)
    else:
        print(f"[QT] Could not load bundled UI font: {font_path}")
    if "WizZ Inter Strong" not in strong_families:
        print(f"[QT] Could not load bundled heading font: {strong_font_path}")

    controller = create_controller()
    bridge: WizzBridge | None = None
    desktop_runtime: QtDesktopRuntime | None = None
    try:
        if virtual_count:
            print(f"[QT] Virtual-light QA mode: {virtual_count} simulated bulbs; no WiZ LAN traffic.")
        else:
            print("[QT] Real WiZ LAN control enabled.")
        controller.start()
        bridge = WizzBridge(controller)
        if screenshot_path and os.environ.get("WIZZ_QT_UPDATE_PREVIEW") == "1":
            bridge._update_in_progress = True
            bridge._update_preparing = True
            bridge._update_progress = 68
            bridge._update_status = "Downloading v1.4.2… 96%"
        # Extraction and startup verification vary with disk speed. Keep
        # checking until the detached helper publishes a terminal result.
        _watch_update_completion(app, bridge)
        # Test captures can validate either language without changing the
        # user's saved preference.
        if language := os.environ.get("WIZZ_QT_LANGUAGE"):
            bridge.setPreviewLanguage(language)
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
        if virtual_count and not os.environ.get("WIZZ_QT_TITLE"):
            window.setProperty("title", "WizZ Desktop — Virtual lights (test mode)")
        bridge.setMainWindow(window)
        quick_panel, screenshot_path = _apply_qa_overrides(window, screenshot_path=screenshot_path)
        window.show()
        window.raise_()
        window.requestActivate()
        if quick_panel:
            # The Quick Panel is a separate top-level window. Show it only
            # after the owner window has a native handle; otherwise Qt may
            # leave the panel hidden on some desktop backends.
            QTimer.singleShot(200, lambda: QMetaObject.invokeMethod(window, "showQuickPanel"))
        runtime_settings = AppRuntimeManager()
        _prepare_virtual_runtime_settings(runtime_settings, virtual_count)
        desktop_runtime = QtDesktopRuntime(
            app, window, bridge, runtime_settings, guard,
            icon_path=root / "assets" / "tray_icon.png",
        )
        bridge.quitRequested.connect(desktop_runtime.quit_application)
        desktop_runtime.start_single_instance_listener()
        if not screenshot_path:
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
