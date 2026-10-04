from __future__ import annotations

import json
import os
import platform as host_platform
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import zipfile

from core.update_checker import ReleaseInfo
from core import update_installer


def test_windows_update_is_staged_with_verified_release_assets(monkeypatch, tmp_path):
    install = tmp_path / "WizZ Desktop"
    install.mkdir()
    (install / "BUILD_INFO.json").write_text("{}", encoding="utf-8")

    def fake_download(_url: str, target: Path) -> str:
        target.write_bytes(b"verified archive")
        return "a" * 64

    monkeypatch.setattr(update_installer, "can_self_update", lambda: True)
    monkeypatch.setattr(update_installer, "packaged_install_dir", lambda: install)
    monkeypatch.setattr(update_installer, "config_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(update_installer, "_read_sha256", lambda _url: "a" * 64)
    monkeypatch.setattr(update_installer, "_download", fake_download)

    script = update_installer.stage_windows_update(
        ReleaseInfo(
            version="1.3.1-beta.2",
            download_url="https://example.test/WizZDesktop-windows-x64.zip",
            checksum_url="https://example.test/WizZDesktop-windows-x64.zip.sha256",
        )
    )

    content = script.read_text(encoding="utf-8")
    assert script.name == "apply-update.ps1"
    assert "Expand-Archive" in content
    assert "Wait-Process" in content
    assert "Move-WithRetry" in content
    assert "Set-Location -LiteralPath $PSScriptRoot" in content
    assert "failedInstall" in content
    assert "update-error.log" in content
    assert "WizZDesktop.exe" in content
    assert "unins*" in content
    state = json.loads(update_installer.update_state_path().read_text(encoding="utf-8"))
    assert state["state"] == "preparing"


def test_pending_update_marker_expires_safely(monkeypatch, tmp_path):
    monkeypatch.setattr(update_installer, "config_dir", lambda: tmp_path / "config")
    state = update_installer.update_state_path()
    state.parent.mkdir(parents=True)
    state.write_text('{"state":"applying","updated_at":0}', encoding="utf-8")

    assert not update_installer.update_is_applying()


def test_pending_update_marker_accepts_powershell_utf8_bom(monkeypatch, tmp_path):
    monkeypatch.setattr(update_installer, "config_dir", lambda: tmp_path / "config")
    state = update_installer.update_state_path()
    state.parent.mkdir(parents=True)
    state.write_text(
        '\ufeff{"state":"applying","updated_at":' + str(time.time()) + "}",
        encoding="utf-8",
    )

    assert update_installer.update_is_applying()


def test_windows_helper_replaces_app_when_launched_from_install_directory(monkeypatch, tmp_path):
    if not sys.platform.startswith("win"):
        return

    install = tmp_path / "WizZ Desktop"
    install.mkdir()
    (install / "BUILD_INFO.json").write_text('{"version":"old"}', encoding="utf-8")
    stage_root = tmp_path / "data"

    def fake_download(_url: str, target: Path) -> str:
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("WizZDesktop.exe", b"not-a-real-executable")
            archive.writestr("BUILD_INFO.json", '{"version":"new"}')
        return "a" * 64

    monkeypatch.setattr(update_installer, "can_self_update", lambda: True)
    monkeypatch.setattr(update_installer, "packaged_install_dir", lambda: install)
    monkeypatch.setattr(update_installer, "config_dir", lambda: stage_root / "config")
    monkeypatch.setattr(update_installer, "_read_sha256", lambda _url: "a" * 64)
    monkeypatch.setattr(update_installer, "_download", fake_download)
    script = update_installer.stage_windows_update(
        ReleaseInfo(
            version="test-update",
            download_url="https://example.test/WizZDesktop-windows-x64.zip",
            checksum_url="https://example.test/WizZDesktop-windows-x64.zip.sha256",
        )
    )

    powershell = Path(os.environ["WINDIR"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "2147483647"],
        cwd=install,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    # Start-Process intentionally fails on the fake executable. The helper
    # must restore the original app after proving it can move the install dir.
    assert result.returncode != 0
    assert (install / "BUILD_INFO.json").read_text(encoding="utf-8") == '{"version":"old"}'
    assert (script.parent / "update-error.log").is_file()


def _make_linux_bundle(directory: Path, version: str, executable_body: str = "#!/bin/sh\nexit 0\n") -> Path:
    source = directory / f"source-{version}"
    source.mkdir(parents=True)
    executable = source / "WizZDesktop"
    executable.write_text(executable_body, encoding="utf-8")
    executable.chmod(0o755)
    (source / "BUILD_INFO.json").write_text(
        json.dumps({
            "artifact": "WizZDesktop",
            "version": version,
            "platform": "linux",
            "architecture": "arm64" if host_platform.machine().lower() in {"aarch64", "arm64"} else "x64",
        }),
        encoding="utf-8",
    )
    archive = directory / f"bundle-{version}.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(executable, arcname="WizZDesktop")
        bundle.add(source / "BUILD_INFO.json", arcname="BUILD_INFO.json")
    return archive


def test_linux_update_is_staged_with_checksum_and_verified_bundle(monkeypatch, tmp_path):
    install = tmp_path / "WizZDesktop"
    install.mkdir()
    (install / "BUILD_INFO.json").write_text('{"version":"old"}', encoding="utf-8")
    source_archive = _make_linux_bundle(tmp_path, "1.3.5")

    def fake_download(_url: str, target: Path) -> str:
        target.write_bytes(source_archive.read_bytes())
        return "b" * 64

    monkeypatch.setattr(update_installer.sys, "platform", "linux")
    monkeypatch.setattr(update_installer, "can_self_update", lambda: True)
    monkeypatch.setattr(update_installer, "packaged_install_dir", lambda: install)
    monkeypatch.setattr(update_installer, "config_dir", lambda: tmp_path / "config")
    monkeypatch.setattr(update_installer, "_read_sha256", lambda _url: "b" * 64)
    monkeypatch.setattr(update_installer, "_download", fake_download)

    script = update_installer.stage_linux_update(
        ReleaseInfo(
            version="1.3.5",
            download_url="https://example.test/WizZDesktop-linux-x64.tar.gz",
            checksum_url="https://example.test/WizZDesktop-linux-x64.tar.gz.sha256",
        )
    )

    replacement = script.parent / "replacement"
    assert script.name == "apply-update.sh"
    assert script.parent.parent.parent == install.parent
    assert script.parent.parent.name == ".WizZDesktop-updates"
    assert os.access(script, os.X_OK)
    if os.name != "nt":
        # NTFS does not expose POSIX executable permission bits, even when the
        # Linux updater path is exercised by monkeypatching sys.platform.
        assert (replacement / "WizZDesktop").stat().st_mode & 0o111
    assert json.loads((replacement / "BUILD_INFO.json").read_text(encoding="utf-8"))["version"] == "1.3.5"
    assert "backup_created=0" in script.read_text(encoding="utf-8")
    assert json.loads(update_installer.update_state_path().read_text(encoding="utf-8"))["state"] == "preparing"


def test_linux_update_helper_swaps_bundle_and_rolls_back_on_launch_failure(monkeypatch, tmp_path):
    if not sys.platform.startswith("linux"):
        return

    install = tmp_path / "WizZDesktop"
    install.mkdir()
    (install / "BUILD_INFO.json").write_text('{"version":"old"}', encoding="utf-8")
    source_archive = _make_linux_bundle(tmp_path, "1.3.5", "#!/bin/sh\nexit 1\n")

    def fake_download(_url: str, target: Path) -> str:
        target.write_bytes(source_archive.read_bytes())
        return "c" * 64

    monkeypatch.setattr(update_installer, "can_self_update", lambda: True)
    monkeypatch.setattr(update_installer, "packaged_install_dir", lambda: install)
    monkeypatch.setattr(update_installer, "config_dir", lambda: tmp_path / "config")
    monkeypatch.setattr(update_installer, "_read_sha256", lambda _url: "c" * 64)
    monkeypatch.setattr(update_installer, "_download", fake_download)
    script = update_installer.stage_linux_update(
        ReleaseInfo(
            version="1.3.5",
            download_url="https://example.test/WizZDesktop-linux-x64.tar.gz",
            checksum_url="https://example.test/WizZDesktop-linux-x64.tar.gz.sha256",
        )
    )

    result = subprocess.run(
        ["bash", str(script), "2147483647"],
        cwd=script.parent,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode != 0
    assert (install / "BUILD_INFO.json").read_text(encoding="utf-8") == '{"version":"old"}'
    assert (script.parent / "update-error.log").is_file()
