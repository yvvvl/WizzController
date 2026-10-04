"""Staged, checksum-verified self-update support for packaged desktop builds."""
from __future__ import annotations

import hashlib
import json
import os
import platform as host_platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

from app_meta import APP_ARTIFACT
from config.paths import config_dir
from .update_checker import ReleaseInfo


class UpdateInstallError(RuntimeError):
    pass


def update_state_path() -> Path:
    """State shared by the app and its detached platform updater."""
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
        # Windows PowerShell 5 writes UTF-8 JSON with a BOM when using
        # Set-Content -Encoding utf8.
        state = json.loads(update_state_path().read_text(encoding="utf-8-sig"))
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
        (sys.platform.startswith("win") or sys.platform.startswith("linux"))
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
        # The app is commonly launched with its install directory as the
        # process working directory. PowerShell inherits it, which prevents
        # Windows from renaming that directory even after the app exits.
        "Set-Location -LiteralPath $PSScriptRoot\n"
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
        "  if (Test-Path $backup) {\n"
        "    $failedInstall = $install + '.failed'\n"
        "    Remove-Item $failedInstall -Recurse -Force -ErrorAction SilentlyContinue\n"
        "    if (Test-Path $install) { Move-WithRetry $install $failedInstall }\n"
        "    try { Move-WithRetry $backup $install } catch {\n"
        "      if ((Test-Path $failedInstall) -and -not (Test-Path $install)) { Move-WithRetry $failedInstall $install }\n"
        "      throw\n"
        "    }\n"
        "    Remove-Item $failedInstall -Recurse -Force -ErrorAction SilentlyContinue\n"
        "  }\n"
        "  exit 1\n"
        "}\n",
        encoding="utf-8",
    )
    _write_update_state("preparing", "Update download verified; waiting for WizZ Desktop to close")
    return script


def stage_linux_update(release: ReleaseInfo) -> Path:
    """Download and verify a native Linux bundle and prepare its safe swap helper."""
    if not sys.platform.startswith("linux"):
        raise UpdateInstallError("La actualización Linux sólo está disponible en Linux.")
    if not can_self_update():
        raise UpdateInstallError(
            "La actualización automática requiere una instalación Linux empaquetada con permisos de escritura."
        )
    if not release.download_url or not release.checksum_url:
        raise UpdateInstallError("La release no incluye el paquete Linux de esta arquitectura y su SHA-256.")

    install_dir = packaged_install_dir()
    assert install_dir is not None
    version = re.sub(r"[^A-Za-z0-9._-]", "_", release.version)
    # Keep the staged replacement beside the install so the final directory
    # swap stays on one filesystem, even when XDG config and data are mounted
    # separately. Update status itself remains in the persistent config area.
    stage = install_dir.parent / f".{APP_ARTIFACT}-updates" / version
    stage.mkdir(parents=True, exist_ok=True)
    archive = stage / f"{APP_ARTIFACT}-update.tar.gz"
    expected = _read_sha256(release.checksum_url)
    actual = _download(release.download_url, archive)
    if actual != expected:
        archive.unlink(missing_ok=True)
        raise UpdateInstallError("La verificación SHA-256 falló; la actualización fue descartada.")

    replacement = stage / "replacement"
    shutil.rmtree(replacement, ignore_errors=True)
    replacement.mkdir(parents=True)
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            # Python's data filter rejects absolute paths, traversal and unsafe
            # links before extraction into this private staging directory.
            bundle.extractall(replacement, filter="data")
    except (OSError, tarfile.TarError, ValueError) as exc:
        shutil.rmtree(replacement, ignore_errors=True)
        raise UpdateInstallError("El paquete Linux no se pudo extraer de forma segura.") from exc

    executable = replacement / APP_ARTIFACT
    build_info = replacement / "BUILD_INFO.json"
    if not executable.is_file() or not build_info.is_file():
        shutil.rmtree(replacement, ignore_errors=True)
        raise UpdateInstallError("El paquete Linux no contiene el ejecutable o sus metadatos.")
    try:
        metadata = json.loads(build_info.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError("Build metadata must be an object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        shutil.rmtree(replacement, ignore_errors=True)
        raise UpdateInstallError("Los metadatos del paquete Linux no son válidos.") from exc
    if (
        str(metadata.get("artifact") or "") != APP_ARTIFACT
        or str(metadata.get("version") or "").lstrip("v") != release.version.lstrip("v")
        or str(metadata.get("platform") or "").lower() != "linux"
        or str(metadata.get("architecture") or "").lower() != (
            "arm64" if host_platform.machine().strip().lower() in {"aarch64", "arm64"} else "x64"
        )
    ):
        shutil.rmtree(replacement, ignore_errors=True)
        raise UpdateInstallError("Los metadatos del paquete no coinciden con la actualización solicitada.")
    executable.chmod(executable.stat().st_mode | 0o111)

    script = stage / "apply-update.sh"
    backup = install_dir.with_name(f".{install_dir.name}.backup-{version}")
    state_file = update_state_path()
    diagnostic = stage / "update-error.log"
    q = shlex.quote
    script.write_text(
        "#!/usr/bin/env bash\n"
        "set -Eeuo pipefail\n"
        f"install={q(str(install_dir))}\n"
        f"replacement={q(str(replacement))}\n"
        f"backup={q(str(backup))}\n"
        f"state_file={q(str(state_file))}\n"
        f"diagnostic={q(str(diagnostic))}\n"
        "process_id=\"${1:?missing process id}\"\n"
        "backup_created=0\n"
        "cd -- \"$(dirname -- \"$replacement\")\"\n"
        "write_state() { printf '{\"state\":\"%s\",\"updated_at\":%s}\\n' \"$1\" \"$(date +%s)\" > \"$state_file\"; }\n"
        "rollback() {\n"
        "  status=$?\n"
        "  if [[ $status -ne 0 ]]; then\n"
        "    printf 'Update helper failed (exit %s)\\n' \"$status\" > \"$diagnostic\"\n"
        "    write_state failed || true\n"
        "    if [[ $backup_created -eq 1 && -d $backup ]]; then\n"
        "      failed=\"${install}.failed\"\n"
        "      rm -rf -- \"$failed\"\n"
        "      [[ ! -e $install ]] || mv -- \"$install\" \"$failed\"\n"
        "      mv -- \"$backup\" \"$install\"\n"
        "      rm -rf -- \"$failed\"\n"
        "    fi\n"
        "  fi\n"
        "}\n"
        "trap rollback EXIT\n"
        "write_state applying\n"
        "while kill -0 \"$process_id\" 2>/dev/null; do sleep 0.25; done\n"
        "[[ -x $replacement/WizZDesktop && -f $replacement/BUILD_INFO.json ]] || { echo 'Validated replacement bundle is incomplete' > \"$diagnostic\"; exit 1; }\n"
        "[[ ! -e $backup ]] || { echo 'A previous update backup exists; refusing to overwrite it' > \"$diagnostic\"; exit 1; }\n"
        "mv -- \"$install\" \"$backup\"\n"
        "backup_created=1\n"
        "mv -- \"$replacement\" \"$install\"\n"
        "write_state restarting\n"
        "nohup \"$install/WizZDesktop\" </dev/null >/dev/null 2>&1 &\n"
        "new_pid=$!\n"
        "sleep 2\n"
        "kill -0 \"$new_pid\" 2>/dev/null || { echo 'Updated app did not stay running; restoring the previous version' > \"$diagnostic\"; exit 1; }\n"
        "rm -rf -- \"$backup\"\n"
        "rm -f -- \"$state_file\"\n"
        "trap - EXIT\n",
        encoding="utf-8",
    )
    script.chmod(0o700)
    _write_update_state("preparing", "Verified Linux update is ready; waiting for WizZ Desktop to close")
    return script


def launch_staged_update(script: Path) -> None:
    if sys.platform.startswith("win"):
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), str(os.getpid())],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            cwd=str(script.parent),
        )
    elif sys.platform.startswith("linux"):
        subprocess.Popen(
            ["bash", str(script), str(os.getpid())],
            cwd=str(script.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    else:
        raise UpdateInstallError("La actualización automática no está disponible en este sistema operativo.")
