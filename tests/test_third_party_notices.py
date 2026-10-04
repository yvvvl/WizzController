from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pywizlight_notice_exists():
    notice = ROOT / "THIRD_PARTY_NOTICES.md"
    license_file = ROOT / "licenses" / "pywizlight-LICENSE.txt"

    assert notice.exists()
    assert license_file.exists()


def test_pywizlight_notice_mentions_license():
    text = (
        ROOT / "THIRD_PARTY_NOTICES.md"
    ).read_text(
        encoding="utf-8"
    )

    assert "pywizlight" in text.lower()
    assert "MIT License" in text


def test_linux_release_bundles_third_party_notice_and_license():
    build_script = (ROOT / "scripts" / "build_qt_linux.sh").read_text(encoding="utf-8")

    assert '"$ROOT/THIRD_PARTY_NOTICES.md" "$PACKAGE_DIR/THIRD_PARTY_NOTICES.md"' in build_script
    assert '"$ROOT/licenses" "$PACKAGE_DIR/licenses"' in build_script
