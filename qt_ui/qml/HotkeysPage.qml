pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    objectName: "hotkeysPage"
    implicitHeight: pageContent.implicitHeight
    property string feedback: ""
    property bool recording: false
    property bool captureAwaitingRelease: false
    property string capturePreview: ""
    property string capturedCombo: ""
    property string actionQuery: ""
    property string actionGroup: ""
    property string exportText: ""
    property string customHex: "#ff0000"
    property int customKelvin: 4000

    Timer {
        id: captureReleaseTimer
        interval: 1000
        onTriggered: root.endCapture()
    }

    function t(spanish, english) { return wizz.language === "en" ? english : spanish }

    readonly property bool editingCustomColor: String(actionBox.currentValue || "") === "color_custom"
    readonly property bool editingCustomWhite: String(actionBox.currentValue || "") === "white_custom"
    readonly property bool editingPicker: editingCustomColor || editingCustomWhite

    function selectedActionId() {
        if (editingCustomColor) {
            const raw = customHex.replace("#", "").replace(/[^0-9a-f]/gi, "")
            return raw.length === 6 ? "color_hex_" + raw.toLowerCase() : ""
        }
        if (editingCustomWhite)
            return customKelvin >= 2200 && customKelvin <= 6500 ? "white_kelvin_" + customKelvin : ""
        return String(actionBox.currentValue || "")
    }

    function normalizedHex(value) {
        const raw = String(value || "").replace("#", "").replace(/[^0-9a-f]/gi, "").slice(0, 6)
        return raw.length === 6 ? "#" + raw.toUpperCase() : ""
    }

    function formatCombo(combo) {
        const labels = { ctrl: "Ctrl", alt: "Alt", shift: "Shift", win: "Win",
                         numpadplus: "Numpad Plus", numpadminus: "Numpad Minus",
                         numpadmultiply: "Numpad Multiply", numpaddivide: "Numpad Divide",
                         numpaddecimal: "Numpad Decimal" }
        return String(combo || "").split("+").map(function(part) {
            if (/^numpad[0-9]$/.test(part)) return "Numpad " + part.slice(-1)
            return labels[part] || part.toUpperCase()
        }).join("  +  ")
    }

    function keyName(key, modifiers) {
        if (modifiers & Qt.KeypadModifier) {
            if (key >= Qt.Key_0 && key <= Qt.Key_9)
                return "numpad" + String.fromCharCode(key)
            if (key === Qt.Key_Plus) return "numpadplus"
            if (key === Qt.Key_Minus) return "numpadminus"
            if (key === Qt.Key_Asterisk) return "numpadmultiply"
            if (key === Qt.Key_Slash) return "numpaddivide"
            if (key === Qt.Key_Period || key === Qt.Key_Comma) return "numpaddecimal"
            // With Num Lock off Qt reports navigation keys for the keypad;
            // those cannot be registered as distinct numeric VKs.
            return ""
        }
        if (key >= Qt.Key_A && key <= Qt.Key_Z) return String.fromCharCode(key).toLowerCase()
        if (key >= Qt.Key_0 && key <= Qt.Key_9) return String.fromCharCode(key)
        if (key >= Qt.Key_F1 && key <= Qt.Key_F24) return "f" + (key - Qt.Key_F1 + 1)
        if (key === Qt.Key_Up) return "up"
        if (key === Qt.Key_Down) return "down"
        if (key === Qt.Key_Left) return "left"
        if (key === Qt.Key_Right) return "right"
        if (key === Qt.Key_Space) return "space"
        if (key === Qt.Key_Return || key === Qt.Key_Enter) return "enter"
        if (key === Qt.Key_Tab) return "tab"
        if (key === Qt.Key_Backspace) return "backspace"
        if (key === Qt.Key_Delete) return "delete"
        if (key === Qt.Key_Insert) return "insert"
        if (key === Qt.Key_Home) return "home"
        if (key === Qt.Key_End) return "end"
        if (key === Qt.Key_PageUp) return "page up"
        if (key === Qt.Key_PageDown) return "page down"
        if (key === Qt.Key_Plus) return "plus"
        if (key === Qt.Key_Minus) return "minus"
        return ""
    }

    function modifierNames(modifiers) {
        const names = []
        if (modifiers & Qt.ControlModifier) names.push("ctrl")
        if (modifiers & Qt.AltModifier) names.push("alt")
        if (modifiers & Qt.ShiftModifier) names.push("shift")
        if (modifiers & Qt.MetaModifier) names.push("win")
        return names
    }

    function beginCapture() {
        if (recording) return
        wizz.beginHotkeyCapture()
        recording = true
        capturePreview = ""
        feedback = t("Pulsa modificadores y una tecla; Esc cancela.", "Press modifiers and one key; Esc cancels.")
        shortcutCapture.forceActiveFocus()
    }

    function endCapture() {
        if (!recording && !captureAwaitingRelease) return
        captureReleaseTimer.stop()
        recording = false
        captureAwaitingRelease = false
        capturePreview = ""
        wizz.endHotkeyCapture()
    }

    function captureKey(event) {
        event.accepted = true
        if (!recording || event.isAutoRepeat) return
        if (event.key === Qt.Key_Escape) {
            endCapture()
            feedback = t("Captura cancelada.", "Capture cancelled.")
            return
        }
        const modifiers = modifierNames(event.modifiers)
        const key = keyName(event.key, event.modifiers)
        if (!key) {
            capturePreview = modifiers.join(" + ") + (modifiers.length ? " + …" : "")
            if (event.modifiers & Qt.KeypadModifier) {
                feedback = event.key === Qt.Key_Enter || event.key === Qt.Key_Return
                    ? t("Numpad Enter no se puede distinguir de Enter en los atajos globales de Windows.", "Windows global shortcuts cannot distinguish Numpad Enter from Enter.")
                    : t("Activa Bloq Num para capturar esta tecla del teclado numérico.", "Turn on Num Lock to capture this numpad key.")
            }
            return
        }
        capturedCombo = modifiers.concat([key]).join("+")
        capturePreview = ""
        recording = false
        captureAwaitingRelease = true
        captureReleaseTimer.restart()
        feedback = t("Combinación capturada. Revísala y guarda.", "Shortcut captured. Review it and save.")
    }

    function actionGroups() {
        const groups = [root.t("Todas", "All")]
        const actions = wizz.hotkeyActions || []
        for (let i = 0; i < actions.length; ++i) {
            const group = String(actions[i].group || "General")
            if (groups.indexOf(group) < 0) groups.push(group)
        }
        return groups
    }

    function filteredActions() {
        const query = actionQuery.trim().toLowerCase()
        return (wizz.hotkeyActions || []).filter(function(action) {
            const group = String(action.group || "General")
            const name = String(action.name || "")
            return (!actionGroup || actionGroup === root.t("Todas", "All") || group === actionGroup)
                && (!query || name.toLowerCase().indexOf(query) >= 0 || group.toLowerCase().indexOf(query) >= 0)
        })
    }

    function chooseAction(actionId, combo) {
        if (actionId.indexOf("color_hex_") === 0) {
            const hex = normalizedHex(actionId.substring(10))
            if (hex) customPicker.sendHex(hex)
            actionId = "color_custom"
        } else if (actionId.indexOf("white_kelvin_") === 0) {
            const kelvin = Number(actionId.substring(13))
            if (kelvin >= 2200 && kelvin <= 6500) customPicker.chooseKelvin(kelvin)
            actionId = "white_custom"
        }
        for (let i = 0; i < actionBox.count; ++i) {
            if (actionBox.valueAt(i) === actionId) {
                actionBox.currentIndex = i
                break
            }
        }
        capturedCombo = combo || ""
    }

    onVisibleChanged: if (!visible) endCapture()
    Component.onDestruction: endCapture()

    Column {
        id: pageContent
        width: parent.width
        spacing: 16

        Item {
            width: parent.width
            height: 62
            Column {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: Math.max(0, hotkeysStatusBadge.x - x - 12)
                spacing: 3
                Text { width: parent.width; text: root.t("Atajos globales", "Global hotkeys"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: Theme.pageTitleSize; font.weight: Theme.pageTitleWeight; elide: Text.ElideRight }
                Text { width: parent.width; text: root.t("Atajos para luz, escenas, favoritos y rutinas", "Shortcuts for lights, scenes, favorites, and routines"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 13; elide: Text.ElideRight }
            }
            Rectangle {
                id: hotkeysStatusBadge
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(300, Math.max(210, parent.width * 0.43))
                height: 38
                radius: 19
                color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.10)
                border.width: 1; border.color: Theme.stroke
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14; spacing: 9
                    Item {
                        Layout.preferredWidth: 16; Layout.preferredHeight: 16
                        Rectangle {
                            anchors.centerIn: parent
                            width: 11; height: 11; radius: 6
                            color: wizz.hotkeysEnabled && wizz.hotkeysOperational ? Theme.success : Theme.warning
                        }
                    }
                    Text { Layout.fillWidth: true; text: wizz.hotkeysStatus; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold; elide: Text.ElideRight }
                }
            }
        }

        Rectangle {
            visible: Qt.platform.os === "linux"
            width: parent.width
            height: Math.max(84, linuxNotice.implicitHeight + 28)
            radius: Theme.radiusMedium
            color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.09)
            border.width: 1
            border.color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.36)
            RowLayout {
                id: linuxNotice
                anchors.fill: parent; anchors.margins: 14; spacing: 11
                AppIcon { Layout.preferredWidth: 18; Layout.preferredHeight: 18; name: "info"; color: Theme.warning }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 3
                    Text {
                        Layout.fillWidth: true
                        text: root.t("Los atajos globales todavía no funcionan en Linux", "Global hotkeys are not available on Linux yet")
                        color: Theme.text; font.family: Theme.controlFont
                        font.pixelSize: 12; font.weight: Font.Bold; wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.t("Puedes usar los controles desde la ventana y el panel rápido. Tus combinaciones guardadas se conservan, pero no se ejecutarán hasta que agreguemos un backend seguro para Linux.", "Use the app window and Quick Panel for now. Your saved shortcuts are kept, but will not run until a safe Linux backend is available.")
                        color: Theme.muted; font.family: Theme.uiFont
                        font.pixelSize: Theme.captionSize; wrapMode: Text.WordWrap
                    }
                }
            }
        }

        Rectangle {
            visible: Qt.platform.os === "osx"
            width: parent.width
            height: Math.max(84, macosNotice.implicitHeight + 28)
            radius: Theme.radiusMedium
            color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.09)
            border.width: 1
            border.color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.36)
            RowLayout {
                id: macosNotice
                anchors.fill: parent
                anchors.margins: 14
                spacing: 11
                AppIcon { Layout.preferredWidth: 18; Layout.preferredHeight: 18; name: "info"; color: Theme.warning }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        Layout.fillWidth: true
                        text: root.t("Atajos globales todavía no disponibles en esta versión experimental para macOS", "Global shortcuts are not available in this experimental macOS build yet")
                        color: Theme.text
                        font.family: Theme.controlFont
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.t("Tu configuración se conserva. La biblioteca de terceros marca el soporte para macOS como experimental y usa permisos de entrada del sistema; lo activaremos cuando esté validado en un Mac real.", "Your settings are preserved. The third-party library labels macOS support experimental and uses system input permissions; we’ll enable it after validating it on a real Mac.")
                        color: Theme.muted
                        font.family: Theme.uiFont
                        font.pixelSize: Theme.captionSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        Rectangle {
            width: parent.width; height: root.width < 750 ? 244 : 220; radius: Theme.radiusMedium
            color: Theme.card; border.width: 1; border.color: Theme.stroke
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                Text { text: root.t("ESTADO", "STATUS"); color: Theme.muted; font.pixelSize: Theme.captionSize; font.weight: Font.Bold; font.letterSpacing: 1 }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Repeater {
                        model: [
                            { title: root.t("Atajos activos", "Hotkeys enabled"), help: root.t("Servicio global de la aplicación", "Global application service"), value: wizz.hotkeysEnabled, kind: "enabled" },
                            { title: root.t("Bloquear combinación", "Block shortcut"), help: root.t("Evita que el atajo llegue a la app activa, si está disponible.", "Keep the shortcut from reaching the active app, if supported."), value: wizz.hotkeysSuppress, kind: "suppress" },
                            { title: root.t("Ejecutar al soltar", "Run on release"), help: root.t("Evita repeticiones accidentales", "Avoids accidental repeats"), value: wizz.hotkeysRelease, kind: "release" }
                        ]
                        delegate: Rectangle {
                            id: settingCard
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: root.width < 750 ? 108 : 84; radius: 12
                            color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 12; spacing: 8
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 2
                                    Text { Layout.fillWidth: true; text: settingCard.modelData.title; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
                                    Text { id: settingHelp; Layout.fillWidth: true; text: settingCard.modelData.help; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; wrapMode: Text.WordWrap; maximumLineCount: 4; elide: Text.ElideRight }
                                }
                                Switch {
                                    id: switchControl
                                    checked: settingCard.modelData.value
                                    enabled: wizz.hotkeysAvailable
                                    onToggled: {
                                        if (settingCard.modelData.kind === "enabled") wizz.setHotkeysEnabled(checked)
                                        else if (settingCard.modelData.kind === "suppress") wizz.setHotkeysSuppress(checked)
                                        else wizz.setHotkeysRelease(checked)
                                    }
                                    indicator: Rectangle {
                                        implicitWidth: 48; implicitHeight: 28; radius: 14
                                        color: switchControl.checked ? Theme.primary : Theme.stroke
                                        Rectangle { width: 20; height: 20; radius: 10; y: 4; x: switchControl.checked ? 24 : 4; color: Theme.text; Behavior on x { NumberAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } } }
                                    }
                                }
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    Text { text: root.t("Antirrebote", "Debounce"); color: Theme.muted; font.pixelSize: Theme.labelSize }
                    Slider {
                        id: cooldown
                        Layout.fillWidth: true; from: 120; to: 900; stepSize: 60; value: wizz.hotkeysCooldown
                        onMoved: wizz.setHotkeysCooldown(Math.round(value))
                        background: Rectangle { x: cooldown.leftPadding; y: cooldown.topPadding + cooldown.availableHeight / 2 - 2; width: cooldown.availableWidth; height: 4; radius: 2; color: Theme.stroke; Rectangle { width: cooldown.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.accent } }
                        handle: Rectangle { x: cooldown.leftPadding + cooldown.visualPosition * (cooldown.availableWidth - width); y: cooldown.topPadding + cooldown.availableHeight / 2 - height / 2; width: 20; height: 20; radius: 10; color: Theme.text }
                    }
                    Text { text: Math.round(cooldown.value) + " ms"; color: Theme.muted; font.pixelSize: Theme.labelSize; Layout.preferredWidth: 54 }
                    PressSurface {
                        Layout.preferredWidth: 122; Layout.preferredHeight: 36; radius: 18; color: "transparent"; border.color: Theme.stroke
                        // Re-registering is a recovery action, not part of
                        // creating an empty set of shortcuts.  Keep it out
                        // of the primary flow until the backend has work to
                        // reconnect.
                        outlined: true; visible: wizz.hotkeysAvailable && wizz.hotkeyModel.rowCount() > 0
                        onClicked: wizz.reregisterHotkeys()
                        Text { anchors.centerIn: parent; text: root.t("Re-registrar", "Re-register"); color: Theme.text; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width; height: editorContent.implicitHeight + 32; radius: Theme.radiusMedium
            color: Theme.card; border.width: 1; border.color: Theme.stroke
            Behavior on height { NumberAnimation { duration: Theme.motionNormal; easing.type: Easing.OutCubic } }
            ColumnLayout {
                id: editorContent
                x: 16; y: 16; width: parent.width - 32; spacing: 11
                Text { text: root.t("CREAR / EDITAR ATAJO", "CREATE / EDIT SHORTCUT"); color: Theme.muted; font.pixelSize: Theme.captionSize; font.weight: Font.Bold; font.letterSpacing: 1 }
                Text { text: root.t("Elige una acción, captura una combinación y guárdala.", "Choose an action, capture a shortcut, then save it."); color: Theme.muted; font.pixelSize: Theme.labelSize }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    WizComboBox {
                        id: groupBox
                        objectName: "hotkeyGroupBox"
                        Layout.preferredWidth: 190; Layout.preferredHeight: 40
                        model: root.actionGroups()
                        currentIndex: Math.max(0, model.indexOf(root.actionGroup))
                        onActivated: root.actionGroup = currentText
                        contentItem: Text { leftPadding: 13; text: groupBox.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: Theme.labelSize; elide: Text.ElideRight }
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: groupBox.activeFocus ? Theme.primary : Theme.stroke }
                    }
                    TextField {
                        id: actionSearch
                        Layout.fillWidth: true; Layout.preferredHeight: 40
                        placeholderText: root.t("Buscar acción", "Search action"); placeholderTextColor: Theme.faint; color: Theme.text; leftPadding: 13; rightPadding: 13
                        onTextEdited: root.actionQuery = text
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: actionSearch.activeFocus ? Theme.primary : Theme.stroke }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    WizComboBox {
                        id: actionBox
                        objectName: "hotkeyActionBox"
                        Layout.fillWidth: true; Layout.preferredHeight: 44
                        searchable: true
                        sectionRole: "group"
                        model: root.filteredActions(); textRole: "name"; valueRole: "id"
                        contentItem: Text { leftPadding: 13; text: actionBox.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12; elide: Text.ElideRight }
                        indicator: AppIcon { x: actionBox.width - width - 12; anchors.verticalCenter: parent.verticalCenter; width: 12; height: 12; name: "chevronDown"; color: Theme.muted }
                        background: Rectangle { color: Theme.cardHi; radius: 12; border.width: 1; border.color: actionBox.activeFocus ? Theme.primary : Theme.stroke }
                    }
                    FocusScope {
                        id: shortcutCapture
                        objectName: "shortcutCapture"
                        Layout.preferredWidth: 260; Layout.preferredHeight: 44
                        activeFocusOnTab: true
                        onActiveFocusChanged: if (!activeFocus) root.endCapture()
                        Keys.onPressed: (event) => root.captureKey(event)
                        Keys.onReleased: (event) => {
                            event.accepted = true
                            if (root.captureAwaitingRelease && event.modifiers === Qt.NoModifier)
                                root.endCapture()
                        }
                        Rectangle {
                            anchors.fill: parent; color: Theme.cardHi; radius: 12
                            border.width: 1; border.color: shortcutCapture.activeFocus && root.recording ? Theme.primary : Theme.stroke
                            Text {
                                anchors.fill: parent; anchors.leftMargin: 13; anchors.rightMargin: 13
                                verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
                                text: root.recording ? (root.capturePreview || root.t("Pulsa Ctrl + Alt + una tecla…", "Press Ctrl + Alt + a key…"))
                                     : (root.capturedCombo ? root.formatCombo(root.capturedCombo) : root.t("Haz clic para capturar", "Click to capture"))
                                color: root.capturedCombo || root.recording ? Theme.text : Theme.faint
                                font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold
                            }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.beginCapture() }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    PressSurface {
                        Layout.preferredWidth: 104; Layout.preferredHeight: 38; radius: 19; color: Theme.primary; accentColor: Theme.primary
                        onClicked: root.recording ? root.endCapture() : root.beginCapture()
                        Text { anchors.centerIn: parent; text: root.recording ? root.t("Cancelar", "Cancel") : root.t("Grabar", "Record"); color: "white"; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                    }
                    PressSurface {
                        Layout.preferredWidth: 100; Layout.preferredHeight: 38; radius: 19; color: Theme.primaryDark; accentColor: Theme.primary
                        onClicked: {
                            root.endCapture()
                            const actionId = root.selectedActionId()
                            root.feedback = actionId ? wizz.saveHotkey(actionId, root.capturedCombo) : root.t("Elige una acción y un valor válido.", "Choose an action and a valid value.")
                        }
                        Text { anchors.centerIn: parent; text: root.t("Guardar", "Save"); color: "white"; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                    }
                    PressSurface {
                        Layout.preferredWidth: 92; Layout.preferredHeight: 38; radius: 19; color: "transparent"; outlined: true; border.color: Theme.stroke
                        onClicked: {
                            const actionId = root.selectedActionId()
                            root.feedback = actionId && wizz.testHotkeyAction(actionId) ? root.t("Acción ejecutada.", "Action run.") : root.t("No se pudo ejecutar esta acción.", "Could not run this action.")
                        }
                        Text { anchors.centerIn: parent; text: root.t("Probar", "Test"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                    }
                    PressSurface {
                        Layout.preferredWidth: 92; Layout.preferredHeight: 38; radius: 19; color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.error
                        onClicked: { root.endCapture(); const actionId = root.selectedActionId(); if (actionId) wizz.clearHotkey(actionId); root.capturedCombo = ""; root.feedback = root.t("Atajo quitado.", "Shortcut removed.") }
                        Text { anchors.centerIn: parent; text: root.t("Quitar", "Remove"); color: Theme.error; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                    }
                    Item { Layout.fillWidth: true }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: customPicker.implicitHeight + 26
                    visible: root.editingPicker
                    color: Theme.bg; radius: 14; border.width: 1; border.color: Theme.stroke
                    WizColorPicker {
                        id: customPicker
                        objectName: "hotkeyCustomPicker"
                        anchors.fill: parent; anchors.margins: 13
                        selectionOnly: true
                        showColorSection: root.editingCustomColor
                        showWhiteSection: root.editingCustomWhite
                        selectedHex: root.customHex
                        selectedKelvin: root.customKelvin
                        onColorSelected: (hex) => root.customHex = hex
                        onWhiteSelected: (kelvin) => root.customKelvin = kelvin
                    }
                }
                RowLayout {
                    visible: root.editingPicker
                    Layout.fillWidth: true; spacing: 10
                    Rectangle {
                        Layout.preferredWidth: 32; Layout.preferredHeight: 32; radius: 10
                        color: root.editingCustomColor ? root.customHex : (root.customKelvin < 4100 ? "#ffe0a5" : "#d8efff")
                        border.width: 1; border.color: Theme.stroke
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.editingCustomColor ? root.t("HEX EXACTO", "EXACT HEX") : root.t("KELVIN EXACTO · 2200–6500 K", "EXACT KELVIN · 2200–6500 K")
                        color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold
                    }
                    TextField {
                        id: customHexField
                        visible: root.editingCustomColor
                        Layout.preferredWidth: 150; Layout.preferredHeight: 38
                        text: root.customHex; placeholderText: "#FF0000"; color: Theme.text; font.family: Theme.monoFont; font.pixelSize: Theme.labelSize
                        validator: RegularExpressionValidator { regularExpression: /#?[0-9a-fA-F]{0,6}/ }
                        onEditingFinished: {
                            const hex = root.normalizedHex(text)
                            if (hex) customPicker.sendHex(hex)
                            text = root.customHex
                        }
                        background: Rectangle { color: Theme.cardHi; radius: 10; border.width: 1; border.color: customHexField.activeFocus ? Theme.primary : Theme.stroke }
                    }
                    TextField {
                        id: customKelvinField
                        visible: root.editingCustomWhite
                        Layout.preferredWidth: 110; Layout.preferredHeight: 38
                        text: String(root.customKelvin); placeholderText: "4000"; color: Theme.text; font.family: Theme.monoFont; font.pixelSize: Theme.labelSize
                        validator: IntValidator { bottom: 2200; top: 6500 }
                        onEditingFinished: {
                            const value = Number(text)
                            if (value >= 2200 && value <= 6500) customPicker.chooseKelvin(value)
                            text = String(root.customKelvin)
                        }
                        background: Rectangle { color: Theme.cardHi; radius: 10; border.width: 1; border.color: customKelvinField.activeFocus ? Theme.primary : Theme.stroke }
                    }
                }
                Text { Layout.fillWidth: true; text: root.feedback; visible: text.length > 0; color: Theme.accent; font.pixelSize: Theme.labelSize; wrapMode: Text.WordWrap }
            }
        }

        Rectangle {
            width: parent.width; height: 136; radius: Theme.radiusMedium
            color: Theme.card; border.width: 1; border.color: Theme.stroke
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: root.t("PLANTILLAS ÚTILES", "USEFUL TEMPLATES"); color: Theme.muted; font.pixelSize: Theme.captionSize; font.weight: Font.Bold; font.letterSpacing: 1 }
                    Item { Layout.fillWidth: true }
                    PressSurface { Layout.preferredWidth: 166; Layout.preferredHeight: 32; radius: 16; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: wizz.resetHotkeys(); Text { anchors.centerIn: parent; text: root.t("Restaurar predeterminados", "Restore defaults"); color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold } }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 9
                    Repeater {
                        model: [
                            { name: root.t("Alternar", "Toggle"), action: "toggle", combo: "ctrl+alt+l" },
                            { name: root.t("Brillo +", "Brightness +"), action: "bri_up", combo: "ctrl+alt+up" },
                            { name: root.t("Brillo −", "Brightness −"), action: "bri_down", combo: "ctrl+alt+down" },
                            { name: root.t("Rojo", "Red"), action: "color_red", combo: "ctrl+alt+r" }
                        ]
                        delegate: PressSurface {
                            id: presetCard
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 58; radius: 11; accentColor: Theme.primary
                            onClicked: root.chooseAction(presetCard.modelData.action, presetCard.modelData.combo)
                            Column { anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 2; Text { text: presetCard.modelData.name; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold } Text { text: presetCard.modelData.combo; color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize } }
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width; height: assignedColumn.implicitHeight + 32; radius: Theme.radiusMedium
            color: Theme.card; border.width: 1; border.color: Theme.stroke
            Column {
                id: assignedColumn
                x: 16; y: 16; width: parent.width - 32; spacing: 8
                RowLayout {
                    width: parent.width; height: 30
                    Text { Layout.fillWidth: true; text: root.t("ATAJOS ASIGNADOS", "ASSIGNED SHORTCUTS"); color: Theme.muted; font.pixelSize: Theme.captionSize; font.weight: Font.Bold; font.letterSpacing: 1 }
                    PressSurface {
                        Layout.preferredWidth: 100; Layout.preferredHeight: 30; radius: 15
                        color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary
                        onClicked: { root.exportText = wizz.exportHotkeys(); exportDialog.open() }
                        Text { anchors.centerIn: parent; text: root.t("Exportar", "Export"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                    }
                }
                Repeater {
                    model: wizz.hotkeyModel
                    delegate: Rectangle {
                        id: assignedCard
                        required property string title
                        required property string subtitle
                        required property string uid
                        required property string rawValue
                        width: parent.width; height: 56; radius: 12
                        color: assignedPointer.containsMouse ? Theme.cardHi : Theme.bg
                        border.width: 1; border.color: assignedPointer.containsMouse ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.55) : Theme.stroke
                        Behavior on color { ColorAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } }
                        Behavior on border.color { ColorAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } }
                        MouseArea { id: assignedPointer; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.chooseAction(assignedCard.uid, assignedCard.rawValue) }
                        // Fixed rails keep every row readable at a glance:
                        // action on the left, shortcut in the visual centre,
                        // and destructive control at the far edge.
                        Rectangle {
                            x: 11; anchors.verticalCenter: parent.verticalCenter
                            width: 32; height: 32; radius: 10
                            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.16)
                            AppIcon { anchors.centerIn: parent; width: 15; height: 15; name: "keyboard"; color: Theme.primary }
                        }
                        Column {
                            x: 56; anchors.verticalCenter: parent.verticalCenter; width: 190; spacing: 1
                            Text { width: parent.width; text: assignedCard.title; color: Theme.text; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { width: parent.width; text: assignedCard.subtitle; color: Theme.faint; font.pixelSize: Theme.captionSize; elide: Text.ElideRight }
                        }
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.verticalCenter
                            width: 166; height: 30; radius: 9
                            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.08)
                            border.width: 1; border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.28)
                            Text { anchors.centerIn: parent; text: root.formatCombo(assignedCard.rawValue); color: Theme.accent; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                        }
                        PressSurface {
                            width: 30; height: 30; anchors.right: parent.right; anchors.rightMargin: 11; anchors.verticalCenter: parent.verticalCenter
                            radius: 15; color: "transparent"; accentColor: Theme.error
                            onClicked: wizz.clearHotkey(assignedCard.uid)
                            AppIcon { anchors.centerIn: parent; width: 13; height: 13; name: "close"; color: Theme.error }
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: exportDialog
        parent: Overlay.overlay; anchors.centerIn: parent
        width: Math.min(640, Overlay.overlay.width - 48); height: Math.min(500, Overlay.overlay.height - 48)
        modal: true; focus: true; dim: true; padding: 0; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 22; spacing: 12
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout { Layout.fillWidth: true; spacing: 2; Text { text: root.t("Exportar atajos", "Export shortcuts"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 21; font.weight: Font.Bold } Text { text: root.t("Copia este JSON para conservar tu configuración.", "Copy this JSON to keep your configuration."); color: Theme.muted; font.pixelSize: Theme.labelSize } }
                PressSurface { Layout.preferredWidth: 32; Layout.preferredHeight: 32; radius: 16; color: "transparent"; onClicked: exportDialog.close(); AppIcon { anchors.centerIn: parent; width: 14; height: 14; name: "close"; color: Theme.muted } }
            }
            TextArea {
                Layout.fillWidth: true; Layout.fillHeight: true
                readOnly: true; text: root.exportText; selectByMouse: true; wrapMode: TextEdit.WrapAnywhere
                color: Theme.text; font.family: Theme.monoFont; font.pixelSize: Theme.labelSize; leftPadding: 13; rightPadding: 13; topPadding: 12; bottomPadding: 12
                background: Rectangle { color: Theme.bg; radius: 12; border.width: 1; border.color: Theme.stroke }
            }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } PressSurface { Layout.preferredWidth: 92; Layout.preferredHeight: 38; radius: 19; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: exportDialog.close(); Text { anchors.centerIn: parent; text: root.t("Cerrar", "Close"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold } } }
        }
    }
}
