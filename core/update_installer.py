"""Staged, checksum-verified self-update support for portable Windows builds."""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from app_meta import APP_ARTIFACT
from config.paths import config_dir
from .update_checker import ReleaseInfo


class UpdateInstallError(RuntimeError):
    pass


def packaged_install_dir() -> Path | None:
    """Return the portable install root only when its build marker exists."""
    candidate = Path(sys.executable).resolve().parent
    return candidate if (candidate / "BUILD_INFO.json").is_file() else None


def can_self_update() -> bool:
    install_dir = packaged_install_dir()
    return bool(
        sys.platform.startswith("win")
        and install_dir is not None
        and os.access(install_dir.parent, os.W_OK)
    )


def _read_sha256(url: str) -> str:
    request = Request(url, headers={"User-Agent": "WizZ-Desktop-Updater"})
    with urlopen(request, timeout=15) as response:
        content = response.read().decode("utf-8", errors="replace")
    match = re.search(r"\b([A-Fa-f0-9]{64})\b", content)
    if not match:
        raise UpdateInstallError("La suma SHA-256 publicada no es válida.")
    return match.group(1).lower()


def _download(url: str, target: Path) -> str:
    request = Request(url, headers={"User-Agent": "WizZ-Desktop-Updater"})
    digest = hashlib.sha256()
    temporary = target.with_suffix(target.suffix + ".part")
    try:
        with urlopen(request, timeout=20) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 256):
                digest.update(chunk)
                output.write(chunk)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return digest.hexdigest().lower()


def stage_windows_update(release: ReleaseInfo) -> Path:
    """Download and verify a release, returning a post-exit update script.

    The script waits for this process, atomically swaps the portable app
    directory, launches the new executable, and restores the old directory if
    extraction does not contain the expected launcher.
    """
    if not can_self_update():
        raise UpdateInstallError("La actualización automática requiere una instalación portable de Windows con permisos de escritura.")
    if not release.download_url or not release.checksum_url:
        raise UpdateInstallError("La release no incluye un ZIP de Windows con su SHA-256.")

    install_dir = packaged_install_dir()
    assert install_dir is not None
    version = re.sub(r"[^A-Za-z0-9._-]", "_", release.version)
    stage = config_dir().parent / "updates" / version
    stage.mkdir(parents=True, exist_ok=True)
    archive = stage / f"{APP_ARTIFACT}-update.zip"
    expected = _read_sha256(release.checksum_url)
    actual = _download(release.download_url, archive)
    if actual != expected:
        archive.unlink(missing_ok=True)
        raise UpdateInstallError("La verificación SHA-256 falló; la actualización fue descartada.")

    script = stage / "apply-update.ps1"
    replacement = stage / "replacement"
    backup = install_dir.with_name(install_dir.name + ".backup")
    executable = install_dir / f"{APP_ARTIFACT}.exe"
    def ps_literal(value: Path) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    script.write_text(
        "param([int]$ProcessId)\n"
        "$ErrorActionPreference = 'Stop'\n"
        "try { Wait-Process -Id $ProcessId -ErrorAction SilentlyContinue } catch {}\n"
        f"$archive = {ps_literal(archive)}\n$replacement = {ps_literal(replacement)}\n"
        f"$install = {ps_literal(install_dir)}\n$backup = {ps_literal(backup)}\n"
        "Remove-Item $replacement -Recurse -Force -ErrorAction SilentlyContinue\n"
        "New-Item -ItemType Directory -Path $replacement -Force | Out-Null\n"
        "Expand-Archive -LiteralPath $archive -DestinationPath $replacement -Force\n"
        f"if (-not (Test-Path (Join-Path $replacement '{APP_ARTIFACT}.exe'))) {{ throw 'El ZIP no contiene el ejecutable esperado.' }}\n"
        "Remove-Item $backup -Recurse -Force -ErrorAction SilentlyContinue\n"
        "Move-Item -LiteralPath $install -Destination $backup\n"
        "try { Move-Item -LiteralPath $replacement -Destination $install } catch { Move-Item -LiteralPath $backup -Destination $install; throw }\n"
        f"Start-Process -FilePath (Join-Path $install '{APP_ARTIFACT}.exe')\n"
        "Remove-Item $backup -Recurse -Force -ErrorAction SilentlyContinue\n",
        encoding="utf-8",
    )
    return script


def launch_staged_update(script: Path) -> None:
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), str(os.getpid())],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
