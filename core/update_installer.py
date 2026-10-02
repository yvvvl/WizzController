"""Staged, checksum-verified self-update support for portable Windows builds."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

from app_meta import APP_ARTIFACT
from config.paths import config_dir
from .update_checker import ReleaseInfo


class UpdateInstallError(RuntimeError):
    pass


def update_state_path() -> Path:
    """State shared by the app and the detached Windows updater."""
    return config_dir().parent / "updates" / "update-state.json"


def _write_update_state(state: str, detail: str = "") -> None:
    target = update_state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"state": state, "detail": detail, "updated_at": time.time()}),
        encoding="utf-8",
    )


def update_is_applying(*, max_age_seconds: int = 300) -> bool:
    """True only while a recently-started helper owns the app replacement."""
    try:
        state = json.loads(update_state_path().read_text(encoding="utf-8"))
        age = time.time() - float(state.get("updated_at", 0))
        return state.get("state") in {"preparing", "applying"} and 0 <= age <= max_age_seconds
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


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
    state_file = update_state_path()
    diagnostic = stage / "update-error.log"
    def ps_literal(value: Path) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    script.write_text(
        "param([int]$ProcessId)\n"
        "$ErrorActionPreference = 'Stop'\n"
        f"$stateFile = {ps_literal(state_file)}\n$diagnostic = {ps_literal(diagnostic)}\n"
        f"$archive = {ps_literal(archive)}\n$replacement = {ps_literal(replacement)}\n"
        f"$install = {ps_literal(install_dir)}\n$backup = {ps_literal(backup)}\n"
        "function Set-UpdateState([string]$state, [string]$detail = '') {\n"
        "  @{ state = $state; detail = $detail; updated_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() } | ConvertTo-Json -Compress | Set-Content -LiteralPath $stateFile -Encoding utf8\n"
        "}\n"
        "function Move-WithRetry([string]$source, [string]$destination) {\n"
        "  $lastError = $null\n"
        "  for ($attempt = 1; $attempt -le 20; $attempt++) {\n"
        "    try { Move-Item -LiteralPath $source -Destination $destination -ErrorAction Stop; return }\n"
        "    catch { $lastError = $_; Start-Sleep -Milliseconds 500 }\n"
        "  }\n"
        "  throw $lastError\n"
        "}\n"
        "try {\n"
        "  Set-UpdateState 'applying' 'Waiting for WizZ Desktop to close'\n"
        "  try { Wait-Process -Id $ProcessId -ErrorAction SilentlyContinue } catch {}\n"
        "  Remove-Item $replacement -Recurse -Force -ErrorAction SilentlyContinue\n"
        "  New-Item -ItemType Directory -Path $replacement -Force | Out-Null\n"
        "  Set-UpdateState 'applying' 'Extracting the update'\n"
        "  Expand-Archive -LiteralPath $archive -DestinationPath $replacement -Force\n"
        f"  if (-not (Test-Path (Join-Path $replacement '{APP_ARTIFACT}.exe'))) {{ throw 'The update ZIP does not contain the expected executable.' }}\n"
        # Inno Setup owns these files. The portable ZIP deliberately does not
        # contain them, so retain them while swapping the app payload.
        "  Get-ChildItem -LiteralPath $install -Filter 'unins*' -File -ErrorAction SilentlyContinue | Copy-Item -Destination $replacement -Force\n"
        "  Remove-Item $backup -Recurse -Force -ErrorAction SilentlyContinue\n"
        "  Set-UpdateState 'applying' 'Replacing the previous version'\n"
        "  Move-WithRetry $install $backup\n"
        "  try { Move-WithRetry $replacement $install } catch { Move-WithRetry $backup $install; throw }\n"
        "  Set-UpdateState 'restarting' 'Starting the updated app'\n"
        f"  Start-Process -FilePath (Join-Path $install '{APP_ARTIFACT}.exe') -WorkingDirectory $install -ErrorAction Stop\n"
        "  Remove-Item $backup -Recurse -Force -ErrorAction SilentlyContinue\n"
        "  Remove-Item $stateFile -Force -ErrorAction SilentlyContinue\n"
        "} catch {\n"
        "  $message = ($_ | Out-String).Trim()\n"
        "  Set-Content -LiteralPath $diagnostic -Value $message -Encoding utf8\n"
        "  Set-UpdateState 'failed' $message\n"
        "  if ((Test-Path $backup) -and -not (Test-Path $install)) { Move-Item -LiteralPath $backup -Destination $install -ErrorAction SilentlyContinue }\n"
        "  exit 1\n"
        "}\n",
        encoding="utf-8",
    )
    _write_update_state("preparing", "Update download verified; waiting for WizZ Desktop to close")
    return script


def launch_staged_update(script: Path) -> None:
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), str(os.getpid())],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
