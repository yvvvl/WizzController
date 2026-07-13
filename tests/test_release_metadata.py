from __future__ import annotations

import tomllib
from pathlib import Path

from app_meta import APP_ARTIFACT, APP_BUILD_NUMBER, APP_PRODUCT, APP_VERSION


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_matches_runtime_metadata():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["version"] == APP_VERSION
    assert data["tool"]["flet"]["product"] == APP_PRODUCT
    assert data["tool"]["flet"]["build_number"] == APP_BUILD_NUMBER
    assert data["tool"]["flet"]["windows"]["artifact"] == APP_ARTIFACT


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


def test_runtime_dependencies_are_declared_for_flet_build():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = "\n".join(data["project"]["dependencies"]).casefold()
    for package in (
        "flet",
        "pywizlight",
        "psutil",
        "keyboard",
        "pystray",
        "pillow",
    ):
        assert package in dependencies

    for removed in ("faster-whisper", "sounddevice", "numpy"):
        assert removed not in dependencies


def test_flet_build_excludes_private_runtime_and_dev_files():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    excluded = set(data["tool"]["flet"]["app"]["exclude"])

    assert "config/json" in excluded
    assert "tests" in excluded
    assert "tools" in excluded
    assert ".git" in excluded
    assert data["tool"]["flet"]["app"]["boot_screen"]["show"] is True
    assert data["tool"]["flet"]["app"]["startup_screen"]["show"] is True


def test_windows_build_and_smoke_scripts_are_present():
    build_script = (ROOT / "scripts" / "build_windows.ps1").read_text(
        encoding="utf-8"
    )
    smoke_script = (ROOT / "scripts" / "test_windows_build.ps1").read_text(
        encoding="utf-8"
    )

    assert '"build",' in build_script
    assert '"windows",' in build_script
    assert "BUILD_INFO.json" in build_script
    assert "WizZDesktop.exe" in smoke_script
    assert "LaunchSecondInstance" in smoke_script
