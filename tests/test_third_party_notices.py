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
    