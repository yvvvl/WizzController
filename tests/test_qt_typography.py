from pathlib import Path


QML = Path(__file__).resolve().parents[1] / "qt_ui" / "qml"


def test_page_titles_share_a_stronger_weight():
    for name in (
        "Main.qml",
        "ColorPage.qml",
        "FavoritesPage.qml",
        "HotkeysPage.qml",
        "RoutinesPage.qml",
        "ScenesPage.qml",
        "SettingsPage.qml",
    ):
        source = (QML / name).read_text(encoding="utf-8")
        assert "font.pixelSize: Theme.pageTitleSize; font.weight: Theme.pageTitleWeight" in source


def test_power_states_and_connection_status_are_visually_emphasized():
    for name in ("Main.qml", "QuickPanel.qml"):
        source = (QML / name).read_text(encoding="utf-8")
        assert "font.weight: Theme.stateWeight" in source
    home = (QML / "Main.qml").read_text(encoding="utf-8")
    assert "text: wizz.statusLine; color: Theme.text" in home
    assert "font.weight: Font.Bold; elide: Text.ElideRight" in home


def test_hotkey_status_badge_is_right_aligned():
    source = (QML / "HotkeysPage.qml").read_text(encoding="utf-8")
    assert "id: hotkeysStatusBadge" in source
    assert "anchors.right: parent.right" in source
    assert "width: Math.max(0, hotkeysStatusBadge.x - x - 12)" in source
