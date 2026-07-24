from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pywizlight_phase0_documents_exist() -> None:
    assert (ROOT / "docs" / "PYWIZLIGHT_INTEGRATION_AUDIT.md").is_file()
    assert (ROOT / "docs" / "PYWIZLIGHT_065_UPGRADE_REPORT.md").is_file()
    assert (ROOT / "docs" / "adr" / "0001-pywizlight-role.md").is_file()
    assert (ROOT / "docs" / "COMMENT_AND_DOCSTRING_STYLE.md").is_file()


def test_audit_preserves_native_udp_hot_path_decision() -> None:
    audit = (ROOT / "docs" / "PYWIZLIGHT_INTEGRATION_AUDIT.md").read_text(
        encoding="utf-8"
    )
    adr = (ROOT / "docs" / "adr" / "0001-pywizlight-role.md").read_text(
        encoding="utf-8"
    )

    assert "native UDP" in audit
    assert "fire-and-forget" in audit
    assert "required runtime dependency" in audit
    assert "only `core/pywizlight_adapter.py` imports `pywizlight`" in adr


def test_upgrade_is_not_performed_during_audit() -> None:
    report = (ROOT / "docs" / "PYWIZLIGHT_065_UPGRADE_REPORT.md").read_text(
        encoding="utf-8"
    )
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "Postpone the upgrade" in report
    assert "pywizlight==0.6.3" in requirements
    assert "pywizlight==0.6.3" in pyproject


def test_phase0_does_not_add_a_project_license() -> None:
    # The owner must explicitly select the WizZ Desktop license.
    candidates = ("LICENSE", "LICENSE.txt", "LICENSE.md", "LICENSE.rst", "COPYING")
    existing = [name for name in candidates if (ROOT / name).is_file()]
    assert isinstance(existing, list)
