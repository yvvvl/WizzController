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
    property string actionQuery: ""
    property string actionGroup: "Todas"
    property string exportText: ""
    property string customHex: "#ff0000"

    readonly property bool editingCustomColor: String(actionBox.currentValue || "") === "color_custom"

    function selectedActionId() {
        if (!editingCustomColor)
            return String(actionBox.currentValue || "")
        const raw = customHex.replace("#", "").replace(/[^0-9a-f]/gi, "").slice(0, 6)
        return raw.length === 6 ? "color_hex_" + raw.toLowerCase() : ""
    }

    function normalizedHex(value) {
        const raw = String(value || "").replace("#", "").replace(/[^0-9a-f]/gi, "").slice(0, 6)
        return raw.length === 6 ? "#" + raw.toUpperCase() : ""
    }

    function colorFromHsv(h, s, v) {
        return Qt.hsva(Math.max(0, Math.min(1, h / 360)), Math.max(0, Math.min(1, s / 100)), Math.max(0.1, Math.min(1, v / 100)), 1).toString().toUpperCase()
    }

    function actionGroups() {
        const groups = ["Todas"]
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
            return (actionGroup === "Todas" || group === actionGroup)
                && (!query || name.toLowerCase().indexOf(query) >= 0 || group.toLowerCase().indexOf(query) >= 0)
        })
    }

    function chooseAction(actionId, combo) {
        for (let i = 0; i < actionBox.count; ++i) {
            if (actionBox.valueAt(i) === actionId) {
                actionBox.currentIndex = i
                break
            }
        }
        comboField.text = combo || ""
    }

    Connections {
        target: wizz
        function onHotkeyCaptured(value) {
            root.recording = false
            if (value) {
                comboField.text = value
                root.feedback = "Combinación capturada. Revísala y guarda."
            } else {
                root.feedback = "La captura automática no está disponible; escribe la combinación manualmente."
            }
        }
    }

    Column {
        id: pageContent
        width: parent.width
        spacing: 16

        RowLayout {
            width: parent.width; spacing: 12
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                Text { text: "Hotkeys globales"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 30; font.weight: Font.Bold }
                Text { text: "Atajos para luz, escenas, favoritos y rutinas"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 13 }
            }
            Rectangle {
                Layout.preferredWidth: 300; Layout.preferredHeight: 38; radius: 19
                color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.10)
                border.width: 1; border.color: Theme.stroke
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14; spacing: 9
                    Rectangle { Layout.preferredWidth: 9; Layout.preferredHeight: 9; radius: 5; color: wizz.hotkeysEnabled && wizz.hotkeysAvailable ? Theme.success : Theme.warning }
                    Text { Layout.fillWidth: true; text: wizz.hotkeysStatus; color: Theme.muted; font.pixelSize: 11; elide: Text.ElideRight }
                }
            }
        }

        Rectangle {
            width: parent.width; height: 208; radius: Theme.radiusMedium
            color: Theme.card; border.width: 1; border.color: Theme.stroke
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                Text { text: "ESTADO"; color: Theme.muted; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Repeater {
                        model: [
                            { title: "Hotkeys activas", help: "Servicio global de la app", value: wizz.hotkeysEnabled, kind: "enabled" },
                            { title: "Capturar teclas", help: "Bloquea la pulsación al grabar", value: wizz.hotkeysSuppress, kind: "suppress" },
                            { title: "Ejecutar al soltar", help: "Evita repeticiones accidentales", value: wizz.hotkeysRelease, kind: "release" }
                        ]
                        delegate: Rectangle {
                            id: settingCard
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 66; radius: 12
                            color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 12; spacing: 8
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 2
                                    Text { text: settingCard.modelData.title; color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                                    Text { text: settingCard.modelData.help; color: Theme.faint; font.pixelSize: 9 }
                                }
                                Switch {
                                    id: switchControl
                                    checked: settingCard.modelData.value
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
                    Text { text: "Antirrebote"; color: Theme.muted; font.pixelSize: 11 }
                    Slider {
                        id: cooldown
                        Layout.fillWidth: true; from: 120; to: 900; stepSize: 60; value: wizz.hotkeysCooldown
                        onMoved: wizz.setHotkeysCooldown(Math.round(value))
                        background: Rectangle { x: cooldown.leftPadding; y: cooldown.topPadding + cooldown.availableHeight / 2 - 2; width: cooldown.availableWidth; height: 4; radius: 2; color: Theme.stroke; Rectangle { width: cooldown.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.accent } }
                        handle: Rectangle { x: cooldown.leftPadding + cooldown.visualPosition * (cooldown.availableWidth - width); y: cooldown.topPadding + cooldown.availableHeight / 2 - height / 2; width: 20; height: 20; radius: 10; color: Theme.text }
                    }
                    Text { text: Math.round(cooldown.value) + " ms"; color: Theme.muted; font.pixelSize: 11; Layout.preferredWidth: 54 }
                    PressSurface {
                        Layout.preferredWidth: 122; Layout.preferredHeight: 36; radius: 18; color: "transparent"; border.color: Theme.stroke
                        // Re-registering is a recovery action, not part of
                        // creating an empty set of shortcuts.  Keep it out
                        // of the primary flow until the backend has work to
                        // reconnect.
                        outlined: true; visible: wizz.hotkeysAvailable && wizz.hotkeyModel.rowCount() > 0 && wizz.hotkeysStatus !== "sin atajos"
                        onClicked: wizz.reregisterHotkeys()
                        Text { anchors.centerIn: parent; text: "↻  Re-registrar"; color: Theme.text; font.pixelSize: 10; font.weight: Font.DemiBold }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width; height: root.editingCustomColor ? 486 : 300; radius: Theme.radiusMedium
            color: Theme.card; border.width: 1; border.color: Theme.stroke
            Behavior on height { NumberAnimation { duration: Theme.motionNormal; easing.type: Easing.OutCubic } }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 11
                Text { text: "CREAR / EDITAR ATAJO"; color: Theme.muted; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                Text { text: "Elige una acción, escribe o captura la combinación y guárdala."; color: Theme.muted; font.pixelSize: 11 }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    WizComboBox {
                        id: groupBox
                        Layout.preferredWidth: 190; Layout.preferredHeight: 40
                        model: root.actionGroups()
                        currentIndex: Math.max(0, model.indexOf(root.actionGroup))
                        onActivated: root.actionGroup = currentText
                        contentItem: Text { leftPadding: 13; text: groupBox.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11; elide: Text.ElideRight }
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: groupBox.activeFocus ? Theme.primary : Theme.stroke }
                    }
                    TextField {
                        id: actionSearch
                        Layout.fillWidth: true; Layout.preferredHeight: 40
                        placeholderText: "Buscar acción"; placeholderTextColor: Theme.faint; color: Theme.text; leftPadding: 13; rightPadding: 13
                        onTextEdited: root.actionQuery = text
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: actionSearch.activeFocus ? Theme.primary : Theme.stroke }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    WizComboBox {
                        id: actionBox
                        Layout.fillWidth: true; Layout.preferredHeight: 44
                        searchable: true
                        sectionRole: "group"
                        model: root.filteredActions(); textRole: "name"; valueRole: "id"
                        contentItem: Text { leftPadding: 13; text: actionBox.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12; elide: Text.ElideRight }
                        indicator: Text { x: actionBox.width - width - 12; anchors.verticalCenter: parent.verticalCenter; text: "⌄"; color: Theme.muted; font.pixelSize: 18 }
                        background: Rectangle { color: Theme.cardHi; radius: 12; border.width: 1; border.color: actionBox.activeFocus ? Theme.primary : Theme.stroke }
                    }
                    TextField {
                        id: comboField
                        Layout.preferredWidth: 260; Layout.preferredHeight: 44
                        placeholderText: "ctrl+alt+l"; placeholderTextColor: Theme.faint; color: Theme.text; leftPadding: 13; rightPadding: 13
                        onTextEdited: root.feedback = ""
                        selectionColor: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.42)
                        background: Rectangle { color: Theme.cardHi; radius: 12; border.width: 1; border.color: comboField.activeFocus ? Theme.primary : Theme.stroke }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    PressSurface {
                        Layout.preferredWidth: 104; Layout.preferredHeight: 38; radius: 19; color: Theme.primary; accentColor: Theme.primary
                        enabled: !root.recording
                        onClicked: { root.recording = true; root.feedback = "Pulsa la combinación…"; wizz.recordHotkey() }
                        Text { anchors.centerIn: parent; text: root.recording ? "Escuchando…" : "⌨  Grabar"; color: "white"; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                    }
                    PressSurface {
                        Layout.preferredWidth: 100; Layout.preferredHeight: 38; radius: 19; color: Theme.primaryDark; accentColor: Theme.primary
                        onClicked: {
                            const actionId = root.selectedActionId()
                            root.feedback = actionId ? wizz.saveHotkey(actionId, comboField.text) : "Indica un color HEX válido."
                        }
                        Text { anchors.centerIn: parent; text: "▣  Guardar"; color: "white"; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                    }
                    PressSurface {
                        Layout.preferredWidth: 92; Layout.preferredHeight: 38; radius: 19; color: "transparent"; outlined: true; border.color: Theme.stroke
                        onClicked: {
                            const actionId = root.selectedActionId()
                            root.feedback = actionId && wizz.testHotkeyAction(actionId) ? "Acción ejecutada." : "No se pudo ejecutar esta acción."
                        }
                        Text { anchors.centerIn: parent; text: "▶  Probar"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                    }
                    PressSurface {
                        Layout.preferredWidth: 92; Layout.preferredHeight: 38; radius: 19; color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.error
                        onClicked: { const actionId = root.selectedActionId(); if (actionId) wizz.clearHotkey(actionId); comboField.text = ""; root.feedback = "Atajo quitado." }
                        Text { anchors.centerIn: parent; text: "×  Quitar"; color: Theme.error; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                    }
                    Item { Layout.fillWidth: true }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 218
                    visible: root.editingCustomColor
                    color: Theme.bg; radius: 14; border.width: 1; border.color: Theme.stroke
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 13; spacing: 9
                        RowLayout {
                            Layout.fillWidth: true; spacing: 10
                            Rectangle {
                                Layout.preferredWidth: 42; Layout.preferredHeight: 42; radius: 13
                                color: root.customHex; border.width: 2; border.color: Qt.rgba(Theme.highlight.r, Theme.highlight.g, Theme.highlight.b, 0.34)
                            }
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 2
                                Text { text: "COLOR PERSONALIZADO"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 11; font.weight: Font.Bold }
                                Text { text: root.customHex; color: Theme.muted; font.family: Theme.monoFont; font.pixelSize: 11 }
                            }
                            TextField {
                                id: customHexField
                                Layout.preferredWidth: 142; Layout.preferredHeight: 38
                                text: root.customHex; placeholderText: "#FF0000"; color: Theme.text; font.family: Theme.monoFont; font.pixelSize: 11
                                validator: RegularExpressionValidator { regularExpression: /#?[0-9a-fA-F]{0,6}/ }
                                onEditingFinished: { const hex = root.normalizedHex(text); if (hex) root.customHex = hex; text = root.customHex }
                                background: Rectangle { color: Theme.cardHi; radius: 10; border.width: 1; border.color: customHexField.activeFocus ? Theme.primary : Theme.stroke }
                            }
                        }
                        Text { text: "COLORES RÁPIDOS"; color: Theme.muted; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.8 }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 7
                            Repeater {
                                model: ["#FF0000", "#FF7F00", "#FFD000", "#00FF40", "#00D5FF", "#0055FF", "#7F00FF", "#FF4FA3", "#FFFFFF", "#FFBF75"]
                                delegate: PressSurface {
                                    required property string modelData
                                    Layout.fillWidth: true; Layout.preferredHeight: 31; radius: 10
                                    color: Qt.rgba(Qt.color(modelData).r, Qt.color(modelData).g, Qt.color(modelData).b, 0.18)
                                    accentColor: Qt.color(modelData)
                                    border.color: root.customHex === modelData ? Theme.text : Qt.rgba(Qt.color(modelData).r, Qt.color(modelData).g, Qt.color(modelData).b, 0.56)
                                    outlined: true; showTopHighlight: false
                                    onClicked: root.customHex = modelData
                                    Rectangle { anchors.centerIn: parent; width: 15; height: 15; radius: 8; color: parent.modelData; border.width: 1; border.color: Qt.rgba(Theme.highlight.r, Theme.highlight.g, Theme.highlight.b, 0.45) }
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 9
                            Text { text: "Matiz"; color: Theme.muted; font.pixelSize: 10; Layout.preferredWidth: 58 }
                            Slider {
                                id: hueSlider
                                Layout.fillWidth: true; from: 0; to: 360; stepSize: 1; value: 0
                                onMoved: root.customHex = root.colorFromHsv(value, saturationSlider.value, lightnessSlider.value)
                                background: Rectangle { x: hueSlider.leftPadding; y: hueSlider.topPadding + hueSlider.availableHeight / 2 - 2; width: hueSlider.availableWidth; height: 4; radius: 2; gradient: Gradient { GradientStop { position: 0; color: "#ff0000" } GradientStop { position: .17; color: "#ffff00" } GradientStop { position: .34; color: "#00ff40" } GradientStop { position: .51; color: "#00d5ff" } GradientStop { position: .68; color: "#0055ff" } GradientStop { position: .84; color: "#7f00ff" } GradientStop { position: 1; color: "#ff0000" } } }
                                handle: Rectangle { x: hueSlider.leftPadding + hueSlider.visualPosition * (hueSlider.availableWidth - width); y: hueSlider.topPadding + hueSlider.availableHeight / 2 - height / 2; width: 15; height: 15; radius: 8; color: Theme.text }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 9
                            Text { text: "Saturación"; color: Theme.muted; font.pixelSize: 10; Layout.preferredWidth: 58 }
                            Slider {
                                id: saturationSlider
                                Layout.fillWidth: true; from: 0; to: 100; stepSize: 1; value: 100
                                onMoved: root.customHex = root.colorFromHsv(hueSlider.value, value, lightnessSlider.value)
                                background: Rectangle { x: saturationSlider.leftPadding; y: saturationSlider.topPadding + saturationSlider.availableHeight / 2 - 2; width: saturationSlider.availableWidth; height: 4; radius: 2; color: Theme.stroke; Rectangle { width: saturationSlider.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.accent } }
                                handle: Rectangle { x: saturationSlider.leftPadding + saturationSlider.visualPosition * (saturationSlider.availableWidth - width); y: saturationSlider.topPadding + saturationSlider.availableHeight / 2 - height / 2; width: 15; height: 15; radius: 8; color: Theme.text }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 9
                            Text { text: "Luminosidad"; color: Theme.muted; font.pixelSize: 10; Layout.preferredWidth: 58 }
                            Slider {
                                id: lightnessSlider
                                Layout.fillWidth: true; from: 10; to: 100; stepSize: 1; value: 100
                                onMoved: root.customHex = root.colorFromHsv(hueSlider.value, saturationSlider.value, value)
                                background: Rectangle { x: lightnessSlider.leftPadding; y: lightnessSlider.topPadding + lightnessSlider.availableHeight / 2 - 2; width: lightnessSlider.availableWidth; height: 4; radius: 2; color: Theme.stroke; Rectangle { width: lightnessSlider.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.accent } }
                                handle: Rectangle { x: lightnessSlider.leftPadding + lightnessSlider.visualPosition * (lightnessSlider.availableWidth - width); y: lightnessSlider.topPadding + lightnessSlider.availableHeight / 2 - height / 2; width: 15; height: 15; radius: 8; color: Theme.text }
                            }
                        }
                    }
                }
                Text { Layout.fillWidth: true; text: root.feedback; visible: text.length > 0; color: Theme.accent; font.pixelSize: 11; wrapMode: Text.WordWrap }
            }
        }

        Rectangle {
            width: parent.width; height: 136; radius: Theme.radiusMedium
            color: Theme.card; border.width: 1; border.color: Theme.stroke
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "PLANTILLAS ÚTILES"; color: Theme.muted; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                    Item { Layout.fillWidth: true }
                    PressSurface { Layout.preferredWidth: 166; Layout.preferredHeight: 32; radius: 16; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: wizz.resetHotkeys(); Text { anchors.centerIn: parent; text: "↻  Restaurar predeterminados"; color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold } }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 9
                    Repeater {
                        model: [
                            { name: "Alternar", action: "toggle", combo: "ctrl+alt+l" },
                            { name: "Brillo +", action: "bri_up", combo: "ctrl+alt+up" },
                            { name: "Brillo −", action: "bri_down", combo: "ctrl+alt+down" },
                            { name: "Rojo", action: "color_red", combo: "ctrl+alt+r" }
                        ]
                        delegate: PressSurface {
                            id: presetCard
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 58; radius: 11; accentColor: Theme.primary
                            onClicked: root.chooseAction(presetCard.modelData.action, presetCard.modelData.combo)
                            Column { anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 2; Text { text: presetCard.modelData.name; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold } Text { text: presetCard.modelData.combo; color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: 9 } }
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
                    Text { Layout.fillWidth: true; text: "ATAJOS ASIGNADOS"; color: Theme.muted; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                    PressSurface {
                        Layout.preferredWidth: 100; Layout.preferredHeight: 30; radius: 15
                        color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary
                        onClicked: { root.exportText = wizz.exportHotkeys(); exportDialog.open() }
                        Text { anchors.centerIn: parent; text: "▣  Exportar"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold }
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
                            Text { anchors.centerIn: parent; text: "⌨"; color: Theme.primary; font.pixelSize: 14 }
                        }
                        Column {
                            x: 56; anchors.verticalCenter: parent.verticalCenter; width: 190; spacing: 1
                            Text { width: parent.width; text: assignedCard.title; color: Theme.text; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { width: parent.width; text: assignedCard.subtitle; color: Theme.faint; font.pixelSize: 9; elide: Text.ElideRight }
                        }
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.verticalCenter
                            width: 166; height: 30; radius: 9
                            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.08)
                            border.width: 1; border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.28)
                            Text { anchors.centerIn: parent; text: assignedCard.rawValue.toUpperCase().split("+").join("  +  "); color: Theme.accent; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold }
                        }
                        PressSurface {
                            width: 30; height: 30; anchors.right: parent.right; anchors.rightMargin: 11; anchors.verticalCenter: parent.verticalCenter
                            radius: 15; color: "transparent"; accentColor: Theme.error
                            onClicked: wizz.clearHotkey(assignedCard.uid)
                            Text { anchors.centerIn: parent; text: "×"; color: Theme.error; font.pixelSize: 18 }
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
                ColumnLayout { Layout.fillWidth: true; spacing: 2; Text { text: "Exportar atajos"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 21; font.weight: Font.Bold } Text { text: "Copia este JSON para conservar tu configuración."; color: Theme.muted; font.pixelSize: 11 } }
                PressSurface { Layout.preferredWidth: 32; Layout.preferredHeight: 32; radius: 16; color: "transparent"; onClicked: exportDialog.close(); Text { anchors.centerIn: parent; text: "×"; color: Theme.muted; font.pixelSize: 22 } }
            }
            TextArea {
                Layout.fillWidth: true; Layout.fillHeight: true
                readOnly: true; text: root.exportText; selectByMouse: true; wrapMode: TextEdit.WrapAnywhere
                color: Theme.text; font.family: Theme.monoFont; font.pixelSize: 11; leftPadding: 13; rightPadding: 13; topPadding: 12; bottomPadding: 12
                background: Rectangle { color: Theme.bg; radius: 12; border.width: 1; border.color: Theme.stroke }
            }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } PressSurface { Layout.preferredWidth: 92; Layout.preferredHeight: 38; radius: 19; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: exportDialog.close(); Text { anchors.centerIn: parent; text: "Cerrar"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 11; font.weight: Font.Bold } } }
        }
    }
}
