"""Exercise keyboard capture and the shared picker in an isolated Qt process."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hotkey_editor_captures_one_chord_and_selects_kelvin_without_transport(tmp_path):
    script = r'''
import os
import re
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QWheelEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.dev_virtual_lights import VirtualLightController
from qt_ui.bridge import WizzBridge

app = QApplication([])
font_id = QFontDatabase.addApplicationFont(str(Path.cwd() / "assets" / "fonts" / "InterVariable.ttf"))
QFontDatabase.addApplicationFont(str(Path.cwd() / "assets" / "fonts" / "WizZInterStrong.ttf"))
families = QFontDatabase.applicationFontFamilies(font_id)
if families:
    app.setFont(QFont(families[0], 11))
controller = VirtualLightController(1)
controller.start()
bridge = WizzBridge(controller)
if shot_lang := os.environ.get("WIZZ_QT_HOTKEY_SHOT_LANG"):
    bridge.setLanguage(shot_lang)
engine = QQmlApplicationEngine()
engine.warnings.connect(lambda warnings: [print(warning.toString()) for warning in warnings])
root = Path.cwd()
engine.addImportPath(str(root / "qt_ui" / "qml"))
engine.rootContext().setContextProperty("wizz", bridge)
engine.load(QUrl.fromLocalFile(str(root / "qt_ui" / "qml" / "Main.qml")))
assert engine.rootObjects(), "Main.qml failed to load"
window = engine.rootObjects()[0]
window.setProperty("currentPage", 6)
window.setProperty("pageVisible", True)
window.show()
app.processEvents()
page = window.findChild(QObject, "hotkeysPage")
capture = window.findChild(QObject, "shortcutCapture")
assert page is not None and capture is not None

page.beginCapture()
assert page.property("recording") is True
QTest.keyClick(window, Qt.Key_L, Qt.ControlModifier | Qt.AltModifier)
app.processEvents()
assert page.property("capturedCombo") == "ctrl+alt+l", page.property("capturedCombo")
QTest.keyClick(window, Qt.Key_3)
assert page.property("capturedCombo") == "ctrl+alt+l"
QTest.qWait(1100)
assert page.property("captureAwaitingRelease") is False

page.beginCapture()
QTest.keyClick(window, Qt.Key_1, Qt.ControlModifier | Qt.AltModifier | Qt.KeypadModifier)
app.processEvents()
assert page.property("capturedCombo") == "ctrl+alt+numpad1"
assert "Numpad 1" in page.formatCombo(page.property("capturedCombo"))
page.endCapture()
page.beginCapture()
QTest.keyClick(window, Qt.Key_1, Qt.ControlModifier | Qt.AltModifier)
app.processEvents()
assert page.property("capturedCombo") == "ctrl+alt+1"
page.endCapture()
page.beginCapture()
QTest.keyClick(window, Qt.Key_Plus, Qt.ControlModifier | Qt.AltModifier | Qt.KeypadModifier)
app.processEvents()
assert page.property("capturedCombo") == "ctrl+alt+numpadplus"
page.endCapture()
page.beginCapture()
QTest.keyClick(window, Qt.Key_End, Qt.ControlModifier | Qt.AltModifier | Qt.KeypadModifier)
app.processEvents()
assert page.property("recording") is True
assert page.property("capturedCombo") == "ctrl+alt+numpadplus"
assert "Num Lock" in page.property("feedback") or "Bloq Num" in page.property("feedback")
page.endCapture()

for _ in range(100):
    app.processEvents()
    if bridge.hotkeyActions:
        break
    QTest.qWait(20)
actions = bridge.hotkeyActions
index = next(i for i, action in enumerate(actions) if action["id"] == "white_custom")
action_box = window.findChild(QQuickItem, "hotkeyActionBox")
picker = window.findChild(QObject, "hotkeyCustomPicker")
assert action_box is not None and picker is not None
action_box.setProperty("currentIndex", index)
app.processEvents()
assert page.property("editingCustomWhite") is True
assert picker.property("selectionOnly") is True
assert picker.property("showWhiteSection") is True
before = controller.get_state().copy()
picker.chooseKelvin(3350)
app.processEvents()
assert page.property("customKelvin") == 3350
assert page.selectedActionId() == "white_kelvin_3350"
assert controller.get_state() == before, "editing a shortcut changed the bulb"

scroll = window.findChild(QObject, "pageScroll")
scroll.setProperty("contentY", 380)
QTest.qWait(500)
white_track = window.findChild(QQuickItem, "whiteCctTrack")
assert white_track is not None and white_track.width() > 0
white_point = white_track.mapToScene(QPointF(white_track.width() * 0.7, white_track.height() / 2))
QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(round(white_point.x()), round(white_point.y())))
app.processEvents()
assert 5100 <= page.property("customKelvin") <= 5300, page.property("customKelvin")
assert controller.get_state() == before, "clicking the white track changed the bulb"

if shot_dir := os.environ.get("WIZZ_QT_HOTKEY_SHOT_DIR"):
    assert window.screen().grabWindow(window.winId()).save(str(Path(shot_dir) / "hotkey-white.png"))

color_index = next(i for i, action in enumerate(actions) if action["id"] == "color_custom")
action_box.setProperty("currentIndex", color_index)
app.processEvents()
assert page.property("editingCustomColor") is True
assert picker.property("showColorSection") is True
picker.sendHex("#12ABEF")
app.processEvents()
assert page.property("customHex") == "#12ABEF"
assert page.selectedActionId() == "color_hex_12abef"
assert controller.get_state() == before, "editing a color shortcut changed the bulb"

scroll.setProperty("contentY", 380)
QTest.qWait(500)
spectrum = window.findChild(QQuickItem, "colorSpectrum")
assert spectrum is not None and spectrum.width() > 0
color_point = spectrum.mapToScene(QPointF(spectrum.width() * 0.35, spectrum.height() * 0.6))
QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(round(color_point.x()), round(color_point.y())))
app.processEvents()
assert page.property("customHex") != "#12ABEF", page.property("customHex")
assert re.fullmatch(r"#[0-9A-F]{6}", page.property("customHex")), page.property("customHex")
assert page.selectedActionId().startswith("color_hex_")
assert controller.get_state() == before, "clicking the color palette changed the bulb"
if shot_dir := os.environ.get("WIZZ_QT_HOTKEY_SHOT_DIR"):
    assert window.screen().grabWindow(window.winId()).save(str(Path(shot_dir) / "hotkey-color.png"))

box_point = action_box.mapToScene(QPointF(action_box.width() * 0.5, action_box.height() * 0.5))
QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(round(box_point.x()), round(box_point.y())))
QTest.qWait(200)
if shot_dir := os.environ.get("WIZZ_QT_HOTKEY_SHOT_DIR"):
    assert window.screen().grabWindow(window.winId()).save(str(Path(shot_dir) / "hotkey-menu-initial.png"))
assert action_box.property("matchingCount") == action_box.property("count")
options_view = action_box.findChild(QQuickItem, "wizzComboOptionsView")
assert options_view is not None and options_view.width() > 0
before_scroll = options_view.property("contentY")
wheel_point = options_view.mapToScene(QPointF(options_view.width() / 2, options_view.height() / 2))
wheel = QWheelEvent(wheel_point, QPointF(window.mapToGlobal(wheel_point.toPoint())),
                    QPoint(0, 0), QPoint(0, -120), Qt.NoButton, Qt.NoModifier,
                    Qt.NoScrollPhase, False)
app.sendEvent(window, wheel)
QTest.qWait(220)
assert options_view.property("contentY") > before_scroll, (before_scroll, options_view.property("contentY"))
action_box.setProperty("filterText", "unlikely-to-match-any-action-123")
app.processEvents()
assert action_box.property("matchingCount") == 0
action_box.setProperty("filterText", "")
QTest.qWait(120)

if shot_dir := os.environ.get("WIZZ_QT_HOTKEY_SHOT_DIR"):
    assert window.screen().grabWindow(window.winId()).save(str(Path(shot_dir) / "hotkey-menu.png"))
action_box.setProperty("filterText", actions[0]["name"])
QTest.qWait(120)
assert options_view is not None and options_view.width() > 0
first_option = options_view.mapToScene(QPointF(80, 45))
QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(round(first_option.x()), round(first_option.y())))
app.processEvents()
assert action_box.property("currentValue") == actions[0]["id"], (action_box.property("currentValue"), actions[0]["id"], first_option)
assert page.property("editingPicker") is False
group_box = window.findChild(QObject, "hotkeyGroupBox")
group_box.activateVisibleIndex(1)
app.processEvents()
assert page.property("actionGroup") == group_box.property("currentText")

bridge.shutdown()
controller.stop()
window.close()
'''
    env = os.environ.copy()
    env.update({
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "WIZZ_CONFIG_DIR": str(tmp_path),
    })
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
