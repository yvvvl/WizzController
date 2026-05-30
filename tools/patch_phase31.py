from __future__ import annotations

import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path.cwd().resolve()


def backup(path: pathlib.Path) -> None:
    if path.exists():
        dst = path.with_suffix(path.suffix + ".phase31.bak")
        if not dst.exists():
            shutil.copy2(path, dst)


def ensure_requirements() -> None:
    req = ROOT / "requirements.txt"
    if not req.exists():
        req.write_text("flet==0.85.2\n", encoding="utf-8")
    backup(req)
    text = req.read_text(encoding="utf-8")
    adds = []
    if "pystray" not in text.lower():
        adds.append("pystray>=0.19.5")
    if "pillow" not in text.lower() and "PIL" not in text:
        adds.append("Pillow>=10.0.0")
    if adds:
        text = text.rstrip() + "\n\n# --- Bandeja / segundo plano ---\n" + "\n".join(adds) + "\n"
        req.write_text(text, encoding="utf-8")


def patch_main() -> None:
    main = ROOT / "main.py"
    if not main.exists():
        print("[phase31] main.py no encontrado; se omite patch de bandeja")
        return
    backup(main)
    text = main.read_text(encoding="utf-8")

    if "AppRuntimeManager" not in text:
        text = text.replace(
            "from ui.theme import Theme\n",
            "from ui.theme import Theme\nfrom config.app_runtime_manager import AppRuntimeManager\nfrom core.background.tray_service import TrayService, install_window_handlers\n",
        )

    if "# PHASE31_RUNTIME_TRAY" not in text:
        marker = "        app = WizzApp(page, wiz)\n"
        if marker in text:
            text = text.replace(
                marker,
                marker
                + "        # PHASE31_RUNTIME_TRAY\n"
                + "        runtime = AppRuntimeManager()\n"
                + "        tray = None\n"
                + "        if runtime.get('tray_enabled', True):\n"
                + "            try:\n"
                + "                tray = TrayService(page, wiz, app, runtime)\n"
                + "                tray.start()\n"
                + "                install_window_handlers(page, tray, runtime)\n"
                + "            except Exception as _tray_error:\n"
                + "                logging.debug(f'[Tray] no iniciado: {_tray_error}')\n",
            )
        else:
            print("[phase31] No pude encontrar 'app = WizzApp(page, wiz)' en main.py")

    if "# PHASE31_OPEN_MINIMIZED" not in text:
        marker = "        page.update()\n\n        wiz.start()\n"
        if marker in text:
            text = text.replace(
                marker,
                "        page.update()\n"
                + "        # PHASE31_OPEN_MINIMIZED\n"
                + "        try:\n"
                + "            if runtime.get('open_minimized', False) and tray is not None:\n"
                + "                tray.hide_window()\n"
                + "        except Exception:\n"
                + "            pass\n\n"
                + "        wiz.start()\n",
            )

    main.write_text(text, encoding="utf-8")


def clean_pycache() -> None:
    for d in ROOT.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)
    for f in ROOT.rglob("*.pyc"):
        try:
            f.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    ensure_requirements()
    patch_main()
    clean_pycache()
    print("[phase31] Patch aplicado.")
