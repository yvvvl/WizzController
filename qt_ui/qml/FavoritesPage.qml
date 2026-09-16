pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    objectName: "favoritesPage"
    implicitHeight: pageContent.implicitHeight

    property string editingUid: ""
    property string editingName: ""
    property string editingKind: "rgb"
    property string editingValue: "#FF0000"
    property string editingSceneSource: "wiz:18"
    property string deletingUid: ""
    property string deletingName: ""
    property bool openEditorOnLoad: false
    property string qaEditorKind: ""

    function favoritePayload() {
        if (typeKind(typeBox.currentIndex) !== "scene") return valueField.text
        return JSON.stringify({ sceneId: Number(valueField.text || 18), speed: Math.round(sceneSpeed.value) })
    }

    Component.onCompleted: {
        if (openEditorOnLoad) Qt.callLater(function() {
            root.openNew()
            const index = root.typeIndex(root.qaEditorKind)
            if (root.qaEditorKind && index !== 0) {
                typeBox.currentIndex = index
                root.syncDefaultValue()
            }
        })
    }

    function typeIndex(kind) {
        if (kind === "white") return 1
        if (kind === "brightness") return 2
        if (kind === "scene") return 3
        return 0
    }

    function typeKind(index) {
        return ["rgb", "white", "brightness", "scene"][Math.max(0, Math.min(3, index))]
    }

    function previewColor() {
        if (typeBox.currentIndex === 0 && /^#[0-9a-fA-F]{6}$/.test(valueField.text)) return valueField.text
        if (typeBox.currentIndex === 1) return whitePreviewColor(valueField.text)
        if (typeBox.currentIndex === 2) return Theme.primary
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

    function sceneIndexForSource(source) {
        const choices = wizz.favoriteSceneChoices
        for (let index = 0; index < choices.length; ++index) {
            if (String(choices[index].source) === String(source)) return index
        }
        return 0
    }

    function selectedSceneLabel() {
        const choices = wizz.favoriteSceneChoices
        const index = sceneIndexForSource(editingSceneSource)
        return choices.length > index ? choices[index].title : "Escena WiZ"
    }

    function openNew() {
        editingUid = ""
        editingName = "Nuevo favorito"
        editingKind = "rgb"
        editingValue = "#FF4FA3"
        nameField.text = editingName
        typeBox.currentIndex = 0
        valueField.text = editingValue
        editingSceneSource = "wiz:18"
        sceneSpeed.value = 100
        editor.open()
    }

    function openEdit(uid, title, kind, rawValue) {
        editingUid = uid
        editingName = title
        editingKind = kind
        editingValue = rawValue
        nameField.text = title
        typeBox.currentIndex = typeIndex(kind)
        if (kind === "scene") {
            let payload = {}
            try { payload = JSON.parse(rawValue || "{}") } catch (error) { payload = {} }
            valueField.text = String(payload.sceneId || rawValue || 18)
            editingSceneSource = "wiz:" + valueField.text
            sceneSpeed.value = Number(payload.speed || 100)
        } else {
            valueField.text = rawValue
            sceneSpeed.value = 100
            editingSceneSource = "wiz:18"
        }
        editor.open()
    }

    function syncDefaultValue() {
        const kind = typeKind(typeBox.currentIndex)
        if (kind === "rgb" && valueField.text.indexOf("#") !== 0) valueField.text = "#FF4FA3"
        else if (kind === "white") valueField.text = "4000"
        else if (kind === "brightness") valueField.text = "70"
        else if (kind === "scene") {
            valueField.text = "18"
            editingSceneSource = "wiz:18"
        }
    }

    Column {
        id: pageContent
        width: parent.width
        spacing: 18

        Item {
            width: parent.width; height: 48
            Column {
                anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; spacing: 3
                Text { text: "Favoritos"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 30; font.weight: Font.Bold }
                Text { text: "Colores, blancos, escenas y brillo guardados"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 13 }
            }
            PressSurface {
                width: 112; height: 38; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                radius: 19
                color: "transparent"
                outlined: true
                accentColor: Theme.primary
                border.color: Theme.primary
                onClicked: root.openNew()
                Text { anchors.centerIn: parent; text: "+  Nuevo"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.DemiBold }
            }
        }

        GridLayout {
            id: favoriteGrid
            width: parent.width
            columns: width >= 930 ? 4 : width >= 650 ? 3 : 2
            columnSpacing: 12
            rowSpacing: 12

            Repeater {
                model: wizz.favoriteModel
                delegate: PressSurface {
                    id: favoriteCard
                    required property string title
                    required property string subtitle
                    required property color entryColor
                    required property string uid
                    required property string kind
                    required property string rawValue
                    Layout.fillWidth: true
                    Layout.preferredHeight: 136
                    radius: 16
                    accentColor: entryColor
                    onClicked: wizz.applyFavorite(favoriteCard.uid)

                    Rectangle {
                        x: 14; y: 14; width: 42; height: 42; radius: 13
                        color: favoriteCard.entryColor
                        Text {
                            anchors.centerIn: parent
                            text: favoriteCard.kind === "white" || favoriteCard.kind === "brightness" ? "\uE706" : favoriteCard.kind === "scene" ? "\uE8B2" : "\uE790"
                            color: favoriteCard.kind === "rgb" ? "white" : Theme.bg
                            font.family: Theme.iconFont; font.pixelSize: 18
                        }
                    }

                    Row {
                        anchors.right: parent.right; anchors.rightMargin: 10; y: 12; spacing: 4
                        PressSurface {
                            width: 34; height: 34; radius: 17; color: "transparent"; accentColor: Theme.primary
                            onClicked: root.openEdit(favoriteCard.uid, favoriteCard.title, favoriteCard.kind, favoriteCard.rawValue)
                            Text { anchors.centerIn: parent; text: "\uE70F"; color: Theme.primary; font.family: Theme.iconFont; font.pixelSize: 16 }
                        }
                        PressSurface {
                            width: 34; height: 34; radius: 17; color: "transparent"; accentColor: Theme.error
                            onClicked: { root.deletingUid = favoriteCard.uid; root.deletingName = favoriteCard.title; confirmDelete.open() }
                            Text { anchors.centerIn: parent; text: "\uE74D"; color: Theme.error; font.family: Theme.iconFont; font.pixelSize: 15 }
                        }
                    }

                    Column {
                        x: 14; y: 82; width: parent.width - 28; spacing: 3
                        Text { width: parent.width; text: favoriteCard.title; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        Text { width: parent.width; text: favoriteCard.subtitle; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11; elide: Text.ElideRight }
                    }
                }
            }
        }
    }

    Popup {
        id: editor
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(560, Overlay.overlay.width - 48)
        height: Math.min(720, Overlay.overlay.height - 24)
        modal: true
        focus: true
        dim: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 0
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }

        contentItem: ColumnLayout {
            spacing: 16
            anchors.fill: parent
            anchors.margins: 22

            Item {
                Layout.fillWidth: true; Layout.preferredHeight: 42
                Column {
                    anchors.left: parent.left; anchors.top: parent.top; anchors.right: closeFavorite.left; anchors.rightMargin: 12; spacing: 2
                    Text { text: root.editingUid ? "Editar favorito" : "Nuevo favorito"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 22; font.weight: Font.Bold }
                    Text { text: "Guarda un estado fácil de reconocer y aplicar."; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 12 }
                }
                PressSurface { id: closeFavorite; width: 34; height: 34; anchors.right: parent.right; anchors.top: parent.top; radius: 17; color: "transparent"; onClicked: editor.close(); Text { anchors.centerIn: parent; text: "×"; color: Theme.muted; font.pixelSize: 24 } }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 8
                visible: typeBox.currentIndex === 0
                Repeater {
                    model: ["#FF2D2D", "#0066FF", "#7C3AED", "#FF4FA3", "#7DFB83"]
                    delegate: PressSurface {
                        required property string modelData
                        Layout.preferredWidth: 32; Layout.preferredHeight: 32; radius: 16; accentColor: modelData
                        onClicked: valueField.text = modelData
                        Rectangle { anchors.centerIn: parent; width: 20; height: 20; radius: 10; color: modelData; border.width: valueField.text.toUpperCase() === modelData ? 2 : 0; border.color: "white" }
                    }
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 8
                visible: typeBox.currentIndex === 1
                Repeater {
                    model: [2200, 2700, 4000, 5000, 6500]
                    delegate: PressSurface {
                        required property int modelData
                        Layout.preferredWidth: 56; Layout.preferredHeight: 30; radius: 15; accentColor: "#ffd9a0"
                        onClicked: valueField.text = String(modelData)
                        Text { anchors.centerIn: parent; text: modelData + "K"; color: Theme.text; font.pixelSize: 9; font.weight: Font.DemiBold }
                    }
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 8
                visible: typeBox.currentIndex === 2
                Repeater {
                    model: [10, 25, 50, 75, 100]
                    delegate: PressSurface {
                        required property int modelData
                        Layout.preferredWidth: 46; Layout.preferredHeight: 30; radius: 15; accentColor: Theme.primary
                        onClicked: valueField.text = String(modelData)
                        Text { anchors.centerIn: parent; text: modelData + "%"; color: Theme.text; font.pixelSize: 9; font.weight: Font.DemiBold }
                    }
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 10; visible: typeBox.currentIndex === 3
                Text { text: "VELOCIDAD"; color: Theme.muted; font.pixelSize: 10; font.weight: Font.Bold }
                Slider {
                    id: sceneSpeed
                    Layout.fillWidth: true
                    from: 20; to: 200; value: 100; live: true
                    background: Rectangle {
                        x: sceneSpeed.leftPadding
                        y: sceneSpeed.topPadding + sceneSpeed.availableHeight / 2 - 2
                        width: sceneSpeed.availableWidth; height: 4; radius: 2
                        color: Theme.stroke
                        Rectangle { width: sceneSpeed.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.warning }
                    }
                    handle: Rectangle {
                        x: sceneSpeed.leftPadding + sceneSpeed.visualPosition * (sceneSpeed.availableWidth - width)
                        y: sceneSpeed.topPadding + sceneSpeed.availableHeight / 2 - height / 2
                        width: 18; height: 18; radius: 9; color: "white"
                        border.width: 2; border.color: Qt.rgba(0, 0, 0, 0.14)
                    }
                }
                Text { text: Math.round(sceneSpeed.value); color: Theme.text; font.pixelSize: 11; font.weight: Font.DemiBold }
            }

            Text { text: "NOMBRE"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 10; font.weight: Font.Bold }
            TextField {
                id: nameField
                Layout.fillWidth: true; Layout.preferredHeight: 46
                color: Theme.text; placeholderText: "Nombre del favorito"; placeholderTextColor: Theme.faint
                font.family: Theme.uiFont; font.pixelSize: 13; leftPadding: 14; rightPadding: 14
                background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: nameField.activeFocus ? Theme.primary : Theme.stroke }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 7
                    Text { text: "TIPO"; color: Theme.muted; font.pixelSize: 10; font.weight: Font.Bold }
                    WizComboBox {
                        id: typeBox
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        model: ["Color RGB", "Blanco CCT", "Brillo", "Escena WiZ"]
                        onActivated: root.syncDefaultValue()
                        contentItem: Text { leftPadding: 14; text: typeBox.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 13 }
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: typeBox.activeFocus ? Theme.primary : Theme.stroke }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 7
                    Text { text: typeBox.currentIndex === 0 ? "HEX" : typeBox.currentIndex === 1 ? "KELVIN" : typeBox.currentIndex === 2 ? "PORCENTAJE" : "ESCENA WIZ"; color: Theme.muted; font.pixelSize: 10; font.weight: Font.Bold }
                    TextField {
                        id: valueField
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        visible: typeBox.currentIndex !== 3
                        color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 13; leftPadding: 14; rightPadding: 14
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: valueField.activeFocus ? Theme.primary : Theme.stroke }
                    }
                    WizComboBox {
                        id: sceneChoiceBox
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        searchable: true
                        sectionRole: "group"
                        visible: typeBox.currentIndex === 3
                        model: wizz.favoriteSceneChoices
                        textRole: "label"
                        valueRole: "source"
                        currentIndex: root.sceneIndexForSource(root.editingSceneSource)
                        onActivated: root.editingSceneSource = String(currentValue)
                        contentItem: Text {
                            leftPadding: 14; rightPadding: 32
                            text: sceneChoiceBox.displayText
                            color: Theme.text; verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight; font.family: Theme.uiFont; font.pixelSize: 13
                        }
                        background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: sceneChoiceBox.activeFocus ? Theme.primary : Theme.stroke }
                    }
                }
            }

            WizPresetPicker {
                Layout.fillWidth: true
                visible: typeBox.currentIndex === 0 || typeBox.currentIndex === 1
                mode: typeBox.currentIndex === 1 ? "white" : "rgb"
                selection: valueField.text
                onPicked: function(value) { valueField.text = value }
            }

            Text { text: "VISTA PREVIA"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 10; font.weight: Font.Bold }
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 14
                color: root.previewColor()
                border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.18)
                RowLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 12
                    Rectangle { Layout.preferredWidth: 42; Layout.preferredHeight: 42; radius: 13; color: Qt.rgba(0, 0, 0, 0.16); Text { anchors.centerIn: parent; text: typeBox.currentIndex === 3 ? "✦" : "●"; color: "white"; font.pixelSize: 18 } }
                    ColumnLayout { Layout.fillWidth: true; spacing: 2; Text { text: nameField.text || "Nuevo favorito"; color: root.previewTextColor(); font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: typeBox.currentIndex === 3 ? root.selectedSceneLabel() + " · Velocidad " + Math.round(sceneSpeed.value) : valueField.text; color: Qt.rgba(Qt.color(root.previewTextColor()).r, Qt.color(root.previewTextColor()).g, Qt.color(root.previewTextColor()).b, 0.78); font.pixelSize: 11 } }
                }
            }

            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 100; Layout.preferredHeight: 40; radius: 20; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: editor.close(); Text { anchors.centerIn: parent; text: "Cancelar"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold } }
                PressSurface {
                    Layout.preferredWidth: 112; Layout.preferredHeight: 40; radius: 20; color: Theme.primary; accentColor: Theme.primary
                    onClicked: {
                        const isScene = root.typeKind(typeBox.currentIndex) === "scene"
                        const saved = isScene
                            ? wizz.upsertFavoriteFromScene(root.editingUid, nameField.text, root.editingSceneSource, Math.round(sceneSpeed.value))
                            : wizz.upsertFavorite(root.editingUid, nameField.text, root.typeKind(typeBox.currentIndex), root.favoritePayload())
                        if (saved) editor.close()
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
        width: Math.min(430, Overlay.overlay.width - 48); height: 220
        modal: true; focus: true; dim: true; padding: 0
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 22; spacing: 10
            Text { text: "Eliminar favorito"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 21; font.weight: Font.Bold }
            Text { Layout.fillWidth: true; text: "¿Quieres eliminar “" + root.deletingName + "”? Esta acción no afecta a la luz."; color: Theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; spacing: 10; Item { Layout.fillWidth: true } PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 40; radius: 20; color: "transparent"; border.color: Theme.stroke; onClicked: confirmDelete.close(); Text { anchors.centerIn: parent; text: "Cancelar"; color: Theme.text; font.pixelSize: 12 } } PressSurface { Layout.preferredWidth: 104; Layout.preferredHeight: 40; radius: 20; color: Theme.error; accentColor: Theme.error; onClicked: { wizz.deleteFavorite(root.deletingUid); confirmDelete.close() } Text { anchors.centerIn: parent; text: "Eliminar"; color: "white"; font.pixelSize: 12; font.weight: Font.Bold } } }
        }
    }
}
