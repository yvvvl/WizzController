pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    objectName: "scenesPage"
    implicitHeight: pageContent.implicitHeight

    property int selectedSceneId: 4
    property int sceneSpeed: 100
    property string editingCustomUid: ""
    property string deletingCustomUid: ""
    property string deletingCustomName: ""
    property bool openEditorOnLoad: false

    function t(spanish, english) { return wizz.language === "en" ? english : spanish }

    Component.onCompleted: {
        if (openEditorOnLoad) Qt.callLater(function() {
            root.openCustom("", "Mi escena", "rgb", "{}")
        })
    }

    function customTypeIndex(mode) {
        return mode === "white" ? 1 : mode === "scene" ? 2 : 0
    }

    function customType(index) {
        return ["rgb", "white", "scene"][Math.max(0, Math.min(2, index))]
    }

    function sceneNameFor(sceneId) {
        return wizz.sceneName(Number(sceneId))
    }

    function sceneChoiceIndex(sceneId) {
        const choices = wizz.sceneChoices
        for (let index = 0; index < choices.length; ++index) {
            if (Number(choices[index].sceneId) === Number(sceneId)) return index
        }
        return 0
    }

    function previewColor() {
        const kind = root.customType(customTypeBox.currentIndex)
        if (kind === "rgb" && /^#[0-9a-fA-F]{6}$/.test(customValue.text))
            return customValue.text
        if (kind === "white") {
            return root.whitePreviewColor(customValue.text)
        }
        return "#8b5cf6"
    }

    function whitePreviewColor(value) {
        const point = Math.max(0, Math.min(1, (Number(value || 4000) - 2200) / 4300))
        return Qt.rgba(1 - 0.16 * point, 0.847 + 0.09 * point, 0.584 + 0.416 * point, 1)
    }

    function previewTextColor() {
        const color = Qt.color(previewColor())
        return (color.r * 0.299 + color.g * 0.587 + color.b * 0.114) > 0.72 ? Theme.bg : "#ffffff"
    }

    function previewSubtitle() {
        const kind = root.customType(customTypeBox.currentIndex)
        if (kind === "rgb") return (customValue.text || "#FF4FA3").toUpperCase() + " · Brillo " + Math.round(customDimming.value) + "%"
        if (kind === "white") return (customValue.text || "4000") + "K · Brillo " + Math.round(customDimming.value) + "%"
        return root.sceneNameFor(customValue.text || 18) + " · Velocidad " + Math.round(customSpeed.value)
    }

    function openCustom(uid, title, mode, rawValue) {
        editingCustomUid = uid || ""
        customName.text = title || "Mi escena"
        customTypeBox.currentIndex = customTypeIndex(mode)
        let payload = {}
        try { payload = JSON.parse(rawValue || "{}") } catch (error) { payload = {} }
        if (mode === "white") customValue.text = String(payload.temp || 4000)
        else if (mode === "scene") customValue.text = String(payload.sceneId || 18)
        else customValue.text = "#" + [payload.r || 255, payload.g || 79, payload.b || 163].map(value => Number(value).toString(16).padStart(2, "0")).join("").toUpperCase()
        customDimming.value = Number(payload.dimming || 100)
        customSpeed.value = Number(payload.speed || 100)
        customEditor.open()
    }

    Column {
        id: pageContent
        width: parent.width
        spacing: 16

        Item {
            width: parent.width; height: 48
            Column {
                anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; spacing: 3
                Text { text: root.t("Escenas", "Scenes"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 30; font.weight: Font.Bold }
                Text { text: root.t("Escenas WiZ y escenas personalizadas locales", "WiZ scenes and local custom scenes"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 13 }
            }
            Row {
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                PressSurface {
                width: 146; height: 38; radius: 19
                color: "transparent"; outlined: true; border.color: Theme.primary; accentColor: Theme.primary
                onClicked: captureDialog.open()
                Text { anchors.centerIn: parent; text: root.t("☆  Guardar actual", "☆  Save current"); color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.DemiBold }
            }
            PressSurface {
                width: 126; height: 38; radius: 19
                color: Theme.primary; accentColor: Theme.primary
                onClicked: root.openCustom("", "Mi escena", "rgb", "{}")
                Text { anchors.centerIn: parent; text: root.t("+  Nueva escena", "+  New scene"); color: "white"; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.Bold }
            }
            }
        }

        Rectangle {
            width: parent.width; height: 86; radius: Theme.radiusMedium
            color: Theme.card; border.width: 1; border.color: Theme.stroke
            RowLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 14
                Rectangle {
                    Layout.preferredWidth: 48; Layout.preferredHeight: 48; radius: 15
                    color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.16)
                    Text { anchors.centerIn: parent; text: "\uE7F8"; color: Theme.warning; font.family: Theme.iconFont; font.pixelSize: 20 }
                }
                ColumnLayout {
                    Layout.preferredWidth: 158; spacing: 2
                    Text { text: root.t("Velocidad", "Speed"); color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 16; font.weight: Font.Bold }
                    Text { text: root.sceneNameFor(root.selectedSceneId); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11; elide: Text.ElideRight }
                }
                Slider {
                    id: speedSlider
                    Layout.fillWidth: true
                    from: 20; to: 200; value: root.sceneSpeed
                    live: true
                    onMoved: {
                        root.sceneSpeed = Math.round(value)
                        wizz.queueSceneSpeed(root.selectedSceneId, root.sceneSpeed)
                    }
                    background: Rectangle {
                        x: speedSlider.leftPadding
                        y: speedSlider.topPadding + speedSlider.availableHeight / 2 - 2
                        width: speedSlider.availableWidth; height: 4; radius: 2
                        color: Theme.stroke
                        Rectangle { width: speedSlider.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.warning }
                    }
                    handle: Rectangle {
                        x: speedSlider.leftPadding + speedSlider.visualPosition * (speedSlider.availableWidth - width)
                        y: speedSlider.topPadding + speedSlider.availableHeight / 2 - height / 2
                        width: 20; height: 20; radius: 10
                        color: "white"
                        border.width: 2; border.color: Qt.rgba(0, 0, 0, 0.12)
                    }
                }
                Text {
                    Layout.preferredWidth: 42
                    text: root.sceneSpeed
                    color: Theme.text
                    horizontalAlignment: Text.AlignRight
                    font.family: Theme.uiFont; font.pixelSize: 13; font.weight: Font.DemiBold
                }
                PressSurface {
                    Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17
                    color: "transparent"; accentColor: Theme.warning
                    onClicked: {
                        root.sceneSpeed = 100
                        speedSlider.value = 100
                        wizz.applyScene("wiz:" + root.selectedSceneId)
                    }
                    Text { anchors.centerIn: parent; text: "\uE777"; color: Theme.muted; font.family: Theme.iconFont; font.pixelSize: 16 }
                }
            }
        }

        Column {
            width: parent.width
            spacing: 10
            RowLayout {
                width: parent.width
                Text { text: root.t("MIS ESCENAS", "MY SCENES"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                Item { Layout.fillWidth: true }
                Text { text: customRepeater.count + " guardadas"; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: 11 }
            }
            Rectangle {
                width: parent.width; height: 54; radius: 12
                color: Theme.card; border.width: 1; border.color: Theme.stroke
                visible: customRepeater.count === 0
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left; anchors.leftMargin: 15
                    text: root.t("ⓘ  Aún no tienes escenas personalizadas.", "ⓘ  You do not have any custom scenes yet.")
                    color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11
                }
            }
            GridLayout {
                width: parent.width
                columns: width >= 940 ? 5 : width >= 700 ? 4 : 2
                columnSpacing: 10; rowSpacing: 10
                Repeater {
                    id: customRepeater
                    model: wizz.customSceneModel
                    delegate: PressSurface {
                        id: customCard
                        required property string title
                        required property string subtitle
                        required property color entryColor
                        required property string uid
                        required property string kind
                        required property string rawValue
                        Layout.fillWidth: true
                        Layout.preferredHeight: 112
                        radius: 16
                        accentColor: customCard.entryColor
                        onClicked: wizz.applyScene(customCard.uid)
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            y: 13; width: 40; height: 40; radius: 13
                            color: Qt.rgba(customCard.entryColor.r, customCard.entryColor.g, customCard.entryColor.b, 0.18)
                            Text { anchors.centerIn: parent; text: customCard.kind === "scene" ? "\uE734" : customCard.kind === "white" ? "\uE706" : "\uE790"; color: customCard.entryColor; font.family: Theme.iconFont; font.pixelSize: 18 }
                        }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; y: 60; width: parent.width - 18; text: customCard.title; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; y: 80; width: parent.width - 18; text: customCard.subtitle; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
                        Row {
                            anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 5; spacing: 2
                            PressSurface {
                                width: 28; height: 28; radius: 14; color: "transparent"; accentColor: Theme.primary
                                onClicked: root.openCustom(customCard.uid, customCard.title, customCard.kind, customCard.rawValue)
                                Text { anchors.centerIn: parent; text: "\uE70F"; color: Theme.primary; font.family: Theme.iconFont; font.pixelSize: 12 }
                            }
                            PressSurface {
                                width: 28; height: 28; radius: 14; color: "transparent"; accentColor: Theme.error
                                onClicked: {
                                    root.deletingCustomUid = customCard.uid
                                    root.deletingCustomName = customCard.title
                                    confirmDelete.open()
                                }
                                Text { anchors.centerIn: parent; text: "\uE74D"; color: Theme.error; font.family: Theme.iconFont; font.pixelSize: 12 }
                            }
                        }
                    }
                }
            }
        }

        Repeater {
            model: wizz.sceneGroups
            delegate: Column {
                id: groupBlock
                required property var modelData
                width: root.width
                spacing: 10
                Text { text: groupBlock.modelData.name.toUpperCase(); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 1 }
                GridLayout {
                    width: parent.width
                    columns: width >= 940 ? 7 : width >= 720 ? 5 : 3
                    columnSpacing: 10; rowSpacing: 10
                    Repeater {
                        model: groupBlock.modelData.scenes
                        delegate: PressSurface {
                            id: sceneCard
                            required property var modelData
                            property color cardColor: sceneCard.modelData.entryColor
                            Layout.fillWidth: true
                            Layout.preferredHeight: 104
                            radius: 16
                            accentColor: sceneCard.cardColor
                            selected: root.selectedSceneId === sceneCard.modelData.sceneId
                            onClicked: {
                                root.selectedSceneId = sceneCard.modelData.sceneId
                                wizz.applyScene("wiz:" + root.selectedSceneId)
                            }
                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                y: 12; width: 38; height: 38; radius: 12
                                // Scene artwork uses the app's icon font so
                                // it stays coherent with the rest of the UI.
                                color: "transparent"
                                Text { anchors.centerIn: parent; text: sceneCard.modelData.glyph; color: sceneCard.cardColor; font.family: Theme.iconFont; font.pixelSize: 22 }
                            }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; y: 57; width: parent.width - 14; text: sceneCard.modelData.title; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; y: 77; text: sceneCard.modelData.dynamic ? "dinámica" : "estática"; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: 9 }
                        }
                    }
                }
                Item { width: 1; height: 4 }
            }
        }
    }

    Popup {
        id: captureDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(440, Overlay.overlay.width - 48)
        height: 250
        modal: true; focus: true; dim: true; padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 22; spacing: 12
            Text { text: "Guardar escena actual"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 21; font.weight: Font.Bold }
            Text { text: "Captura color, blanco, brillo o escena activa."; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 12 }
            TextField {
                id: sceneName
                Layout.fillWidth: true; Layout.preferredHeight: 46
                text: "Mi escena"; color: Theme.text; font.family: Theme.uiFont; leftPadding: 14
                background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: sceneName.activeFocus ? Theme.primary : Theme.stroke }
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 94; Layout.preferredHeight: 40; radius: 20; color: "transparent"; border.color: Theme.stroke; onClicked: captureDialog.close(); Text { anchors.centerIn: parent; text: "Cancelar"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12 } }
                PressSurface { Layout.preferredWidth: 110; Layout.preferredHeight: 40; radius: 20; color: Theme.primary; onClicked: { if (wizz.captureCurrentScene(sceneName.text)) captureDialog.close() } Text { anchors.centerIn: parent; text: "Guardar"; color: "white"; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.Bold } }
            }
        }
    }

    Popup {
        id: customEditor
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(660, Overlay.overlay.width - 48)
        height: Math.min(720, Overlay.overlay.height - 18)
        modal: true; focus: true; dim: true; padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            anchors.bottomMargin: 22
            spacing: 13

            Item {
                Layout.fillWidth: true; Layout.preferredHeight: 42
                Column {
                    anchors.left: parent.left; anchors.top: parent.top; anchors.right: closeScene.left; anchors.rightMargin: 12; spacing: 2
                    Text { text: root.editingCustomUid ? "Editar escena" : "Nueva escena"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 22; font.weight: Font.Bold }
                    Text { text: "Guarda un preset local sin escribir JSON."; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 12 }
                }
                PressSurface { id: closeScene; width: 34; height: 34; anchors.right: parent.right; anchors.top: parent.top; radius: 17; color: "transparent"; onClicked: customEditor.close(); Text { anchors.centerIn: parent; text: "×"; color: Theme.muted; font.pixelSize: 24 } }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 92
                radius: 18
                color: root.previewColor()
                border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.16)
                RowLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 14
                    Rectangle {
                        Layout.preferredWidth: 50; Layout.preferredHeight: 50; radius: 16
                        color: Qt.rgba(0, 0, 0, 0.16)
                        Text { anchors.centerIn: parent; text: root.customType(customTypeBox.currentIndex) === "scene" ? "\uE734" : root.customType(customTypeBox.currentIndex) === "white" ? "\uE706" : "\uE790"; color: "white"; font.family: Theme.iconFont; font.pixelSize: 20 }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { Layout.fillWidth: true; text: customName.text || "Mi escena"; color: root.previewTextColor(); font.family: Theme.uiFont; font.pixelSize: 18; font.weight: Font.Bold; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; text: root.previewSubtitle(); color: Qt.rgba(Qt.color(root.previewTextColor()).r, Qt.color(root.previewTextColor()).g, Qt.color(root.previewTextColor()).b, 0.78); font.family: Theme.uiFont; font.pixelSize: 12; elide: Text.ElideRight }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 7
                    Text { text: "NOMBRE"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 10; font.weight: Font.Bold }
                    TextField {
                        id: customName
                        Layout.fillWidth: true; Layout.preferredHeight: 44
                        color: Theme.text; font.family: Theme.uiFont; leftPadding: 14; rightPadding: 14
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: customName.activeFocus ? Theme.primary : Theme.stroke }
                    }
                }
                ColumnLayout {
                    Layout.preferredWidth: 178; spacing: 7
                    Text { text: "TIPO"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 10; font.weight: Font.Bold }
                    WizComboBox {
                        id: customTypeBox
                        Layout.fillWidth: true; Layout.preferredHeight: 44
                        model: ["Color RGB", "Blanco CCT", "Escena WiZ"]
                        onActivated: function(index) { customValue.text = index === 0 ? "#FF4FA3" : index === 1 ? "4000" : "18" }
                        contentItem: Text { leftPadding: 14; text: customTypeBox.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.family: Theme.uiFont; font.pixelSize: 12 }
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: customTypeBox.activeFocus ? Theme.primary : Theme.stroke }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: customTypeBox.currentIndex === 0
                Repeater {
                    model: ["#FF2D2D", "#FF8A3D", "#FBBF24", "#7DFB83", "#00E5FF", "#0066FF", "#7C3AED", "#FF4FA3"]
                    delegate: PressSurface {
                        required property string modelData
                        Layout.preferredWidth: 32; Layout.preferredHeight: 32; radius: 16; accentColor: modelData
                        onClicked: customValue.text = modelData
                        Rectangle { anchors.centerIn: parent; width: 20; height: 20; radius: 10; color: modelData; border.width: customValue.text.toUpperCase() === modelData ? 2 : 0; border.color: "white" }
                    }
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: customTypeBox.currentIndex === 1
                Repeater {
                    model: [2200, 2700, 3120, 4000, 5000, 6500]
                    delegate: PressSurface {
                        required property int modelData
                        Layout.preferredWidth: 58; Layout.preferredHeight: 30; radius: 15; accentColor: "#ffd9a0"
                        onClicked: customValue.text = String(modelData)
                        Text { anchors.centerIn: parent; text: modelData + "K"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 9; font.weight: Font.DemiBold }
                    }
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: customTypeBox.currentIndex === 2
                Repeater {
                    model: [
                        { title: "Fiesta", value: 4, color: "#ec4899" },
                        { title: "Oceano", value: 6, color: "#38bdf8" },
                        { title: "Relax", value: 16, color: "#8b5cf6" },
                        { title: "TV / Cine", value: 18, color: "#7c3aed" },
                        { title: "Dia", value: 20, color: "#d8efff" }
                    ]
                    delegate: PressSurface {
                        required property var modelData
                        Layout.preferredWidth: 82; Layout.preferredHeight: 32; radius: 16; accentColor: modelData.color
                        onClicked: customValue.text = String(modelData.value)
                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 6
                            Rectangle { Layout.preferredWidth: 10; Layout.preferredHeight: 10; radius: 5; color: modelData.color }
                            Text { Layout.fillWidth: true; text: modelData.title; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 9; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        }
                    }
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 7
                    Text { text: customTypeBox.currentIndex === 0 ? "HEX" : customTypeBox.currentIndex === 1 ? "KELVIN" : "ESCENA WIZ"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 10; font.weight: Font.Bold }
                    TextField {
                        id: customValue
                        Layout.fillWidth: true; Layout.preferredHeight: 44
                        visible: customTypeBox.currentIndex !== 2
                        color: Theme.text; font.family: Theme.uiFont; leftPadding: 14; rightPadding: 14
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: customValue.activeFocus ? Theme.primary : Theme.stroke }
                    }
                    WizComboBox {
                        id: customSceneChoice
                        Layout.fillWidth: true; Layout.preferredHeight: 44
                        searchable: true
                        sectionRole: "group"
                        visible: customTypeBox.currentIndex === 2
                        model: wizz.sceneChoices; textRole: "label"; valueRole: "sceneId"
                        currentIndex: root.sceneChoiceIndex(customValue.text)
                        onActivated: customValue.text = String(currentValue)
                        contentItem: Text { leftPadding: 14; rightPadding: 32; text: customSceneChoice.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.family: Theme.uiFont; font.pixelSize: 12; elide: Text.ElideRight }
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: customSceneChoice.activeFocus ? Theme.primary : Theme.stroke }
                    }
                }
                ColumnLayout {
                    Layout.preferredWidth: 170; spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "BRILLO"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 10; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Text { text: Math.round(customDimming.value) + "%"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.Bold }
                    }
                    Slider {
                        id: customDimming
                        Layout.fillWidth: true
                        from: 10; to: 100; value: 100; live: true
                        background: Rectangle {
                            x: customDimming.leftPadding
                            y: customDimming.topPadding + customDimming.availableHeight / 2 - 2
                            width: customDimming.availableWidth; height: 4; radius: 2
                            color: Theme.stroke
                            Rectangle { width: customDimming.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.primary }
                        }
                        handle: Rectangle {
                            x: customDimming.leftPadding + customDimming.visualPosition * (customDimming.availableWidth - width)
                            y: customDimming.topPadding + customDimming.availableHeight / 2 - height / 2
                            width: 22; height: 22; radius: 11
                            color: Theme.text
                            border.width: 2; border.color: Qt.rgba(0, 0, 0, 0.14)
                        }
                    }
                }
            }

            WizPresetPicker {
                Layout.fillWidth: true
                visible: customTypeBox.currentIndex === 0 || customTypeBox.currentIndex === 1
                mode: customTypeBox.currentIndex === 1 ? "white" : "rgb"
                selection: customValue.text
                onPicked: function(value) { customValue.text = value }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: customTypeBox.currentIndex === 2
                Text { text: "VELOCIDAD"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 10; font.weight: Font.Bold }
                Slider {
                    id: customSpeed
                    Layout.fillWidth: true
                    from: 20; to: 200; value: 100; live: true
                    background: Rectangle {
                        x: customSpeed.leftPadding
                        y: customSpeed.topPadding + customSpeed.availableHeight / 2 - 2
                        width: customSpeed.availableWidth; height: 4; radius: 2
                        color: Theme.stroke
                        Rectangle { width: customSpeed.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.warning }
                    }
                    handle: Rectangle {
                        x: customSpeed.leftPadding + customSpeed.visualPosition * (customSpeed.availableWidth - width)
                        y: customSpeed.topPadding + customSpeed.availableHeight / 2 - height / 2
                        width: 22; height: 22; radius: 11
                        color: Theme.text
                        border.width: 2; border.color: Qt.rgba(0, 0, 0, 0.14)
                    }
                }
                Text { Layout.preferredWidth: 36; text: Math.round(customSpeed.value); color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.Bold; horizontalAlignment: Text.AlignRight }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 40; radius: 20; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: customEditor.close(); Text { anchors.centerIn: parent; text: "Cancelar"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold } }
                PressSurface {
                    Layout.preferredWidth: 110; Layout.preferredHeight: 40; radius: 20; color: Theme.primary; accentColor: Theme.primary
                    onClicked: {
                        if (wizz.upsertCustomScene(root.editingCustomUid, customName.text, root.customType(customTypeBox.currentIndex), customValue.text, Math.round(customDimming.value), Math.round(customSpeed.value)))
                            customEditor.close()
                    }
                    Text { anchors.centerIn: parent; text: "Guardar"; color: "white"; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                }
            }
        }
    }

    Popup {
        id: confirmDelete
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(430, Overlay.overlay.width - 48)
        height: 220
        modal: true; focus: true; dim: true; padding: 0
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 22; spacing: 10
            Text { text: "Eliminar escena"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 21; font.weight: Font.Bold }
            Text { Layout.fillWidth: true; text: "¿Quieres eliminar “" + root.deletingCustomName + "”? Esta acción no afecta a la luz."; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 12; wrapMode: Text.WordWrap }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 40; radius: 20; color: "transparent"; border.color: Theme.stroke; onClicked: confirmDelete.close(); Text { anchors.centerIn: parent; text: "Cancelar"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12 } }
                PressSurface { Layout.preferredWidth: 104; Layout.preferredHeight: 40; radius: 20; color: Theme.error; accentColor: Theme.error; onClicked: { wizz.deleteCustomScene(root.deletingCustomUid); confirmDelete.close() } Text { anchors.centerIn: parent; text: "Eliminar"; color: "white"; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.Bold } }
            }
        }
    }
}
