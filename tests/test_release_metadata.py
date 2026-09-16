from __future__ import annotations

import tomllib
from pathlib import Path

from app_meta import APP_ARTIFACT, APP_BUILD_NUMBER, APP_PRODUCT, APP_VERSION


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_matches_runtime_metadata():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["version"] == APP_VERSION
    assert data["project"]["name"] == "wizz-controller"
    assert any(item.startswith("PySide6") for item in data["project"]["dependencies"])
    assert "flet" not in data.get("tool", {})


def test_windows_brand_assets_exist():
    assets = ROOT / "assets"
    for filename in (
        "icon.png",
        "icon_windows.png",
        "icon_windows.ico",
        "tray_icon.png",
    ):
        path = assets / filename
        assert path.is_file()
        assert path.stat().st_size > 1000


def test_runtime_dependencies_are_declared_for_qt_build():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = "\n".join(data["project"]["dependencies"]).casefold()
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").casefold()
    for package in (
        "pywizlight",
        "psutil",
        "keyboard",
        "pystray",
        "pillow",
        "certifi",
    ):
        assert package in dependencies
        assert package in requirements

    for removed in ("faster-whisper", "sounddevice", "numpy"):
        assert removed not in dependencies


def test_flet_is_not_a_release_configuration():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "flet" not in data.get("tool", {})
    assert "legacy-flet" in data["project"]["optional-dependencies"]


def test_windows_build_and_smoke_scripts_are_present():
    build_script = (ROOT / "scripts" / "build_windows.ps1").read_text(
        encoding="utf-8"
    )
    smoke_script = (ROOT / "scripts" / "test_windows_build.ps1").read_text(
        encoding="utf-8"
    )

    assert "retired" in build_script
    assert "build_qt_windows.ps1" in build_script
    assert "WizZDesktop.exe" in smoke_script
    assert "LaunchSecondInstance" in smoke_script


def test_qt_beta_build_packages_the_qt_shell_and_its_resources():
    build_script = (ROOT / "scripts" / "build_qt_windows.ps1").read_text(
        encoding="utf-8"
    )

    assert "PyInstaller" in build_script
    assert "qt_ui\\qml;qt_ui\\qml" in build_script
    assert "assets;assets" in build_script
    assert "BUILD_INFO.json" in build_script
    assert "Get-FileHash" in build_script


def test_linux_build_declares_native_x64_and_arm64_artifacts():
    build_script = (ROOT / "scripts" / "build_linux.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "linux-beta-build.yml").read_text(encoding="utf-8")

    assert "--arch x64|arm64" in build_script
    assert '"architecture": "$ARCH"' in build_script
    assert "linux-${ARCH}.tar.gz" in build_script
    assert "ubuntu-24.04-arm" in workflow
    assert "architecture: arm64" in workflow



def test_windows_workflow_uses_stable_runner_and_keeps_failure_logs():
    workflow = (
        ROOT / ".github" / "workflows" / "build-windows.yml"
    ).read_text(encoding="utf-8")

    assert "runs-on: windows-2022" in workflow
    assert 'python-version: "3.13"' in workflow
    assert "Upload build diagnostics" in workflow
    assert "build-windows.log" in workflow


def test_qt_build_does_not_bundle_legacy_flet_ui():
    build_script = (ROOT / "scripts" / "build_qt_windows.ps1").read_text(encoding="utf-8")
    assert "qt_ui\\run.py" in build_script
    assert "flet build" not in build_script.casefold()
