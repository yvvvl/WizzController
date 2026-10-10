"""Guard QML copy without treating colors, brand names or comments as prose."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

from tools.i18n_audit import qml_hardcoded_strings, qml_translation_pair_errors


def test_qml_audit_catches_untranslated_visible_copy(tmp_path: Path):
    page = tmp_path / "Example.qml"
    page.write_text(
        'Text { text: "Solo español" }\n'
        'TextField { placeholderText: "Search lights" }\n'
        'Repeater { model: [{title: "Fiesta"}] }\n',
        encoding="utf-8",
    )

    assert qml_hardcoded_strings([page]) == [
        "Example.qml:1: text: Solo español",
        "Example.qml:2: placeholderText: Search lights",
        "Example.qml:3: title: Fiesta",
    ]


def test_qml_audit_ignores_translation_pairs_and_nonlinguistic_literals(tmp_path: Path):
    page = tmp_path / "Example.qml"
    page.write_text(
        '// Text { text: "Comment" }\n'
        '/* title: "Also a comment" */\n'
        'property color text: "#f4f7ff"\n'
        'Text { text: root.t("Hola", "Hello") }\n'
        'Text { text: "WizZ Desktop" }\n'
        'Text { text: "HEX" }\n'
        'Text { text: "250ms" }\n'
        'Text { text: "+ " + root.t("Nuevo", "New") }\n'
        'TextField { placeholderText: "#FF0000" }\n'
        'Text { text: wizz.language === "en" ? "Home" : "Inicio" }\n',
        encoding="utf-8",
    )

    assert qml_hardcoded_strings([page]) == []
    assert qml_translation_pair_errors([page]) == []


def test_qml_audit_rejects_missing_or_empty_language_pair(tmp_path: Path):
    page = tmp_path / "Example.qml"
    page.write_text(
        'Text { text: root.t("Hola") }\n'
        'Text { text: root.t(" ", "Hello") }\n'
        'Text { text: root.t("Adiós", "Goodbye") }\n',
        encoding="utf-8",
    )

    assert qml_translation_pair_errors([page]) == [
        "Example.qml:1: incomplete root.t(es, en) pair",
        "Example.qml:2: incomplete root.t(es, en) pair",
    ]


def test_current_qml_has_no_direct_visible_copy_or_incomplete_pairs():
    assert qml_hardcoded_strings() == []
    assert qml_translation_pair_errors() == []


def test_qml_navigation_and_scene_presets_update_in_both_languages(tmp_path: Path):
    script = r'''
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from core.dev_virtual_lights import VirtualLightController
from qt_ui.bridge import WizzBridge

app = QApplication([])
controller = VirtualLightController(1)
controller.start()
bridge = WizzBridge(controller)
engine = QQmlApplicationEngine()
root = Path.cwd()
engine.addImportPath(str(root / "qt_ui" / "qml"))
engine.rootContext().setContextProperty("wizz", bridge)
engine.load(QUrl.fromLocalFile(str(root / "qt_ui" / "qml" / "Main.qml")))
assert engine.rootObjects(), "Main.qml failed to load"
window = engine.rootObjects()[0]
window.show()
window.setProperty("currentPage", 2)
for _ in range(5):
    app.processEvents()
scenes_page = window.findChild(QObject, "scenesPage")
assert scenes_page is not None

for language, expected, preset_names in (
    ("es", {"home": "Inicio", "scenes": "Escenas", "settings": "Ajustes"}, {"Fiesta", "Océano", "Día"}),
    ("en", {"home": "Home", "scenes": "Scenes", "settings": "Settings"}, {"Party", "Ocean", "Daylight"}),
):
    bridge.setPreviewLanguage(language)
    app.processEvents()
    labels = {
        item["icon"]: item["title"]
        for item in window.property("navigationItems").toVariant()
        if item["icon"] in expected
    }
    assert labels == expected, (language, labels)
    titles = {item["title"] for item in scenes_page.property("quickScenePresets").toVariant()}
    assert preset_names <= titles, (language, titles)

# At the smallest supported window size, the routine header must put its
# actions below the copy rather than painting over the subtitle.
window.resize(820, 600)
window.setProperty("currentPage", 4)
for _ in range(5):
    app.processEvents()
routines_page = window.findChild(QObject, "routinesPage")
assert routines_page is not None
header = routines_page.findChild(QObject, "routinesHeader")
header_text = routines_page.findChild(QObject, "routinesHeaderText")
actions = routines_page.findChild(QObject, "routinesHeaderActions")
assert header is not None and header_text is not None and actions is not None
assert header_text.property("y") + header_text.property("height") <= actions.property("y"), (
    header_text.property("y"), header_text.property("height"), actions.property("y")
)
assert actions.property("y") + actions.property("height") <= header.property("height")

window.close()
bridge.shutdown()
controller.stop()
'''
    env = os.environ.copy()
    env.update({
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "WIZZ_CONFIG_DIR": str(tmp_path),
    })
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
