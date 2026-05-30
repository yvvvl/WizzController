from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def patch_app() -> None:
    path = ROOT / "ui" / "app.py"
    if not path.exists():
        print("[Phase38] ui/app.py no existe; se omite navegación de Rutinas.")
        return
    text = read(path)
    if "routines_panel import RoutinesPanel" not in text:
        marker = "from ui.components.settings_panel import SettingsPanel"
        if marker in text:
            text = text.replace(marker, marker + "\nfrom ui.components.routines_panel import RoutinesPanel")
        else:
            text = text.replace("import flet as ft", "import flet as ft\nfrom ui.components.routines_panel import RoutinesPanel")

    if "RoutinesPanel(self.wiz)" not in text:
        # Insertar antes de Ajustes si existe, porque las destinaciones deben mantener el mismo orden.
        if "SettingsPanel(self.wiz)" in text:
            text = text.replace("SettingsPanel(self.wiz)", "RoutinesPanel(self.wiz),\n            SettingsPanel(self.wiz)", 1)
        else:
            # Fallback: después de ScenesPanel.
            text = text.replace("ScenesPanel(self.wiz)", "ScenesPanel(self.wiz),\n            RoutinesPanel(self.wiz)", 1)

    if 'label="Rutinas"' not in text:
        dest = '''                ft.NavigationRailDestination(
                    icon=ft.Icons.ROCKET_LAUNCH_OUTLINED, selected_icon=ft.Icons.ROCKET_LAUNCH_ROUNDED, label="Rutinas"),
'''
        # Preferimos insertarlo antes de Ajustes.
        pattern = re.compile(
            r"(\s*ft\.NavigationRailDestination\(\s*icon=ft\.Icons\.SETTINGS[^\n]*\n\s*selected_icon=ft\.Icons\.SETTINGS[^\n]*label=\"Ajustes\"\),)",
            re.S,
        )
        if pattern.search(text):
            text = pattern.sub(dest + r"\1", text, count=1)
        elif 'label="Ajustes"' in text:
            idx = text.find('label="Ajustes"')
            start = text.rfind("ft.NavigationRailDestination", 0, idx)
            if start != -1:
                line_start = text.rfind("\n", 0, start) + 1
                text = text[:line_start] + dest + text[line_start:]
        else:
            # Último fallback: antes del cierre de destinations.
            text = text.replace("            ],\n            on_change=self._on_nav,", dest + "            ],\n            on_change=self._on_nav,", 1)

    write(path, text)
    print("[Phase38] ui/app.py parcheado con panel Rutinas.")


def append_once(path: pathlib.Path, marker: str, code: str, label: str) -> None:
    if not path.exists():
        print(f"[Phase38] {path} no existe; se omite {label}.")
        return
    text = read(path)
    if marker in text:
        print(f"[Phase38] {label} ya aplicado.")
        return
    write(path, text.rstrip() + "\n\n" + code.strip() + "\n")
    print(f"[Phase38] {label} aplicado.")


def patch_hotkeys() -> None:
    path = ROOT / "config" / "hotkeys_manager.py"
    code = r'''
# ---------------------------------------------------------------------------
# Phase 38: Rutinas compuestas en Hotkeys.
# Extensión no invasiva para no romper el panel existente.
# ---------------------------------------------------------------------------
try:
    from config.routines_manager import RoutinesManager as _Phase38RoutinesManager
    from core.action_sequence import ActionSequenceExecutor as _Phase38ActionSequenceExecutor

    if not hasattr(HotkeysManager, "_phase38_routines_patch"):
        _phase38_orig_list_actions = HotkeysManager.list_actions
        _phase38_orig_execute_action = HotkeysManager.execute_action

        def _phase38_list_actions(self):
            actions = list(_phase38_orig_list_actions(self))
            try:
                for routine in _Phase38RoutinesManager().get_routines():
                    uid = routine.get("id")
                    if uid:
                        actions.append({
                            "id": f"routine_{uid}",
                            "name": routine.get("name", "Rutina"),
                            "group": "Rutinas",
                        })
            except Exception:
                pass
            return actions

        def _phase38_execute_action(self, action_id: str) -> None:
            if isinstance(action_id, str) and action_id.startswith("routine_"):
                uid = action_id.split("_", 1)[1]
                _Phase38ActionSequenceExecutor(self.wiz).execute_routine(uid, threaded=True)
                return
            return _phase38_orig_execute_action(self, action_id)

        HotkeysManager.list_actions = _phase38_list_actions
        HotkeysManager.execute_action = _phase38_execute_action
        HotkeysManager._phase38_routines_patch = True
except Exception:
    pass
'''
    append_once(path, "Phase 38: Rutinas compuestas en Hotkeys", code, "hotkeys + rutinas")


def patch_voice_intent() -> None:
    path = ROOT / "core" / "voice" / "intent_parser.py"
    code = r'''
# ---------------------------------------------------------------------------
# Phase 38: Rutinas compuestas en Voz.
# Se agrega sin reemplazar el parser existente.
# ---------------------------------------------------------------------------
try:
    from config.routines_manager import RoutinesManager as _Phase38RoutinesManager
    from core.action_sequence import ActionSequenceExecutor as _Phase38ActionSequenceExecutor

    if not hasattr(VoiceActionRegistry, "_phase38_routines_patch"):
        _phase38_orig_build_actions = VoiceActionRegistry.build_actions
        _phase38_orig_execute = VoiceActionRegistry.execute

        def _phase38_build_actions(self):
            actions = list(_phase38_orig_build_actions(self))
            try:
                for routine in _Phase38RoutinesManager().get_routines():
                    uid = routine.get("id")
                    if uid:
                        actions.append({
                            "id": f"routine.{uid}",
                            "category": "Rutinas",
                            "name": routine.get("name", "Rutina"),
                            "type": "routine",
                            "value": uid,
                        })
            except Exception:
                pass
            return actions

        def _phase38_execute(self, action):
            if isinstance(action, dict) and action.get("type") == "routine":
                uid = str(action.get("value") or "")
                _Phase38ActionSequenceExecutor(self.wiz).execute_routine(uid, threaded=True)
                return str(action.get("name") or "Rutina")
            return _phase38_orig_execute(self, action)

        VoiceActionRegistry.build_actions = _phase38_build_actions
        VoiceActionRegistry.execute = _phase38_execute
        VoiceActionRegistry._phase38_routines_patch = True
except Exception:
    pass
'''
    append_once(path, "Phase 38: Rutinas compuestas en Voz", code, "voz + rutinas")


def main() -> None:
    patch_app()
    patch_hotkeys()
    patch_voice_intent()


if __name__ == "__main__":
    main()
