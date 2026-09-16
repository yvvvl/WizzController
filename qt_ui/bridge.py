from __future__ import annotations

import json
import threading
from typing import Any

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    Property,
    QTimer,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication
from config.custom_scenes_manager import CustomScenesManager
from config.favorites_manager import FavoritesManager
from config.hotkeys_manager import HotkeysManager
from config.routines_manager import RoutinesManager
from config.app_runtime_manager import AppRuntimeManager
from app_meta import APP_PRODUCT, APP_VERSION, display_version
from core.action_sequence import ActionSequenceExecutor
from core import wiz_scenes
from core.update_checker import ReleaseInfo, is_update_available
from core.update_client import ReleaseClient
from core.update_installer import (
    UpdateInstallError,
    can_self_update,
    launch_staged_update,
    stage_windows_update,
)
from localization import RuntimeLanguagePreference, get_manager, translated_scene_group, translated_scene_name


class LightListModel(QAbstractListModel):
    NameRole = Qt.ItemDataRole.UserRole + 1
    IpRole = NameRole + 1
    OnRole = IpRole + 1
    BrightnessRole = OnRole + 1
    ColorRole = BrightnessRole + 1
    SelectedRole = ColorRole + 1
    OnlineRole = SelectedRole + 1
    ModuleRole = OnlineRole + 1

    def __init__(self) -> None:
        super().__init__()
        self._items: list[dict[str, Any]] = []

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.NameRole: QByteArray(b"displayName"),
            self.IpRole: QByteArray(b"address"),
            self.OnRole: QByteArray(b"isOn"),
            self.BrightnessRole: QByteArray(b"brightness"),
            self.ColorRole: QByteArray(b"lightColor"),
            self.SelectedRole: QByteArray(b"isSelected"),
            self.OnlineRole: QByteArray(b"isOnline"),
            self.ModuleRole: QByteArray(b"moduleName"),
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {
            self.NameRole: item["name"],
            self.IpRole: item["ip"],
            self.OnRole: item["isOn"],
            self.BrightnessRole: item["brightness"],
            self.ColorRole: item["lightColor"],
            self.SelectedRole: item["selected"],
            self.OnlineRole: item.get("online", False),
            self.ModuleRole: item.get("module", ""),
        }
        return mapping.get(role)

    def replace(self, items: list[dict[str, Any]]) -> None:
        # Controller acknowledgements refresh state frequently.  When the
        # physical list is unchanged, updating rows in place preserves a
        # QML ListView's contentX (and therefore the carousel page).
        existing_ips = [str(item.get("ip") or "") for item in self._items]
        incoming_ips = [str(item.get("ip") or "") for item in items]
        if existing_ips == incoming_ips:
            for row, item in enumerate(items):
                if self._items[row] == item:
                    continue
                self._items[row] = item
                index = self.index(row, 0)
                self.dataChanged.emit(
                    index,
                    index,
                    [
                        self.NameRole, self.IpRole, self.OnRole,
                        self.BrightnessRole, self.ColorRole, self.SelectedRole,
                        self.OnlineRole, self.ModuleRole,
                    ],
                )
            return
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def update_selection(self, selected_ips: set[str]) -> None:
        """Update only selection roles, preserving a view's scroll position."""
        for row, item in enumerate(self._items):
            selected = str(item.get("ip") or "") in selected_ips
            if bool(item.get("selected")) == selected:
                continue
            item["selected"] = selected
            index = self.index(row, 0)
            self.dataChanged.emit(index, index, [self.SelectedRole])


class EntryListModel(QAbstractListModel):
    TitleRole = Qt.ItemDataRole.UserRole + 1
    SubtitleRole = TitleRole + 1
    ColorRole = SubtitleRole + 1
    UidRole = ColorRole + 1
    KindRole = UidRole + 1
    ValueRole = KindRole + 1

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.TitleRole: QByteArray(b"title"),
            self.SubtitleRole: QByteArray(b"subtitle"),
            self.ColorRole: QByteArray(b"entryColor"),
            self.UidRole: QByteArray(b"uid"),
            self.KindRole: QByteArray(b"kind"),
            self.ValueRole: QByteArray(b"rawValue"),
        }

    def __init__(self) -> None:
        super().__init__()
        self._items: list[dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        return {
            self.TitleRole: item.get("title", ""), self.SubtitleRole: item.get("subtitle", ""),
            self.ColorRole: item.get("entryColor", "#a78bfa"), self.UidRole: item.get("uid", ""),
            self.KindRole: item.get("kind", ""), self.ValueRole: item.get("rawValue", ""),
        }.get(role)

    def replace(self, items: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()


class WizzBridge(QObject):
    """Small Qt-facing view model; WiZ transport remains owned by Python."""

    stateChanged = Signal()
    colorChanged = Signal()
    modeChanged = Signal()
    brightnessChanged = Signal()
    whiteChanged = Signal()
    statusChanged = Signal()
    themeChanged = Signal()
    hotkeysChanged = Signal()
    quickActionsChanged = Signal()
    hotkeyActionsLoaded = Signal(list)
    favoriteStateChanged = Signal()
    updateChanged = Signal()
    updateResultReceived = Signal(object, str)
    updateInstallResultReceived = Signal(str, str)
    hotkeyCaptured = Signal(str)
    navigateRequested = Signal(int)
    controllerStateReceived = Signal(dict)
    languageChanged = Signal()

    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self.lights = LightListModel()
        self.entries = EntryListModel()
        self.favorites = EntryListModel()
        self.recents = EntryListModel()
        self.scenes = EntryListModel()
        self.custom_scenes = EntryListModel()
        self.routines = EntryListModel()
        self.hotkeys = EntryListModel()
        self._favorites_manager = FavoritesManager()
        self._scenes_manager = CustomScenesManager()
        self._routines_manager = RoutinesManager()
        self._hotkeys_manager = HotkeysManager(
            controller, auto_apply=not bool(getattr(controller, "is_virtual", False))
        )
        self._hotkey_actions_cache: list[dict[str, Any]] = []
        self._hotkey_actions_loading = False
        # Keep Qt's appearance preferences in the same durable runtime store
        # used by the Flet shell.  The two clients can now be alternated
        # without each one silently resetting the user's visual choices.
        self._runtime = AppRuntimeManager()
        self._i18n = get_manager()
        self._i18n.set_preference(RuntimeLanguagePreference(self._runtime).load())
        self._executor = ActionSequenceExecutor(controller)
        self._state: dict[str, Any] = {}
        self._main_window: Any = None
        self._optimistic_color = ""
        self._optimistic_brightness: int | None = None
        self._optimistic_kelvin: int | None = None
        self._color_mode = "white"
        stored_theme = str(self._runtime.get("ui_theme", "midnight") or "midnight").lower()
        # Consolidate legacy near-duplicate choices into the shorter Qt
        # palette.  This preserves a user's intended mood while ensuring the
        # selector always has one clear selected option.
        stored_theme = {
            "system": "midnight", "dark": "midnight",
            "aurora": "ocean", "sapphire": "ocean",
        }.get(stored_theme, stored_theme)
        self._theme = stored_theme or "midnight"
        self._reduced_motion = bool(self._runtime.get("reduced_motion", False))
        self._live_brand_accent = bool(self._runtime.get("live_brand_accent", True))
        self._quick_panel_placement = str(self._runtime.get("quick_panel_placement", "bottom-right") or "bottom-right")
        self._quick_action_catalog: list[dict[str, str]] = [
            {"key": "cinema", "title_es": "TV / Cine", "title_en": "TV / Cinema", "glyph": "\ue7f4", "color": "#9b6cff"},
            {"key": "reading", "title_es": "Lectura", "title_en": "Reading", "glyph": "\ue82d", "color": "#fbbf24"},
            {"key": "relax", "title_es": "Relax", "title_en": "Relax", "glyph": "\ue8cb", "color": "#34d399"},
            {"key": "party", "title_es": "Fiesta", "title_en": "Party", "glyph": "\ue7fc", "color": "#ec4899"},
            {"key": "warm", "title_es": "Cálido", "title_en": "Warm", "glyph": "\ue706", "color": "#ff8a3d"},
            {"key": "cool", "title_es": "Frío", "title_en": "Cool", "glyph": "\ue9ca", "color": "#38bdf8"},
            {"key": "reset", "title_es": "Restablecer", "title_en": "Reset", "glyph": "\ue777", "color": "#77849e"},
            {"key": "off", "title_es": "Apagar", "title_en": "Turn off", "glyph": "\ue7e8", "color": "#ef6b73"},
        ]
        known_quick_actions = {item["key"] for item in self._quick_action_catalog}
        stored_quick_actions = self._runtime.get("quick_actions", [])
        self._quick_actions = [str(key) for key in stored_quick_actions if str(key) in known_quick_actions][:6]
        if not self._quick_actions:
            self._quick_actions = ["warm", "reading", "cool", "relax", "party", "off"]
        self._update_status = "Comprueba si hay una versión nueva cuando lo necesites."
        self._update_url = ""
        self._update_in_progress = False
        stored_channel = str(self._runtime.get("update_channel", "stable") or "stable").lower()
        self._update_channel = stored_channel if stored_channel in {"stable", "beta"} else "stable"
        self._available_release: ReleaseInfo | None = None
        self._pending_brightness = 100
        self._pending_rgb: tuple[int, int, int] | None = None
        self._pending_white: int | None = None
        self._pending_scene: tuple[int, int] | None = None
        self._recent_items: list[dict[str, Any]] = []
        self._brightness_timer = QTimer(self)
        self._brightness_timer.setSingleShot(True)
        self._brightness_timer.setInterval(55)
        self._brightness_timer.timeout.connect(self._flush_brightness)
        self._rgb_timer = QTimer(self)
        self._rgb_timer.setSingleShot(True)
        self._rgb_timer.setInterval(33)
        self._rgb_timer.timeout.connect(self._flush_rgb)
        self._white_timer = QTimer(self)
        self._white_timer.setSingleShot(True)
        self._white_timer.setInterval(40)
        self._white_timer.timeout.connect(self._flush_white)
        self._scene_timer = QTimer(self)
        self._scene_timer.setSingleShot(True)
        self._scene_timer.setInterval(80)
        self._scene_timer.timeout.connect(self._flush_scene)
        self._model_refresh_timer = QTimer(self)
        self._model_refresh_timer.setSingleShot(True)
        self._model_refresh_timer.setInterval(220)
        self._model_refresh_timer.timeout.connect(self.refresh)
        self.controllerStateReceived.connect(self._apply_controller_state)
        self.updateResultReceived.connect(self._apply_update_result)
        self.updateInstallResultReceived.connect(self._apply_update_install_result)
        self.hotkeyActionsLoaded.connect(self._apply_hotkey_actions)
        self.controller.set_callback(self._receive_controller_state)
        self.refresh()
        QTimer.singleShot(0, self.refreshHotkeyActions)

    def shutdown(self) -> None:
        self._hotkeys_manager.stop()

    def setMainWindow(self, window: Any) -> None:
        """Attach the QML shell so floating UI can target its monitor."""
        self._main_window = window

    @Slot(result="QVariantMap")
    def quickPanelAvailableArea(self) -> dict[str, int]:
        """Return the monitor work area, excluding its taskbar or dock.

        QML exposes virtual desktop bounds reliably, but not the per-screen
        work area on every Windows backend.  Asking QScreen here keeps the
        quick panel flush with a taskbar on any edge and any monitor.
        """
        window = self._main_window
        screen = window.screen() if window is not None else QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry() if screen is not None else None
        if geometry is None:
            return {"x": 0, "y": 0, "width": 1280, "height": 720}
        return {
            "x": geometry.x(), "y": geometry.y(),
            "width": geometry.width(), "height": geometry.height(),
        }

    @staticmethod
    def _state_for_bulb(bulb: dict[str, Any]) -> dict[str, Any]:
        # ``state`` in detailed device summaries is the compact on/off flag;
        # prefer the full pilot reply when available so RGB light colour is
        # never discarded before the QML shell can render it.
        raw = bulb.get("raw_state", bulb.get("state"))
        state = dict(raw) if isinstance(raw, dict) else {
            "state": bool(raw),
            "dimming": bulb.get("dimming", 100),
            "temp": bulb.get("temp", 4000),
        }
        # The pilot's r/g/b channels are the freshest source and preserve
        # saturated colours exactly.  ``color_rgb`` is a calculated fallback
        # for older summaries which do not include the raw pilot payload.
        rgb = bulb.get("color_rgb")
        if (
            not all(key in state for key in ("r", "g", "b"))
            and isinstance(rgb, (tuple, list))
            and len(rgb) == 3
        ):
            state["r"], state["g"], state["b"] = rgb
        return state

    @staticmethod
    def _display_color(state: dict[str, Any]) -> str:
        if not bool(state.get("state", False)):
            return "#697899"
        if all(key in state for key in ("r", "g", "b")):
            return "#{:02x}{:02x}{:02x}".format(
                int(state["r"]), int(state["g"]), int(state["b"])
            )
        temp = int(state.get("temp", 4000) or 4000)
        if temp <= 3000:
            return "#ffd9a0"
        if temp >= 5500:
            return "#d8efff"
        return "#fff0dc"

    def _receive_controller_state(self, state: dict[str, Any]) -> None:
        self.controllerStateReceived.emit(dict(state or {}))

    @Slot(dict)
    def _apply_controller_state(self, state: dict[str, Any]) -> None:
        # A Qt signal queues this update onto the UI thread when WiZ invokes
        # the callback from its worker.
        previous_state = self._state
        self._state = dict(state or {})
        confirmed_dimming = int(self._state.get("dimming", 100) or 100)
        if (
            self._optimistic_brightness == confirmed_dimming
            and not self._brightness_timer.isActive()
        ):
            self._optimistic_brightness = None
        confirmed_kelvin = int(self._state.get("temp", 4000) or 4000)
        if self._optimistic_kelvin == confirmed_kelvin and not self._white_timer.isActive():
            self._optimistic_kelvin = None
        rgb = tuple(self._state.get(key) for key in ("r", "g", "b"))
        rgb_streaming = self._pending_rgb is not None or self._rgb_timer.isActive()
        if not rgb_streaming and all(isinstance(value, (int, float)) for value in rgb):
            self._optimistic_color = "#{:02x}{:02x}{:02x}".format(
                *(int(value) for value in rgb)
            )

        # Keep pointer-driven previews cheap. Rebuilding every list model here
        # stalls Qt's render loop when a controller acknowledges every sample.
        if bool(previous_state.get("state", False)) != bool(self._state.get("state", False)):
            self.stateChanged.emit()
        if not rgb_streaming and rgb != tuple(previous_state.get(key) for key in ("r", "g", "b")):
            self.colorChanged.emit()
        if (
            self._pending_brightness is None
            and confirmed_dimming != int(previous_state.get("dimming", 100) or 100)
        ):
            self.brightnessChanged.emit()
        if (
            self._pending_white is None
            and confirmed_kelvin != int(previous_state.get("temp", 4000) or 4000)
        ):
            self.whiteChanged.emit()
        self._model_refresh_timer.start()

    @Slot()
    def refresh(self) -> None:
        bulbs = self.controller.get_bulbs_detailed()
        target = self.controller.get_target_config()
        selected = set(target.get("selected_ips") or [])
        items: list[dict[str, Any]] = []
        for bulb in bulbs:
            state = self._state_for_bulb(bulb)
            ip = str(bulb.get("ip") or "")
            items.append(
                {
                    "name": str(bulb.get("name") or ip),
                    "ip": ip,
                    "isOn": bool(state.get("state", False)),
                    "brightness": int(state.get("dimming", 100) or 100),
                    "lightColor": self._display_color(state),
                    "selected": ip in selected,
                    "online": bool(bulb.get("online", False)),
                    "module": str(bulb.get("module") or bulb.get("label") or ""),
                }
            )
        self.lights.replace(items)
        self._refresh_library_models()
        self._state = dict(self.controller.get_state() or self._state)
        confirmed_dimming = int(self._state.get("dimming", 100) or 100)
        if (
            self._optimistic_brightness == confirmed_dimming
            and not self._brightness_timer.isActive()
        ):
            self._optimistic_brightness = None
        confirmed_kelvin = int(self._state.get("temp", 4000) or 4000)
        if self._optimistic_kelvin == confirmed_kelvin and not self._white_timer.isActive():
            self._optimistic_kelvin = None
        rgb = tuple(self._state.get(key) for key in ("r", "g", "b"))
        if all(isinstance(value, (int, float)) for value in rgb):
            self._optimistic_color = "#{:02x}{:02x}{:02x}".format(*(int(value) for value in rgb))
        self.stateChanged.emit()
        self.colorChanged.emit()
        self.modeChanged.emit()
        self.brightnessChanged.emit()
        self.whiteChanged.emit()
        self.statusChanged.emit()

    def _refresh_library_models(self) -> None:
        self._favorites_manager.seed_defaults()
        favorites = self._favorites_manager.get_favorites()
        self.favorites.replace([self._favorite_entry(item) for item in favorites])
        self.favoriteStateChanged.emit()
        built_in_scenes = [
            {"title": scene.name, "subtitle": "WiZ · " + ("dinámica" if scene.dynamic else "estática"),
             "entryColor": scene.color, "uid": f"wiz:{scene.id}", "kind": "scene"}
            for scene in wiz_scenes.CATALOG.values()
        ]
        custom_scenes = [
            {"title": str(item.get("name") or "Escena"), "subtitle": str(item.get("mode") or "rgb").upper(),
             "entryColor": self._custom_scene_color(item), "uid": str(item.get("id") or ""),
             "kind": str(item.get("mode") or "rgb"),
             "rawValue": json.dumps(item.get("value"), separators=(",", ":"))}
            for item in self._scenes_manager.get_scenes()
        ]
        self.scenes.replace(built_in_scenes + custom_scenes)
        self.custom_scenes.replace(custom_scenes)
        self.routines.replace([
            {"title": str(item.get("name") or "Rutina"),
             "subtitle": (
                 f"{str(item.get('description') or '').strip()} · {len(item.get('actions') or [])} pasos"
                 if str(item.get("description") or "").strip()
                 else f"{len(item.get('actions') or [])} pasos"
             ),
             "entryColor": str(item.get("color") or "#5f91ff"), "uid": str(item.get("id") or ""), "kind": "routine",
             "rawValue": json.dumps({
                 "description": str(item.get("description") or ""),
                 "actions": item.get("actions") or [],
             }, separators=(",", ":"))}
            for item in self._routines_manager.get_routines()
        ])
        self._refresh_hotkey_model()

    def _refresh_hotkey_model(self) -> None:
        self.hotkeys.replace([
            {
                "title": str(row.get("name") or row.get("id") or "Acción"),
                "subtitle": str(row.get("group") or "General"),
                "entryColor": "#5f91ff",
                "uid": str(row.get("id") or ""),
                "kind": "hotkey",
                "rawValue": str(row.get("combo") or ""),
            }
            for row in self._hotkeys_manager.configured_rows()
        ])
        self.hotkeysChanged.emit()

    @Slot()
    def refreshHotkeyActions(self) -> None:
        """Build the dynamic action catalogue off the Qt render thread."""
        if self._hotkey_actions_loading:
            return
        self._hotkey_actions_loading = True

        def worker() -> None:
            try:
                items = [
                    {"id": str(item.get("id") or ""),
                     "name": str(item.get("name") or item.get("id") or "Acción"),
                     "group": str(item.get("group") or "General")}
                    for item in self._hotkeys_manager.list_actions()
                    if item.get("id")
                ]
            except Exception:
                items = []
            self.hotkeyActionsLoaded.emit(items)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(list)
    def _apply_hotkey_actions(self, items: list[dict[str, Any]]) -> None:
        self._hotkey_actions_loading = False
        self._hotkey_actions_cache = list(items)
        self.hotkeysChanged.emit()

    @Property(QObject, constant=True)
    def lightModel(self) -> QObject:
        return self.lights

    @Property(bool, notify=stateChanged)
    def powerOn(self) -> bool:
        return bool(self._state.get("state", False))

    @Property(int, notify=brightnessChanged)
    def brightness(self) -> int:
        if self._optimistic_brightness is not None:
            return int(self._optimistic_brightness)
        return int(self._state.get("dimming", 100) or 100)

    @Property(int, notify=whiteChanged)
    def whiteKelvin(self) -> int:
        if self._optimistic_kelvin is not None:
            return int(self._optimistic_kelvin)
        return int(self._state.get("temp", 4000) or 4000)

    @Property(bool, notify=favoriteStateChanged)
    def currentFavoriteSaved(self) -> bool:
        """Whether the colour/white value currently shown in Color Studio exists.

        The property deliberately describes the real persisted favourite list,
        rather than a QML-only pressed state, so every entry point stays in
        sync after a save, edit or delete.
        """
        if self._color_mode == "white":
            kind, value = "white", str(self.whiteKelvin)
        else:
            kind, value = "rgb", str(self.colorHex or "#ffffff").upper()
        return any(
            str(item.get("type") or "").lower() == kind
            and str(item.get("value", "")).upper() == value.upper()
            for item in self._favorites_manager.get_favorites()
        )

    @Property(int, notify=statusChanged)
    def totalCount(self) -> int:
        return self.lights.rowCount()

    @Property("QVariantList", notify=colorChanged)
    def brandColors(self) -> list[str]:
        """Visible light colours used by the small Qt shell brand accent."""
        colors: list[str] = []
        for item in self.lights._items:
            color = str(item.get("lightColor") or "")
            if bool(item.get("isOn")) and color and color not in colors:
                colors.append(color)
        return colors or ["#6697ff"]

    @Property(str, notify=stateChanged)
    def brandState(self) -> str:
        active = [item for item in self.lights._items if bool(item.get("isOn"))]
        if not active:
            return "Lights off" if self._i18n.language == "en" else "Luces apagadas"
        if len(active) == 1:
            label = "On" if self._i18n.language == "en" else "Encendida"
            return f"{label} · {int(active[0].get('brightness', 100) or 100)}%"
        return f"{len(active)} {'lights active' if self._i18n.language == 'en' else 'luces activas'}"

    @Property(int, notify=statusChanged)
    def selectedCount(self) -> int:
        return sum(1 for item in self.lights._items if item["selected"])

    @Property(str, notify=statusChanged)
    def statusLine(self) -> str:
        count = self.totalCount
        if self._i18n.language == "en":
            return f"{count}/{count} online · RGB + White" if count else "No linked lights"
        return f"{count}/{count} en línea · RGB + Blancos" if count else "Sin luces vinculadas"

    @Property(str, notify=statusChanged)
    def targetLine(self) -> str:
        active = str(self.controller.get_target_config().get("active_ip") or "—")
        mode = str(self.controller.get_target_config().get("mode") or "single")
        if self._i18n.language == "en":
            return f"target: {'All' if mode == 'all' else 'Selection'} · {active}"
        return f"destino: {'Todas' if mode == 'all' else 'Selección'} · {active}"

    @Property(str, notify=statusChanged)
    def targetMode(self) -> str:
        return str(self.controller.get_target_config().get("mode") or "single")

    @Property(str, notify=statusChanged)
    def activeLightIp(self) -> str:
        return str(self.controller.get_target_config().get("active_ip") or "")

    @Slot(str)
    def setTargetMode(self, mode: str) -> None:
        normalized = str(mode or "").strip().lower()
        if normalized not in {"single", "all"}:
            return
        self.controller.set_target_mode(normalized)
        self.refresh()

    @Slot(str)
    def setActiveLight(self, ip: str) -> None:
        clean_ip = str(ip or "").strip()
        if not clean_ip:
            return
        self.controller.set_active_bulb(clean_ip)
        self.refresh()

    @Property(bool, notify=statusChanged)
    def scanInProgress(self) -> bool:
        status = self.controller.get_scan_status()
        return bool(status.get("in_progress", status.get("running", False)))

    @Property(str, notify=statusChanged)
    def scanMessage(self) -> str:
        status = self.controller.get_scan_status()
        if bool(status.get("in_progress", status.get("running", False))):
            return "Buscando ampolletas en tu red…"
        error = str(status.get("error") or "").strip()
        if error:
            return "No se pudo completar la búsqueda: " + error
        found = int(status.get("found", self.totalCount) or 0)
        return f"{found} ampolleta{'s' if found != 1 else ''} detectada{'s' if found != 1 else ''}"

    @Property(int, notify=statusChanged)
    def sliderInterval(self) -> int:
        return int(self.controller.get_target_config().get("slider_interval_ms", 65) or 65)

    @Slot()
    def scanLights(self) -> None:
        self.controller.rescan()
        self.statusChanged.emit()

    @Slot(str, result=bool)
    def addLight(self, ip: str) -> bool:
        added = bool(self.controller.add_bulb_manual(str(ip or "").strip()))
        if added:
            self.refresh()
        return added

    @Slot(str, str, result=bool)
    def renameLight(self, ip: str, name: str) -> bool:
        clean_name = str(name or "").strip()
        if not clean_name:
            return False
        self.controller.rename_bulb(str(ip), clean_name)
        self.refresh()
        return True

    @Slot(str, result=bool)
    def removeLight(self, ip: str) -> bool:
        removed = bool(self.controller.remove_bulb(str(ip)))
        self.refresh()
        return removed

    @Slot(result=int)
    def cleanupOfflineLights(self) -> int:
        removed = int(self.controller.cleanup_offline_bulbs())
        self.refresh()
        return removed

    @Slot(str, result="QVariantMap")
    def deviceInfo(self, ip: str) -> dict[str, Any]:
        """Return a compact, presentation-safe device summary for Qt."""
        address = str(ip or "").strip()
        details: dict[str, Any] = {}
        try:
            getter = getattr(self.controller, "get_device_info", None)
            if callable(getter):
                details = dict(getter(address) or {})
            if not details:
                rows = getattr(self.controller, "get_bulbs_detailed", lambda: [])()
                details = next((dict(item) for item in rows if str(item.get("ip") or item.get("address") or "") == address), {})
        except Exception:
            details = {}
        state = details.get("raw_state") if isinstance(details.get("raw_state"), dict) else details.get("state")
        state = state if isinstance(state, dict) else {}
        capabilities = details.get("capabilities") if isinstance(details.get("capabilities"), dict) else {}
        return {
            "name": str(details.get("name") or details.get("label") or address or "Ampolleta WiZ"),
            "ip": str(details.get("ip") or details.get("address") or address),
            "mac": str(details.get("mac") or "—"),
            "module": str(details.get("module") or details.get("moduleName") or "—"),
            "online": bool(details.get("online", True)),
            "active": bool(details.get("active", False)),
            "brightness": int(state.get("dimming", details.get("dimming", 0)) or 0),
            "kelvin": int(state.get("temp", details.get("temp", 0)) or 0),
            "scene": int(state.get("sceneId", details.get("sceneId", 0)) or 0),
            "rgb": bool(capabilities.get("rgb", details.get("rgb", False))),
            "tunableWhite": bool(capabilities.get("tunable_white", details.get("tunable_white", False))),
            "kelvinMin": int(details.get("kelvin_min", capabilities.get("kelvin_min", 0)) or 0),
            "kelvinMax": int(details.get("kelvin_max", capabilities.get("kelvin_max", 0)) or 0),
            "firmware": str((details.get("system") or {}).get("fwVersion") if isinstance(details.get("system"), dict) else details.get("firmware") or "—"),
        }

    @Slot(int)
    def setSliderInterval(self, milliseconds: int) -> None:
        self.controller.set_slider_interval_ms(int(milliseconds))
        self.statusChanged.emit()

    @Property(str, notify=themeChanged)
    def themeName(self) -> str:
        return self._theme

    @Slot(str)
    def setTheme(self, name: str) -> None:
        normalized = str(name or "midnight").lower()
        if normalized == "system":
            normalized = "midnight"
        if normalized != self._theme:
            self._theme = normalized
            self._runtime.update(ui_theme=normalized)
            self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def reducedMotion(self) -> bool:
        return self._reduced_motion

    @Slot(bool)
    def setReducedMotion(self, enabled: bool) -> None:
        value = bool(enabled)
        if value == self._reduced_motion:
            return
        self._reduced_motion = value
        self._runtime.update(reduced_motion=value)
        self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def liveBrandAccent(self) -> bool:
        return self._live_brand_accent

    @Slot(bool)
    def setLiveBrandAccent(self, enabled: bool) -> None:
        value = bool(enabled)
        if value == self._live_brand_accent:
            return
        self._live_brand_accent = value
        self._runtime.update(live_brand_accent=value)
        self.themeChanged.emit()

    @Property(str, notify=themeChanged)
    def quickPanelPlacement(self) -> str:
        return self._quick_panel_placement

    @Slot(str)
    def setQuickPanelPlacement(self, placement: str) -> None:
        value = str(placement or "bottom-right").lower()
        if value not in {"bottom-right", "bottom-left", "top-right", "top-left"}:
            return
        if value == self._quick_panel_placement:
            return
        self._quick_panel_placement = value
        self._runtime.update(quick_panel_placement=value)
        self.themeChanged.emit()

    @Property("QVariantList", notify=quickActionsChanged)
    def quickActions(self) -> list[dict[str, str]]:
        by_key = {item["key"]: item for item in self._quick_action_catalog}
        return [self._localize_quick_action(by_key[key]) for key in self._quick_actions if key in by_key]

    @Property("QVariantList", notify=languageChanged)
    def quickActionCatalog(self) -> list[dict[str, str]]:
        return [self._localize_quick_action(item) for item in self._quick_action_catalog]

    def _localize_quick_action(self, item: dict[str, str]) -> dict[str, str]:
        localized = dict(item)
        localized["title"] = localized.pop(
            "title_en" if self._i18n.language == "en" else "title_es",
            localized.get("key", ""),
        )
        localized.pop("title_es", None)
        localized.pop("title_en", None)
        return localized

    @Slot(list)
    def setQuickActions(self, actions: list) -> None:
        known = {item["key"] for item in self._quick_action_catalog}
        selected: list[str] = []
        for action in actions or []:
            key = str(action)
            if key in known and key not in selected:
                selected.append(key)
            if len(selected) == 6:
                break
        if not selected or selected == self._quick_actions:
            return
        self._quick_actions = selected
        self._runtime.update(quick_actions=selected)
        self.quickActionsChanged.emit()

    @Property(str, constant=True)
    def appVersion(self) -> str:
        return display_version()

    @Property(str, constant=True)
    def appProduct(self) -> str:
        return APP_PRODUCT

    @Property(str, notify=updateChanged)
    def updateStatus(self) -> str:
        return self._update_status

    @Property(str, notify=updateChanged)
    def updateUrl(self) -> str:
        return self._update_url

    @Property(bool, notify=updateChanged)
    def updateInProgress(self) -> bool:
        return self._update_in_progress

    @Property(str, notify=updateChanged)
    def updateChannel(self) -> str:
        return self._update_channel

    @Property(bool, notify=updateChanged)
    def updateCanInstall(self) -> bool:
        return can_self_update()

    @Property(bool, notify=updateChanged)
    def updateAvailable(self) -> bool:
        return self._available_release is not None

    @Slot(str)
    def setUpdateChannel(self, channel: str) -> None:
        selected = str(channel or "stable").strip().lower()
        if selected not in {"stable", "beta"} or selected == self._update_channel:
            return
        self._update_channel = selected
        self._runtime.set("update_channel", selected)
        self._available_release = None
        self._update_url = ""
        self._update_status = (
            "Canal beta activo. Recibirás versiones preliminares."
            if selected == "beta"
            else "Canal estable activo. Recibirás sólo versiones finales."
        )
        self.updateChanged.emit()

    @Slot()
    def checkUpdates(self) -> None:
        if self._update_in_progress:
            return
        self._update_in_progress = True
        self._update_status = "Buscando actualizaciones…"
        self._update_url = ""
        self._available_release = None
        self.updateChanged.emit()

        def check() -> None:
            try:
                release = ReleaseClient().latest(channel=self._update_channel)
                if release is None:
                    message = "No hay una versión publicada disponible para este canal."
                elif is_update_available(APP_VERSION, release):
                    message = f"Nueva versión disponible: v{release.version}."
                else:
                    message = "Ya tienes la versión más reciente."
                    release = None
            except Exception:
                release = None
                message = "No se pudo comprobar actualizaciones. Inténtalo más tarde."
            self.updateResultReceived.emit(release, message)

        threading.Thread(target=check, name="WizzQtUpdateCheck", daemon=True).start()

    @Slot(object, str)
    def _apply_update_result(self, release: object, message: str) -> None:
        self._update_in_progress = False
        self._update_status = str(message)
        self._available_release = release if isinstance(release, ReleaseInfo) else None
        self._update_url = str(
            self._available_release.notes_url if self._available_release else ""
        )
        self.updateChanged.emit()

    @Slot()
    def installUpdate(self) -> None:
        """Stage a verified portable update, then exit for the helper to apply it."""
        release = self._available_release
        if self._update_in_progress or release is None:
            return
        if not can_self_update():
            self._update_status = (
                "Esta copia se ejecuta desde código fuente. Descarga la primera "
                "build portable para activar actualizaciones automáticas."
            )
            self.updateChanged.emit()
            return
        self._update_in_progress = True
        self._update_status = "Descargando y verificando la actualización…"
        self.updateChanged.emit()

        def install() -> None:
            try:
                script = stage_windows_update(release)
                launch_staged_update(script)
                message, action = "Actualización lista. WizZ se reiniciará ahora.", "quit"
            except UpdateInstallError as exc:
                message, action = str(exc), ""
            except Exception:
                message, action = "No se pudo preparar la actualización. Inténtalo más tarde.", ""
            self.updateInstallResultReceived.emit(message, action)

        threading.Thread(target=install, name="WizzQtUpdateInstall", daemon=True).start()

    @Slot(str, str)
    def _apply_update_install_result(self, message: str, action: str) -> None:
        self._update_in_progress = False
        self._update_status = str(message)
        self.updateChanged.emit()
        if action == "quit":
            QTimer.singleShot(180, QGuiApplication.quit)

    @Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._i18n.language

    @Slot(str)
    def setLanguage(self, preference: str) -> None:
        normalized = RuntimeLanguagePreference(self._runtime).save(preference)
        self._i18n.set_preference(normalized)
        self._refresh_library_models()
        self.languageChanged.emit()
        self.quickActionsChanged.emit()
        self.stateChanged.emit()
        self.statusChanged.emit()

    @Slot(int, result=str)
    def sceneName(self, scene_id: int) -> str:
        scene = wiz_scenes.get(int(scene_id))
        return translated_scene_name(self._i18n, int(scene_id), scene.name if scene else None)

    @Property(QObject, constant=True)
    def favoriteModel(self) -> QObject:
        return self.favorites

    @Property(QObject, constant=True)
    def recentColorModel(self) -> QObject:
        return self.recents

    @Property(QObject, constant=True)
    def sceneModel(self) -> QObject:
        return self.scenes

    @Property(QObject, constant=True)
    def customSceneModel(self) -> QObject:
        return self.custom_scenes

    @Property("QVariantList", notify=languageChanged)
    def sceneGroups(self) -> list[dict[str, Any]]:
        return [
            {
                "name": translated_scene_group(self._i18n, group),
                "scenes": [
                    {
                        "sceneId": scene.id,
                        "title": translated_scene_name(self._i18n, scene.id, scene.name),
                        "glyph": scene.glyph,
                        "entryColor": scene.color,
                        "dynamic": scene.dynamic,
                    }
                    for scene_id in ids
                    if (scene := wiz_scenes.get(scene_id)) is not None
                ],
            }
            for group, ids in wiz_scenes.GROUPS.items()
        ]

    @Property("QVariantList", notify=languageChanged)
    def sceneChoices(self) -> list[dict[str, Any]]:
        """Flat, de-duplicated scene catalogue for compact editors.

        The catalogue page deliberately keeps its grouped card layout.  Forms
        such as the favourite editor need the same real scene data, but in a
        single, readable selection control instead of exposing a raw WiZ ID.
        """
        choices: list[dict[str, Any]] = []
        seen: set[int] = set()
        for group, ids in wiz_scenes.GROUPS.items():
            for scene_id in ids:
                scene = wiz_scenes.get(scene_id)
                if scene is None or scene.id in seen:
                    continue
                seen.add(scene.id)
                choices.append(
                    {
                        "sceneId": scene.id,
                        "title": translated_scene_name(self._i18n, scene.id, scene.name),
                        "glyph": scene.glyph,
                        "group": translated_scene_group(self._i18n, group),
                        "label": f"{translated_scene_name(self._i18n, scene.id, scene.name)} · {translated_scene_group(self._i18n, group)}",
                    }
                )
        return choices

    @Property("QVariantList", notify=languageChanged)
    def favoriteSceneChoices(self) -> list[dict[str, Any]]:
        """All scene sources that a favourite may reference.

        A favourite in the Flet app can reuse both a WiZ scene and a local
        custom scene.  Keep that distinction here so the UI never asks users
        to translate a scene into a numeric protocol ID.
        """
        choices = [
                    {
                        "source": f"wiz:{scene.id}",
                        "label": f"{translated_scene_name(self._i18n, scene.id, scene.name)} · WiZ",
                        "title": translated_scene_name(self._i18n, scene.id, scene.name),
                        "glyph": scene.glyph,
                        "entryColor": scene.color,
                        "group": "Escenas WiZ",
            }
            for scene in wiz_scenes.CATALOG.values()
        ]
        for item in self._scenes_manager.get_scenes():
            mode = str(item.get("mode") or "rgb")
            if mode not in {"rgb", "white", "scene"}:
                continue
            uid = str(item.get("id") or "")
            if not uid:
                continue
            name = str(item.get("name") or "Escena personalizada")
            choices.append(
                {
                    "source": f"custom:{uid}",
                        "label": f"{name} · Personalizada",
                    "title": name,
                        "glyph": "\ue734",
                    "entryColor": self._custom_scene_color(item),
                    "group": "Personalizadas",
                }
            )
        return choices

    @Property(QObject, constant=True)
    def routineModel(self) -> QObject:
        return self.routines

    @Property(QObject, constant=True)
    def hotkeyModel(self) -> QObject:
        return self.hotkeys

    @Property("QVariantList", notify=hotkeysChanged)
    def hotkeyActions(self) -> list[dict[str, Any]]:
        return list(self._hotkey_actions_cache)

    @Property(bool, notify=hotkeysChanged)
    def hotkeysAvailable(self) -> bool:
        return bool(self._hotkeys_manager.available)

    @Property(bool, notify=hotkeysChanged)
    def hotkeysEnabled(self) -> bool:
        return self._hotkeys_manager.is_enabled()

    @Property(bool, notify=hotkeysChanged)
    def hotkeysSuppress(self) -> bool:
        return self._hotkeys_manager.suppress_enabled()

    @Property(bool, notify=hotkeysChanged)
    def hotkeysRelease(self) -> bool:
        return self._hotkeys_manager.trigger_on_release()

    @Property(int, notify=hotkeysChanged)
    def hotkeysCooldown(self) -> int:
        return self._hotkeys_manager.cooldown_ms()

    @Property(str, notify=hotkeysChanged)
    def hotkeysStatus(self) -> str:
        return self._hotkeys_manager.backend_status()

    @Property(str, notify=colorChanged)
    def colorHex(self) -> str:
        if getattr(self, "_optimistic_color", None):
            return self._optimistic_color
        bulbs = self.controller.get_bulbs_detailed()
        return self._display_color(self._state_for_bulb(bulbs[0])) if bulbs else "#ffffff"

    @Property(str, notify=modeChanged)
    def colorMode(self) -> str:
        return self._color_mode

    @Slot(str)
    def toggleLight(self, ip: str) -> None:
        selected = set(self.controller.get_target_config().get("selected_ips") or [])
        if ip in selected:
            selected.remove(ip)
        else:
            selected.add(ip)
        if not selected:
            selected.add(ip)
        self.controller.set_target_selection(sorted(selected))
        # Do not rebuild LightListModel here: a model reset takes the
        # carousel back to its first item every time a bulb is toggled.
        self.lights.update_selection(selected)
        self.statusChanged.emit()

    @Slot()
    def selectAll(self) -> None:
        ips = [str(item["ip"]) for item in self.lights._items]
        self.controller.set_target_selection(ips)
        self.refresh()

    @Slot()
    def toggleMaster(self) -> None:
        self.controller.turn_off() if self.powerOn else self.controller.turn_on()

    @Slot(int)
    def queueBrightness(self, value: int) -> None:
        self._pending_brightness = max(10, min(100, int(value)))
        self._optimistic_brightness = self._pending_brightness
        self.brightnessChanged.emit()
        if not self._brightness_timer.isActive():
            self._brightness_timer.start()

    @Slot()
    def _flush_brightness(self) -> None:
        self.controller.set_brightness(self._pending_brightness)
        self.brightnessChanged.emit()

    @Slot(str)
    def applyQuick(self, action: str) -> None:
        actions = {
            "cinema": lambda: self.controller.set_scene(18),
            "reading": lambda: self.controller.set_white(4000),
            "relax": lambda: self.controller.set_scene(16),
            "party": lambda: self.controller.set_scene(4, speed=180),
            "warm": lambda: self.controller.set_white(2700),
            "cool": lambda: self.controller.set_white(6500),
            "reset": self.controller.reset_light,
            "off": self.controller.turn_off,
        }
        callback = actions.get(str(action))
        if callback:
            callback()

    @Slot(int, int, int)
    def setRgb(self, red: int, green: int, blue: int) -> None:
        rgb = tuple(max(0, min(255, int(value))) for value in (red, green, blue))
        self._pending_rgb = rgb
        mode_changed = self._color_mode != "rgb"
        self._color_mode = "rgb"
        self._optimistic_color = "#{:02x}{:02x}{:02x}".format(*rgb)
        if mode_changed:
            self.modeChanged.emit()
        if not self._rgb_timer.isActive():
            self._rgb_timer.start()

    @Slot(str, result=bool)
    def setHex(self, value: str) -> bool:
        """Apply a precise RGB value entered from the native UI."""
        raw = str(value or "").strip().lstrip("#")
        if len(raw) != 6:
            return False
        try:
            red, green, blue = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
        except ValueError:
            return False
        self.setRgb(red, green, blue)
        self.commitCurrentColor()
        return True

    @Slot()
    def _flush_rgb(self) -> None:
        if self._pending_rgb is not None:
            self.controller.set_rgb(*self._pending_rgb)
            self._pending_rgb = None
            # The picker paints its cursor locally. Notify the rest of QML only
            # at the transport cadence so pointer events never trigger a full
            # binding pass through the page at 100+ Hz.
            self.colorChanged.emit()

    @Slot(int)
    def setWhite(self, kelvin: int) -> None:
        self._optimistic_color = ""
        mode_changed = self._color_mode != "white"
        self._color_mode = "white"
        self._pending_white = max(2200, min(6500, int(kelvin)))
        self._optimistic_kelvin = self._pending_white
        if mode_changed:
            self.modeChanged.emit()
        self.whiteChanged.emit()
        if not self._white_timer.isActive():
            self._white_timer.start()

    @Slot()
    def _flush_white(self) -> None:
        if self._pending_white is not None:
            self.controller.set_white(self._pending_white)
            self._pending_white = None

    def _remember_recent(self, item: dict[str, Any]) -> None:
        uid = str(item["uid"])
        self._recent_items = [entry for entry in self._recent_items if str(entry["uid"]) != uid]
        self._recent_items.insert(0, item)
        self._recent_items = self._recent_items[:8]
        self.recents.replace(list(self._recent_items))

    @Slot()
    def commitCurrentColor(self) -> None:
        value = str(self.colorHex or "#ffffff").upper()
        self._remember_recent({
            "title": value,
            "subtitle": "RGB",
            "entryColor": value,
            "uid": f"rgb:{value}",
            "kind": "rgb",
        })
        self.favoriteStateChanged.emit()

    @Slot(int)
    def commitWhite(self, kelvin: int) -> None:
        value = max(2200, min(6500, int(kelvin)))
        color = "#ffd9a0" if value <= 3000 else "#d8efff" if value >= 5500 else "#fff0dc"
        self._remember_recent({
            "title": f"{value}K",
            "subtitle": "BLANCO",
            "entryColor": color,
            "uid": f"white:{value}",
            "kind": "white",
        })
        self.favoriteStateChanged.emit()

    @Slot(str)
    def applyRecent(self, uid: str) -> None:
        kind, _, value = str(uid).partition(":")
        if kind == "rgb" and value.startswith("#") and len(value) == 7:
            raw = value[1:]
            self.setRgb(int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
        elif kind == "white":
            try:
                self.setWhite(int(value))
            except ValueError:
                pass

    @Slot()
    def clearRecents(self) -> None:
        self._recent_items = []
        self.recents.replace([])

    @Slot(str)
    def applyFavorite(self, uid: str) -> None:
        favorite = self._favorites_manager.get_favorite(str(uid))
        if favorite:
            self.controller.apply_favorite(favorite)

    @staticmethod
    def _favorite_entry(item: dict[str, Any]) -> dict[str, Any]:
        kind = str(item.get("type") or "rgb").lower()
        value = item.get("value")
        if kind == "rgb":
            raw_value = str(value or "#ffffff").upper()
            subtitle = raw_value
            color = raw_value
        elif kind == "white":
            kelvin = max(2200, min(6500, int(value or 4000)))
            raw_value = str(kelvin)
            subtitle = f"{kelvin}K"
            color = "#ffd9a0" if kelvin <= 3000 else "#d8efff" if kelvin >= 5500 else "#fff0dc"
        elif kind == "brightness":
            level = max(10, min(100, int(value or 100)))
            raw_value = str(level)
            subtitle = f"{level}%"
            color = "#fbbf24"
        elif kind == "scene":
            scene_id = value.get("sceneId", 18) if isinstance(value, dict) else value
            raw_value = json.dumps(value, separators=(",", ":")) if isinstance(value, dict) else str(scene_id or 18)
            scene = wiz_scenes.get(int(scene_id or 18))
            subtitle = scene.name if scene else f"Escena {scene_id}"
            color = scene.color if scene else "#8b5cf6"
        else:
            raw_value = str(value or "")
            subtitle = raw_value
            color = "#a78bfa"
        return {
            "title": str(item.get("name") or "Favorito"),
            "subtitle": subtitle,
            "entryColor": color,
            "uid": str(item.get("id") or ""),
            "kind": kind,
            "rawValue": raw_value,
        }

    @staticmethod
    def _normalize_favorite_value(kind: str, raw_value: str) -> tuple[Any, str]:
        normalized = str(kind or "rgb").strip().lower()
        if normalized == "rgb":
            value = str(raw_value or "#ffffff").strip().upper()
            if not value.startswith("#"):
                value = "#" + value
            if len(value) != 7:
                raise ValueError("El color debe usar el formato #RRGGBB")
            int(value[1:], 16)
            return value, "PALETTE"
        if normalized == "white":
            return max(2200, min(6500, int(raw_value))), "WB_TWILIGHT"
        if normalized == "brightness":
            return max(10, min(100, int(raw_value))), "BRIGHTNESS_6"
        if normalized == "scene":
            text = str(raw_value or "18").strip()
            if text.startswith("{"):
                value = json.loads(text)
            else:
                value = {"sceneId": int(text), "speed": 100}
            return value, "MOVIE"
        raise ValueError("Tipo de favorito no compatible")

    @Slot(str, str, str, str, result=str)
    def upsertFavorite(self, uid: str, name: str, kind: str, raw_value: str) -> str:
        try:
            value, icon = self._normalize_favorite_value(kind, raw_value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return ""
        clean_name = str(name or "Favorito").strip() or "Favorito"
        if uid:
            if not self._favorites_manager.update_favorite(uid, clean_name, kind, value, icon):
                return ""
            result = str(uid)
        else:
            result = str(self._favorites_manager.add_favorite(clean_name, kind, value, icon).get("id") or "")
        self._refresh_library_models()
        self.statusChanged.emit()
        return result

    @Slot(str, str, str, int, result=str)
    def upsertFavoriteFromScene(self, uid: str, name: str, source: str, speed: int) -> str:
        """Persist a favourite derived from a WiZ or saved local scene."""
        source = str(source or "wiz:18")
        level = max(20, min(200, int(speed)))
        kind = "scene"
        raw_value = json.dumps({"sceneId": 18, "speed": level})
        try:
            if source.startswith("custom:"):
                custom_uid = source.split(":", 1)[1]
                item = next(
                    (scene for scene in self._scenes_manager.get_scenes()
                     if str(scene.get("id") or "") == custom_uid),
                    None,
                )
                if item is None:
                    return ""
                mode = str(item.get("mode") or "")
                value = item.get("value") if isinstance(item.get("value"), dict) else {}
                if mode == "rgb":
                    kind = "rgb"
                    raw_value = "#{:02X}{:02X}{:02X}".format(
                        int(value.get("r", 255)), int(value.get("g", 0)), int(value.get("b", 0))
                    )
                elif mode == "white":
                    kind = "white"
                    raw_value = str(int(value.get("temp", 4000)))
                elif mode == "scene":
                    raw_value = json.dumps({
                        "sceneId": int(value.get("sceneId", 18)),
                        "speed": level,
                    })
                else:
                    return ""
            elif source.startswith("wiz:"):
                raw_value = json.dumps({"sceneId": int(source.split(":", 1)[1]), "speed": level})
            else:
                return ""
        except (TypeError, ValueError):
            return ""
        return self.upsertFavorite(uid, name, kind, raw_value)

    @Slot(str, result=bool)
    def deleteFavorite(self, uid: str) -> bool:
        removed = self._favorites_manager.remove_favorite(str(uid))
        if removed:
            self._refresh_library_models()
            self.statusChanged.emit()
        return removed

    @Slot()
    def saveCurrentFavorite(self) -> None:
        if self._color_mode == "white":
            value: Any = self.whiteKelvin
            kind = "white"
            name = f"Blanco {value}K"
            icon = "WB_TWILIGHT"
        else:
            value = str(self.colorHex or "#ffffff").upper()
            kind = "rgb"
            name = f"Color {value}"
            icon = "PALETTE"
        if any(
            str(item.get("type")) == kind
            and str(item.get("value", "")).upper() == str(value).upper()
            for item in self._favorites_manager.get_favorites()
        ):
            self.statusChanged.emit()
            return
        self._favorites_manager.add_favorite(name, kind, value, icon)
        self._refresh_library_models()
        self.statusChanged.emit()

    @Slot(str)
    def applyScene(self, uid: str) -> None:
        if str(uid).startswith("wiz:"):
            try:
                self.controller.set_scene(int(str(uid).split(":", 1)[1]))
            except (TypeError, ValueError):
                pass
            return
        scene = self._scenes_manager.get_scene(str(uid))
        if scene:
            self.controller.apply_custom_scene(scene)

    @staticmethod
    def _custom_scene_color(scene: dict[str, Any]) -> str:
        mode = str(scene.get("mode") or "rgb")
        value = scene.get("value") if isinstance(scene.get("value"), dict) else {}
        if mode == "rgb":
            return "#{:02x}{:02x}{:02x}".format(
                int(value.get("r", 167)), int(value.get("g", 139)), int(value.get("b", 250))
            )
        if mode == "white":
            temp = int(value.get("temp", 4000))
            return "#ffd9a0" if temp <= 3000 else "#d8efff" if temp >= 5500 else "#fff0dc"
        if mode == "scene":
            built_in = wiz_scenes.get(int(value.get("sceneId", 18)))
            return built_in.color if built_in else "#8b5cf6"
        return "#a78bfa"

    @Slot(int, int)
    def queueSceneSpeed(self, scene_id: int, speed: int) -> None:
        self._pending_scene = (int(scene_id), max(20, min(200, int(speed))))
        if not self._scene_timer.isActive():
            self._scene_timer.start()

    @Slot()
    def _flush_scene(self) -> None:
        if self._pending_scene is not None:
            scene_id, speed = self._pending_scene
            self.controller.set_scene(scene_id, speed=speed)
            self._pending_scene = None

    @Slot(str, result=str)
    def captureCurrentScene(self, name: str) -> str:
        scene = self._scenes_manager.scene_from_state(
            dict(self.controller.get_state() or self._state),
            str(name or "Escena actual").strip() or "Escena actual",
        )
        self._refresh_library_models()
        return str(scene.get("id") or "")

    @Slot(str, result=bool)
    def deleteCustomScene(self, uid: str) -> bool:
        removed = self._scenes_manager.remove_scene(str(uid))
        if removed:
            self._refresh_library_models()
        return removed

    @Slot(str, str, str, str, int, int, result=str)
    def upsertCustomScene(
        self, uid: str, name: str, mode: str, raw_value: str, dimming: int, speed: int
    ) -> str:
        normalized = str(mode or "rgb").lower()
        level = max(10, min(100, int(dimming)))
        try:
            if normalized == "rgb":
                color = str(raw_value or "#ffffff").strip().lstrip("#")
                if len(color) != 6:
                    return ""
                red, green, blue = (int(color[index:index + 2], 16) for index in (0, 2, 4))
                value: Any = {"r": red, "g": green, "b": blue, "dimming": level}
            elif normalized == "white":
                value = {"temp": max(2200, min(6500, int(raw_value))), "dimming": level}
            elif normalized == "scene":
                value = {
                    "sceneId": max(1, min(33, int(raw_value))),
                    "speed": max(20, min(200, int(speed))),
                    "dimming": level,
                }
            else:
                return ""
        except (TypeError, ValueError):
            return ""
        clean_name = str(name or "Mi escena").strip() or "Mi escena"
        if uid:
            if not self._scenes_manager.update_scene(uid, clean_name, normalized, value):
                return ""
            result = str(uid)
        else:
            result = str(self._scenes_manager.add_scene(clean_name, normalized, value).get("id") or "")
        self._refresh_library_models()
        return result

    @Slot(str)
    def runRoutine(self, uid: str) -> None:
        if self._routines_manager.get_routine(str(uid)):
            self._executor.execute_routine(str(uid))

    @Slot(result=str)
    def captureCurrentRoutine(self) -> str:
        """Save the currently displayed light state as an editable routine."""
        state = dict(self.controller.get_state() or self._state)
        actions: list[dict[str, Any]] = [{"type": "turn_on"}]
        color = "#5f91ff"
        if state.get("sceneId"):
            actions.append({"type": "scene", "value": {
                "sceneId": int(state["sceneId"]), "speed": int(state.get("speed", 100) or 100),
            }})
            scene = wiz_scenes.get(int(state["sceneId"]))
            color = scene.color if scene else "#8b5cf6"
        elif all(key in state for key in ("r", "g", "b")):
            color = "#{:02X}{:02X}{:02X}".format(int(state["r"]), int(state["g"]), int(state["b"]))
            actions.append({"type": "rgb", "value": color})
        elif state.get("temp"):
            actions.append({"type": "white_kelvin", "value": int(state["temp"])})
            color = "#ffd9a0"
        if state.get("dimming") is not None:
            actions.append({"type": "brightness", "value": int(state.get("dimming", 100) or 100)})
        created = self._routines_manager.add_routine(
            "Estado actual", actions, "Estado capturado de la luz activa.", color, "CAMERA_ALT_ROUNDED"
        )
        self._refresh_library_models()
        return str(created.get("id") or "")

    @Slot(str, str, str, str, str, result=str)
    def upsertRoutine(
        self, uid: str, name: str, description: str, color: str, actions_json: str
    ) -> str:
        clean_name = str(name or "").strip() or "Nueva rutina"
        try:
            actions = json.loads(str(actions_json or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return ""
        actions = self._routines_manager.normalize_actions(actions)
        if not actions:
            return ""
        clean_color = str(color or "#5f91ff").strip()
        if not (clean_color.startswith("#") and len(clean_color) == 7):
            clean_color = "#5f91ff"
        existing = self._routines_manager.get_routine(str(uid)) if uid else None
        if existing:
            self._routines_manager.update_routine(
                str(uid), name=clean_name, description=str(description or "").strip(),
                color=clean_color, actions=actions,
            )
            result = str(uid)
        else:
            created = self._routines_manager.add_routine(
                clean_name, actions, description=str(description or "").strip(), color=clean_color,
            )
            result = str(created.get("id") or "")
        self._refresh_library_models()
        return result

    @Slot(str, result=bool)
    def deleteRoutine(self, uid: str) -> bool:
        removed = self._routines_manager.remove_routine(str(uid))
        if removed:
            self._refresh_library_models()
        return bool(removed)

    @Slot(str, result=str)
    def duplicateRoutine(self, uid: str) -> str:
        created = self._routines_manager.duplicate_routine(str(uid))
        if not created:
            return ""
        self._refresh_library_models()
        return str(created.get("id") or "")

    @Slot()
    def resetRoutineDefaults(self) -> None:
        self._routines_manager.reset_defaults()
        self._refresh_library_models()

    @Slot(bool)
    def setHotkeysEnabled(self, enabled: bool) -> None:
        self._hotkeys_manager.set_enabled(bool(enabled))
        self._refresh_hotkey_model()

    @Slot(bool)
    def setHotkeysSuppress(self, enabled: bool) -> None:
        self._hotkeys_manager.set_suppress(bool(enabled))
        self._refresh_hotkey_model()

    @Slot(bool)
    def setHotkeysRelease(self, enabled: bool) -> None:
        self._hotkeys_manager.set_trigger_on_release(bool(enabled))
        self._refresh_hotkey_model()

    @Slot(int)
    def setHotkeysCooldown(self, value: int) -> None:
        self._hotkeys_manager.set_cooldown_ms(int(value))
        self.hotkeysChanged.emit()

    @Slot(str, str, result=str)
    def saveHotkey(self, action_id: str, combination: str) -> str:
        result = self._hotkeys_manager.assign_hotkey(str(action_id), str(combination))
        self._refresh_hotkey_model()
        return str(result.get("message") or ("Atajo guardado." if result.get("ok") else "Atajo inválido."))

    @Slot(str)
    def clearHotkey(self, action_id: str) -> None:
        self._hotkeys_manager.clear_hotkey(str(action_id))
        self._refresh_hotkey_model()

    @Slot(str, result=bool)
    def testHotkeyAction(self, action_id: str) -> bool:
        action = self._hotkeys_manager.action_by_id(str(action_id))
        payload = action.get("action") if isinstance(action, dict) else None
        if not isinstance(payload, dict):
            return False
        self._executor.execute(payload, threaded=True)
        return True

    @Slot()
    def resetHotkeys(self) -> None:
        self._hotkeys_manager.reset_defaults()
        self._refresh_hotkey_model()

    @Slot()
    def reregisterHotkeys(self) -> None:
        self._hotkeys_manager.apply_hooks()
        self._refresh_hotkey_model()

    @Slot(result=str)
    def exportHotkeys(self) -> str:
        """Return the portable configuration used by the Flet export dialog."""
        return self._hotkeys_manager.export_json()

    @Slot()
    def recordHotkey(self) -> None:
        if not self._hotkeys_manager.can_record:
            self.hotkeyCaptured.emit("")
            return

        def capture() -> None:
            self.hotkeyCaptured.emit(self._hotkeys_manager.read_hotkey_blocking() or "")

        threading.Thread(target=capture, name="WizzQtHotkeyCapture", daemon=True).start()

    @Slot(int)
    def navigate(self, index: int) -> None:
        self.navigateRequested.emit(int(index))
