pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    objectName: "quickActionsEditor"
    implicitHeight: editorCard.implicitHeight
    property string editingKey: ""
    property string deletingKey: ""
    property string deletingName: ""
    property string selectionError: ""
    property string formError: ""
    property bool loadingEditor: false
    property real paletteHue: 0.67
    property real paletteWhiteness: 0.06
    readonly property var actionKinds: ["white", "rgb", "brightness", "scene", "on", "off"]

    function t(spanish, english) { return wizz.language === "en" ? english : spanish }

    function isActive(key) {
        const selected = wizz.quickActions
        for (let index = 0; index < selected.length; ++index)
            if (selected[index].key === key) return true
        return false
    }

    function toggleActive(key) {
        const selected = []
        const current = wizz.quickActions
        for (let index = 0; index < current.length; ++index)
            if (current[index].key !== key) selected.push(current[index].key)
        if (selected.length === current.length) {
            if (selected.length >= 6) {
                selectionError = t("Quita una acción antes de agregar otra.", "Remove an action before adding another.")
                return
            }
            selected.push(key)
        }
        selectionError = ""
        wizz.setQuickActions(selected)
    }

    function sceneIndex(value) {
        const choices = wizz.sceneChoices
        for (let index = 0; index < choices.length; ++index)
            if (String(choices[index].sceneId) === String(value)) return index
        return 0
    }

    function defaultValue(kind) {
        if (kind === "white") return "2700"
        if (kind === "rgb") return "#6697FF"
        if (kind === "brightness") return "50"
        if (kind === "scene") {
            const choices = wizz.sceneChoices
            return choices.length ? String(choices[0].sceneId) : ""
        }
        return ""
    }

    function rgbHex(red, green, blue) {
        function channel(value) { return Math.max(0, Math.min(255, value)).toString(16).padStart(2, "0") }
        return "#" + channel(red) + channel(green) + channel(blue)
    }

    function syncPalette(hex) {
        if (!/^#[0-9a-fA-F]{6}$/.test(hex)) return
        const r = parseInt(hex.slice(1, 3), 16) / 255
        const g = parseInt(hex.slice(3, 5), 16) / 255
        const b = parseInt(hex.slice(5, 7), 16) / 255
        const maximum = Math.max(r, g, b)
        const minimum = Math.min(r, g, b)
        const difference = maximum - minimum
        let hue = 0
        if (difference > 0) {
            if (maximum === r) hue = ((g - b) / difference) % 6
            else if (maximum === g) hue = (b - r) / difference + 2
            else hue = (r - g) / difference + 4
            hue = ((hue / 6) + 1) % 1
        }
        paletteHue = hue
        paletteWhiteness = 1 - (maximum > 0 ? minimum / maximum : 0)
    }

    function choosePaletteColor(px, py, pickerWidth, pickerHeight) {
        paletteHue = Math.max(0, Math.min(1, px / pickerWidth))
        paletteWhiteness = Math.max(0, Math.min(1, py / pickerHeight))
        const sector = paletteHue * 6
        const cross = 1 - Math.abs(sector % 2 - 1)
        let r = 0, g = 0, b = 0
        if (sector < 1) { r = 1; g = cross }
        else if (sector < 2) { r = cross; g = 1 }
        else if (sector < 3) { g = 1; b = cross }
        else if (sector < 4) { g = cross; b = 1 }
        else if (sector < 5) { r = cross; b = 1 }
        else { r = 1; b = cross }
        const white = 1 - paletteWhiteness
        valueField.text = rgbHex(Math.round((r + (1-r)*white) * 255),
                                 Math.round((g + (1-g)*white) * 255),
                                 Math.round((b + (1-b)*white) * 255)).toUpperCase()
    }

    function openEditor(action) {
        loadingEditor = true
        editingKey = action ? action.key : ""
        nameField.text = action ? action.name : ""
        const kind = action ? action.kind : "white"
        typeBox.currentIndex = actionKinds.indexOf(kind)
        valueField.text = action && action.value !== null ? String(action.value) : defaultValue(kind)
        loadingEditor = false
        formError = ""
        actionEditor.open()
        nameField.forceActiveFocus()
    }

    Rectangle {
        id: editorCard
        width: parent.width
        implicitHeight: editorContent.implicitHeight + 36
        radius: Theme.radiusMedium
        color: Theme.card
        border.width: 1
        border.color: Theme.stroke

        ColumnLayout {
            id: editorContent
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text { text: root.t("ACCIONES RÁPIDAS", "QUICK ACTIONS"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold; font.letterSpacing: 0.7 }
                    Text { Layout.fillWidth: true; text: root.t("Crea controles propios para las luces seleccionadas.", "Create your own controls for the selected lights."); color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; wrapMode: Text.WordWrap }
                }
                Text { text: wizz.quickActions.length + "/6"; color: Theme.primary; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
                PressSurface {
                    Layout.preferredWidth: 116; Layout.preferredHeight: 36
                    radius: 18; color: Theme.primary; accentColor: Theme.primary
                    onClicked: root.openEditor(null)
                    Text { anchors.centerIn: parent; text: "+ " + root.t("Crear", "Create"); color: "white"; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: wizz.customQuickActions.length === 0
                text: root.t("Aún no hay acciones personalizadas. Los presets siguen disponibles en el panel rápido.", "No custom actions yet. Built-in presets are still available in the Quick Panel.")
                color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: wizz.customQuickActions
                delegate: Rectangle {
                    id: actionRow
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 58
                    radius: 12; color: Theme.cardHi
                    border.width: 1; border.color: Theme.stroke
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 9; spacing: 10
                        Rectangle {
                            Layout.preferredWidth: 34; Layout.preferredHeight: 34
                            radius: 10
                            color: Qt.rgba(Qt.color(actionRow.modelData.color).r, Qt.color(actionRow.modelData.color).g, Qt.color(actionRow.modelData.color).b, 0.16)
                            AppIcon { anchors.centerIn: parent; width: 18; height: 18; glyph: actionRow.modelData.glyph; color: actionRow.modelData.color }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Text { Layout.fillWidth: true; text: actionRow.modelData.title; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { Layout.fillWidth: true; text: actionRow.modelData.detail; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; elide: Text.ElideRight }
                        }
                        PressSurface {
                            Layout.preferredWidth: 78; Layout.preferredHeight: 32
                            radius: 16; selected: root.isActive(actionRow.modelData.key)
                            accentColor: Theme.primary
                            onClicked: root.toggleActive(actionRow.modelData.key)
                            Text { anchors.centerIn: parent; text: root.isActive(actionRow.modelData.key) ? root.t("Visible", "Visible") : root.t("Mostrar", "Show"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
                        }
                        PressSurface {
                            Layout.preferredWidth: 72; Layout.preferredHeight: 32
                            radius: 16; color: "transparent"; outlined: true; border.color: Theme.stroke
                            onClicked: root.openEditor(actionRow.modelData)
                            Text { anchors.centerIn: parent; text: root.t("Editar", "Edit"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
                        }
                        PressSurface {
                            Layout.preferredWidth: 70; Layout.preferredHeight: 32
                            radius: 16; color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.error
                            onClicked: {
                                root.deletingKey = actionRow.modelData.key
                                root.deletingName = actionRow.modelData.name
                                deleteDialog.open()
                            }
                            Text { anchors.centerIn: parent; text: root.t("Borrar", "Delete"); color: Theme.error; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
                        }
                    }
                }
            }

            Text { visible: root.selectionError.length > 0; text: root.selectionError; color: Theme.warning; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize }
        }
    }

    Popup {
        id: actionEditor
        objectName: "quickActionPopup"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(460, Overlay.overlay.width - 40)
        height: Math.min(Overlay.overlay.height - 32,
                         typeBox.currentIndex === 1 ? 548 : typeBox.currentIndex === 0 ? 430 :
                         typeBox.currentIndex === 2 ? 414 : 326)
        modal: true; focus: true; dim: true; padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 22; spacing: 10
            Text { text: root.editingKey ? root.t("Editar acción rápida", "Edit quick action") : root.t("Nueva acción rápida", "New quick action"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 21; font.weight: Font.Bold }
            Text { text: root.t("Se aplicará a las luces seleccionadas.", "Applies to the selected lights."); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
            TextField {
                id: nameField
                Layout.fillWidth: true; Layout.preferredHeight: 43
                maximumLength: 32
                placeholderText: root.t("Nombre de la acción", "Action name")
                placeholderTextColor: Theme.muted
                color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold
                leftPadding: 13
                background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: nameField.activeFocus ? Theme.primary : Theme.stroke }
            }
            WizComboBox {
                id: typeBox
                objectName: "quickActionType"
                Layout.fillWidth: true; Layout.preferredHeight: 43
                model: wizz.language === "en"
                    ? ["White temperature", "RGB color", "Brightness", "WiZ scene", "Turn on", "Turn off"]
                    : ["Temperatura blanca", "Color RGB", "Brillo", "Escena WiZ", "Encender", "Apagar"]
                onCurrentIndexChanged: {
                    if (actionEditor.visible && !root.loadingEditor && currentIndex >= 0)
                        valueField.text = root.defaultValue(root.actionKinds[currentIndex])
                }
                contentItem: Text { leftPadding: 13; text: typeBox.displayText; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: typeBox.activeFocus ? Theme.primary : Theme.stroke }
            }

            ColumnLayout {
                Layout.fillWidth: true; spacing: 8
                visible: typeBox.currentIndex === 0
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: root.t("TEMPERATURA BLANCA", "WHITE TEMPERATURE"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                    Item { Layout.fillWidth: true }
                    Text { text: Math.round(whiteSlider.value) + " K"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 15; font.weight: Font.Bold }
                }
                Slider {
                    id: whiteSlider
                    objectName: "quickActionTemperature"
                    Layout.fillWidth: true; Layout.preferredHeight: 34
                    from: 2200; to: 6500; stepSize: 50
                    value: Math.max(2200, Math.min(6500, Number(valueField.text) || 2700))
                    onMoved: valueField.text = String(Math.round(value / 50) * 50)
                    background: Rectangle {
                        x: whiteSlider.leftPadding; y: whiteSlider.topPadding + whiteSlider.availableHeight / 2 - height / 2
                        width: whiteSlider.availableWidth; height: 12; radius: 6
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: "#ffe0a5" }
                            GradientStop { position: 0.5; color: "#fffdf4" }
                            GradientStop { position: 1; color: "#d8efff" }
                        }
                    }
                    handle: Rectangle { x: whiteSlider.leftPadding + whiteSlider.visualPosition * (whiteSlider.availableWidth - width); y: whiteSlider.topPadding + whiteSlider.availableHeight / 2 - height / 2; width: 22; height: 22; radius: 11; color: "#ffffff"; border.width: 2; border.color: Theme.card }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Repeater {
                        model: [2700, 4000, 6500]
                        delegate: PressSurface {
                            required property int modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 30; radius: 15
                            color: Number(valueField.text) === modelData ? Theme.cardHi : "transparent"
                            outlined: true; border.color: Number(valueField.text) === modelData ? Theme.primary : Theme.stroke
                            onClicked: valueField.text = String(modelData)
                            Text { anchors.centerIn: parent; text: modelData + " K"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true; spacing: 8
                visible: typeBox.currentIndex === 1
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: root.t("PALETA DE COLOR", "COLOR PALETTE"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                    Item { Layout.fillWidth: true }
                    Text { text: root.t("Elige o escribe un HEX", "Pick or enter a HEX value"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
                }
                Rectangle {
                    id: spectrum
                    objectName: "quickActionSpectrum"
                    Layout.fillWidth: true; Layout.preferredHeight: 150
                    radius: 13; clip: true; antialiasing: true
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: "#ff2b20" }
                        GradientStop { position: 0.16; color: "#fff000" }
                        GradientStop { position: 0.33; color: "#39f51c" }
                        GradientStop { position: 0.5; color: "#10e9ec" }
                        GradientStop { position: 0.67; color: "#1c45ff" }
                        GradientStop { position: 0.84; color: "#cd27ff" }
                        GradientStop { position: 1; color: "#ff2870" }
                    }
                    Rectangle {
                        anchors.fill: parent; radius: spectrum.radius
                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop { position: 0; color: "#ffffff" }
                            GradientStop { position: 0.78; color: "#00ffffff" }
                            GradientStop { position: 1; color: "#00ffffff" }
                        }
                    }
                    Rectangle {
                        width: 22; height: 22; radius: 11
                        x: Math.max(0, Math.min(spectrum.width - width, spectrum.width * root.paletteHue - width / 2))
                        y: Math.max(0, Math.min(spectrum.height - height, spectrum.height * root.paletteWhiteness - height / 2))
                        color: /^#[0-9a-fA-F]{6}$/.test(valueField.text) ? valueField.text : Theme.primary
                        border.width: 2; border.color: "white"
                    }
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.CrossCursor; preventStealing: true
                        onPressed: (mouse) => root.choosePaletteColor(mouse.x, mouse.y, width, height)
                        onPositionChanged: (mouse) => { if (pressed) root.choosePaletteColor(mouse.x, mouse.y, width, height) }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Repeater {
                        model: ["#FF6B6B", "#FFBD72", "#6697FF", "#58D69A", "#B392FF"]
                        delegate: PressSurface {
                            required property string modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 29; radius: 14
                            color: modelData; accentColor: modelData
                            onClicked: valueField.text = modelData
                            Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: "white"; visible: valueField.text.toUpperCase() === modelData }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true; spacing: 8
                visible: typeBox.currentIndex === 2
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: root.t("BRILLO", "BRIGHTNESS"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                    Item { Layout.fillWidth: true }
                    Text { text: Math.round(brightnessSlider.value) + "%"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 15; font.weight: Font.Bold }
                }
                Slider {
                    id: brightnessSlider
                    objectName: "quickActionBrightness"
                    Layout.fillWidth: true; Layout.preferredHeight: 34
                    from: 10; to: 100; stepSize: 1
                    value: Math.max(10, Math.min(100, Number(valueField.text) || 50))
                    onMoved: valueField.text = String(Math.round(value))
                    background: Rectangle {
                        x: brightnessSlider.leftPadding; y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2
                        width: brightnessSlider.availableWidth; height: 6; radius: 3; color: Theme.stroke
                        Rectangle { width: brightnessSlider.visualPosition * parent.width; height: parent.height; radius: parent.radius; color: Theme.primary }
                    }
                    handle: Rectangle { x: brightnessSlider.leftPadding + brightnessSlider.visualPosition * (brightnessSlider.availableWidth - width); y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2; width: 22; height: 22; radius: 11; color: Theme.text; border.width: 2; border.color: Theme.card }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 7
                    Repeater {
                        model: [10, 25, 50, 75, 100]
                        delegate: PressSurface {
                            required property int modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 29; radius: 14
                            color: Number(valueField.text) === modelData ? Theme.cardHi : "transparent"
                            outlined: true; border.color: Number(valueField.text) === modelData ? Theme.primary : Theme.stroke
                            onClicked: valueField.text = String(modelData)
                            Text { anchors.centerIn: parent; text: modelData + "%"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 10
                visible: typeBox.currentIndex < 3
                Rectangle {
                    visible: typeBox.currentIndex === 1
                    Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18
                    color: /^#[0-9a-fA-F]{6}$/.test(valueField.text) ? valueField.text : Theme.cardHi
                    border.width: 1; border.color: Theme.stroke
                }
                Text { text: typeBox.currentIndex === 1 ? "HEX" : root.t("VALOR EXACTO", "EXACT VALUE"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                TextField {
                    id: valueField
                    Layout.fillWidth: true; Layout.preferredHeight: 40
                    placeholderText: typeBox.currentIndex === 0 ? "2200–6500" : typeBox.currentIndex === 1 ? "#RRGGBB" : "10–100"
                    placeholderTextColor: Theme.muted
                    color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold
                    leftPadding: 12
                    onTextChanged: { if (typeBox.currentIndex === 1) root.syncPalette(text) }
                    background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: valueField.activeFocus ? Theme.primary : Theme.stroke }
                }
                Text { visible: typeBox.currentIndex !== 1; text: typeBox.currentIndex === 0 ? "K" : "%"; color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
            }
            WizComboBox {
                id: sceneBox
                Layout.fillWidth: true; Layout.preferredHeight: 43
                visible: typeBox.currentIndex === 3
                searchable: true; sectionRole: "group"
                model: wizz.sceneChoices; textRole: "label"; valueRole: "sceneId"
                currentIndex: root.sceneIndex(valueField.text)
                onActivated: valueField.text = String(currentValue)
                contentItem: Text { leftPadding: 13; rightPadding: 30; text: sceneBox.displayText; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: sceneBox.activeFocus ? Theme.primary : Theme.stroke }
            }
            Text {
                Layout.fillWidth: true
                visible: root.formError.length > 0
                text: root.formError
                color: Theme.warning; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize
                wrapMode: Text.WordWrap
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Item { Layout.fillWidth: true }
                PressSurface {
                    Layout.preferredWidth: 96; Layout.preferredHeight: 38; radius: 19
                    color: "transparent"; outlined: true; border.color: Theme.stroke
                    onClicked: actionEditor.close()
                    Text { anchors.centerIn: parent; text: root.t("Cancelar", "Cancel"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
                }
                PressSurface {
                    Layout.preferredWidth: 104; Layout.preferredHeight: 38; radius: 19
                    color: Theme.primary; accentColor: Theme.primary
                    onClicked: {
                        const saved = wizz.upsertQuickAction(root.editingKey, nameField.text, root.actionKinds[typeBox.currentIndex], valueField.text)
                        if (saved) {
                            actionEditor.close()
                            if (!root.isActive(saved))
                                root.selectionError = root.t("Acción guardada. Quita otra de las seis visibles para mostrarla.", "Action saved. Hide one of the six visible actions to show it.")
                            else
                                root.selectionError = ""
                        }
                        else root.formError = root.t("Revisa el nombre y el valor. Máximo 24 acciones personalizadas.", "Check the name and value. Maximum 24 custom actions.")
                    }
                    Text { anchors.centerIn: parent; text: root.t("Guardar", "Save"); color: "white"; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                }
            }
        }
    }

    Popup {
        id: deleteDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(410, Overlay.overlay.width - 40)
        height: 190
        modal: true; focus: true; dim: true; padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 20; spacing: 10
            Text { text: root.t("Borrar acción rápida", "Delete quick action"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 19; font.weight: Font.Bold }
            Text { Layout.fillWidth: true; text: root.t("¿Borrar “", "Delete “") + root.deletingName + "”?"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; wrapMode: Text.WordWrap }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Item { Layout.fillWidth: true }
                PressSurface {
                    Layout.preferredWidth: 95; Layout.preferredHeight: 36; radius: 18
                    color: "transparent"; outlined: true; border.color: Theme.stroke
                    onClicked: deleteDialog.close()
                    Text { anchors.centerIn: parent; text: root.t("Cancelar", "Cancel"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize }
                }
                PressSurface {
                    Layout.preferredWidth: 95; Layout.preferredHeight: 36; radius: 18
                    color: Theme.error; accentColor: Theme.error
                    onClicked: { wizz.deleteQuickAction(root.deletingKey); deleteDialog.close() }
                    Text { anchors.centerIn: parent; text: root.t("Borrar", "Delete"); color: "white"; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                }
            }
        }
    }
}
