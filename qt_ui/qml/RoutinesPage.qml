pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    objectName: "routinesPage"
    implicitHeight: pageContent.implicitHeight

    property string editingUid: ""
    property string deletingUid: ""
    property string deletingName: ""
    property string feedback: ""
    property bool openEditorOnLoad: false

    function routinePreviewColor(kind, value) {
        if (kind === "rgb" && /^#[0-9a-fA-F]{6}$/.test(value)) return value
        const point = Math.max(0, Math.min(1, (Number(value || 4000) - 2200) / 4300))
        return Qt.rgba(1 - 0.16 * point, 0.847 + 0.09 * point, 0.584 + 0.416 * point, 1)
    }

    ListModel { id: actionDraft }

    Component.onCompleted: {
        if (openEditorOnLoad) Qt.callLater(root.openNew)
    }

    function defaultValue(kind) {
        if (kind === "wait") return "500"
        if (kind === "brightness") return "70"
        if (kind === "brightness_delta") return "10"
        if (kind === "rgb") return "#5F91FF"
        if (kind === "white_kelvin") return "4000"
        if (kind === "white_percent") return "50"
        if (kind === "scene") return "18"
        if (kind === "condition") return "power_on"
        if (kind === "target_mode") return "all"
        return ""
    }

    function actionLabel(kind) {
        const labels = {
            turn_on: "Encender", turn_off: "Apagar", toggle: "Alternar encendido",
            brightness: "Brillo", brightness_delta: "Ajustar brillo", rgb: "Color RGB",
            white_kelvin: "Blanco Kelvin", white_percent: "Blanco porcentual",
            scene: "Escena WiZ", favorite: "Aplicar favorito", custom_scene: "Escena personalizada",
            routine: "Ejecutar rutina", target_mode: "Cambiar destino", wait: "Esperar", condition: "Condición"
        }
        return labels[kind] || kind
    }

    function valueHint(kind) {
        if (kind === "wait") return "Milisegundos"
        if (kind === "brightness") return "10–100%"
        if (kind === "brightness_delta") return "Ej.: +10 o -10"
        if (kind === "rgb") return "#RRGGBB"
        if (kind === "white_kelvin") return "2200–6500K"
        if (kind === "white_percent") return "0–100%"
        if (kind === "scene") return "Scene ID"
        if (["favorite", "custom_scene", "routine"].indexOf(kind) >= 0) return "ID guardado"
        return ""
    }

    function loadActions(rawValue) {
        actionDraft.clear()
        let data = {}
        try { data = JSON.parse(rawValue || "{}") } catch (error) { data = {} }
        const actions = Array.isArray(data.actions) ? data.actions : []
        for (let i = 0; i < actions.length; ++i) {
            const action = actions[i] || {}
            let value = action.value
            if (action.type === "scene" && value && typeof value === "object")
                value = value.sceneId
            actionDraft.append({ kind: String(action.type || "wait"), value: value === undefined ? "" : String(value) })
        }
        if (actionDraft.count === 0) actionDraft.append({ kind: "turn_on", value: "" })
        return data
    }

    function openNew() {
        editingUid = ""
        routineName.text = "Nueva rutina"
        routineDescription.text = ""
        routineColor.text = "#5F91FF"
        actionDraft.clear()
        actionDraft.append({ kind: "turn_on", value: "" })
        actionDraft.append({ kind: "wait", value: "500" })
        editor.open()
    }

    function openEdit(uid, title, color, rawValue) {
        editingUid = uid
        routineName.text = title
        routineColor.text = String(color || "#5F91FF").toUpperCase()
        const data = loadActions(rawValue)
        routineDescription.text = String(data.description || "")
        editor.open()
    }

    function serializedActions() {
        const actions = []
        for (let i = 0; i < actionDraft.count; ++i) {
            const step = actionDraft.get(i)
            let value = step.value
            if (["wait", "brightness", "brightness_delta", "white_kelvin", "white_percent"].indexOf(step.kind) >= 0)
                value = Number(step.value || root.defaultValue(step.kind))
            else if (step.kind === "scene")
                value = { sceneId: Number(step.value || 18), speed: 100 }
            const item = { type: step.kind }
            if (["turn_on", "turn_off", "toggle"].indexOf(step.kind) < 0) item.value = value
            actions.push(item)
        }
        return JSON.stringify(actions)
    }

    Column {
        id: pageContent
        width: parent.width
        spacing: 16

        Item {
            width: parent.width; height: 48
            Column {
                anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; spacing: 3
                Text { text: "Rutinas"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 30; font.weight: Font.Bold }
                Text { text: "Secuencias visuales para acciones rápidas y hotkeys"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 13 }
            }
            Row {
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 10
            PressSurface {
                width: 142; height: 38; radius: 19
                color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary
                onClicked: { if (wizz.captureCurrentRoutine()) root.feedback = "Estado actual guardado como rutina." }
                Text { anchors.centerIn: parent; text: "▣  Capturar estado"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 11; font.weight: Font.DemiBold }
            }
            PressSurface {
                width: 154; height: 38; radius: 19
                color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.accent
                onClicked: wizz.resetRoutineDefaults()
                Text { anchors.centerIn: parent; text: "↻  Restaurar presets"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11; font.weight: Font.DemiBold }
            }
            PressSurface {
                width: 108; height: 38; radius: 19
                color: Theme.primary; accentColor: Theme.primary
                onClicked: root.openNew()
                Text { anchors.centerIn: parent; text: "+  Nueva"; color: "white"; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.Bold }
            }
            }
        }

        Rectangle {
            width: parent.width; height: 56; radius: Theme.radiusMedium
            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.10)
            border.width: 1; border.color: Theme.stroke
            RowLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                Text { text: "ⓘ"; color: Theme.primary; font.pixelSize: 17 }
                Text {
                    Layout.fillWidth: true
                    text: root.feedback || "Combina color, blanco, brillo, escenas, esperas y condiciones sin editar JSON."
                    color: root.feedback ? Theme.accent : Theme.muted; font.family: Theme.uiFont; font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }
        }

        Column {
            width: parent.width
            spacing: 10
            Repeater {
                model: wizz.routineModel
                delegate: PressSurface {
                    id: routineCard
                    required property string title
                    required property string subtitle
                    required property color entryColor
                    required property string uid
                    required property string rawValue
                    width: parent.width; height: 88; radius: 16; accentColor: entryColor
                    onClicked: wizz.runRoutine(routineCard.uid)

                    RowLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 14
                        Rectangle {
                            Layout.preferredWidth: 50; Layout.preferredHeight: 50; radius: 15
                            color: Qt.rgba(routineCard.entryColor.r, routineCard.entryColor.g, routineCard.entryColor.b, 0.22)
                            Text { anchors.centerIn: parent; text: "↯"; color: routineCard.entryColor; font.pixelSize: 23; font.weight: Font.Bold }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 3
                            Text { Layout.fillWidth: true; text: routineCard.title; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 16; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { Layout.fillWidth: true; text: routineCard.subtitle; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11; elide: Text.ElideRight }
                        }
                        PressSurface {
                            Layout.preferredWidth: 108; Layout.preferredHeight: 38; radius: 19; color: Theme.primary; accentColor: Theme.primary
                            onClicked: wizz.runRoutine(routineCard.uid)
                            Text { anchors.centerIn: parent; text: "▶  Aplicar"; color: "white"; font.pixelSize: 11; font.weight: Font.Bold }
                        }
                        PressSurface {
                            Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18; color: "transparent"; accentColor: Theme.primary
                            onClicked: root.openEdit(routineCard.uid, routineCard.title, routineCard.entryColor, routineCard.rawValue)
                            Text { anchors.centerIn: parent; text: "\uE70F"; color: Theme.primary; font.family: Theme.iconFont; font.pixelSize: 16 }
                        }
                        PressSurface {
                            Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18; color: "transparent"; accentColor: Theme.accent
                            onClicked: wizz.duplicateRoutine(routineCard.uid)
                            Text { anchors.centerIn: parent; text: "\uE8C8"; color: Theme.accent; font.family: Theme.iconFont; font.pixelSize: 16 }
                        }
                        PressSurface {
                            Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18; color: "transparent"; accentColor: Theme.error
                            onClicked: { root.deletingUid = routineCard.uid; root.deletingName = routineCard.title; confirmDelete.open() }
                            Text { anchors.centerIn: parent; text: "\uE74D"; color: Theme.error; font.family: Theme.iconFont; font.pixelSize: 16 }
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: editor
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(780, Overlay.overlay.width - 40)
        // The editor grows with the number of steps, rather than leaving a
        // large empty well when a routine is just being created.
        height: Math.min(690, Math.max(470, routineEditorContent.implicitHeight + 40))
        modal: true; focus: true; dim: true; padding: 0
        closePolicy: Popup.CloseOnEscape
        Overlay.modal: Rectangle { color: "#a3000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }

        contentItem: ColumnLayout {
            id: routineEditorContent
            anchors.fill: parent; anchors.margins: 20; spacing: 13
            Item {
                Layout.fillWidth: true; Layout.preferredHeight: 42
                Column {
                    anchors.left: parent.left; anchors.top: parent.top; anchors.right: closeRoutine.left; anchors.rightMargin: 12; spacing: 2
                    Text { text: root.editingUid ? "Editar rutina" : "Nueva rutina"; color: Theme.text; font.pixelSize: 22; font.weight: Font.Bold }
                    Text { text: "Construye la secuencia y ordena cada paso visualmente."; color: Theme.muted; font.pixelSize: 12 }
                }
                PressSurface { id: closeRoutine; width: 34; height: 34; anchors.right: parent.right; anchors.top: parent.top; radius: 17; color: "transparent"; onClicked: editor.close(); Text { anchors.centerIn: parent; text: "×"; color: Theme.muted; font.pixelSize: 24 } }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 10
                TextField {
                    id: routineName
                    Layout.fillWidth: true; Layout.preferredHeight: 44
                    placeholderText: "Nombre de la rutina"; placeholderTextColor: Theme.faint; color: Theme.text; leftPadding: 13; rightPadding: 13
                    background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: routineName.activeFocus ? Theme.primary : Theme.stroke }
                }
                TextField {
                    id: routineColor
                    Layout.preferredWidth: 130; Layout.preferredHeight: 44
                    placeholderText: "#5F91FF"; placeholderTextColor: Theme.faint; color: Theme.text; leftPadding: 13; rightPadding: 13
                    background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: routineColor.activeFocus ? Theme.primary : Theme.stroke }
                }
            }
            TextField {
                id: routineDescription
                Layout.fillWidth: true; Layout.preferredHeight: 44
                placeholderText: "Descripción corta"; placeholderTextColor: Theme.faint; color: Theme.text; leftPadding: 13; rightPadding: 13
                background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: routineDescription.activeFocus ? Theme.primary : Theme.stroke }
            }

            RowLayout {
                Layout.fillWidth: true
                Text { text: "PASOS"; color: Theme.muted; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                Item { Layout.fillWidth: true }
                Text { text: actionDraft.count + (actionDraft.count === 1 ? " paso" : " pasos"); color: Theme.faint; font.pixelSize: 11 }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(330, Math.max(132, actionDraft.count * 65 + 16))
                radius: 14
                color: Theme.bg; border.width: 1; border.color: Theme.stroke
                ListView {
                    id: stepList
                    anchors.fill: parent; anchors.margins: 8
                    spacing: 7; clip: true; model: actionDraft
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                    delegate: Rectangle {
                        id: stepRow
                        required property int index
                        required property string kind
                        required property string value
                        width: stepList.width; height: 58; radius: 11
                        color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 7; spacing: 8
                            Rectangle { Layout.preferredWidth: 28; Layout.preferredHeight: 28; radius: 9; color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.16); Text { anchors.centerIn: parent; text: String(stepRow.index + 1); color: Theme.primary; font.pixelSize: 11; font.weight: Font.Bold } }
                            WizComboBox {
                                id: actionType
                                Layout.preferredWidth: 176; Layout.preferredHeight: 40
                                searchable: true
                                sectionRole: "section"
                                model: [
                                    {label:"Encender", value:"turn_on", section:"Control"}, {label:"Apagar", value:"turn_off", section:"Control"}, {label:"Alternar", value:"toggle", section:"Control"},
                                    {label:"Brillo", value:"brightness", section:"Color y ambiente"}, {label:"Ajustar brillo", value:"brightness_delta", section:"Color y ambiente"}, {label:"Color RGB", value:"rgb", section:"Color y ambiente"}, {label:"Blanco Kelvin", value:"white_kelvin", section:"Color y ambiente"}, {label:"Blanco porcentual", value:"white_percent", section:"Color y ambiente"}, {label:"Escena WiZ", value:"scene", section:"Color y ambiente"},
                                    {label:"Aplicar favorito", value:"favorite", section:"Biblioteca"}, {label:"Escena personalizada", value:"custom_scene", section:"Biblioteca"}, {label:"Ejecutar rutina", value:"routine", section:"Biblioteca"},
                                    {label:"Esperar", value:"wait", section:"Flujo"}, {label:"Condición", value:"condition", section:"Flujo"}
                                ]
                                textRole: "label"; valueRole: "value"
                                function kindIndex(kind) {
                                    for (let option = 0; option < model.length; ++option) {
                                        if (model[option].value === kind)
                                            return option
                                    }
                                    return 0
                                }
                                currentIndex: actionType.kindIndex(stepRow.kind)
                                onActivated: function() {
                                    const nextKind = String(currentValue || "turn_on")
                                    actionDraft.setProperty(stepRow.index, "kind", nextKind)
                                    actionDraft.setProperty(stepRow.index, "value", root.defaultValue(nextKind))
                                }
                                contentItem: Text { leftPadding: 11; text: actionType.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12; elide: Text.ElideRight }
                                background: Rectangle { color: Theme.card; radius: 10; border.width: 1; border.color: actionType.activeFocus ? Theme.primary : Theme.stroke }
                            }
                            WizComboBox {
                                id: conditionValue
                                visible: stepRow.kind === "condition"
                                Layout.fillWidth: true; Layout.preferredHeight: 40
                                model: ["Luces encendidas", "Luces apagadas"]
                                currentIndex: stepRow.value === "power_off" ? 1 : 0
                                onActivated: function(index) { actionDraft.setProperty(stepRow.index, "value", index === 1 ? "power_off" : "power_on") }
                                contentItem: Text { leftPadding: 11; text: conditionValue.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12 }
                                background: Rectangle { color: Theme.card; radius: 10; border.width: 1; border.color: conditionValue.activeFocus ? Theme.primary : Theme.stroke }
                            }
                            WizComboBox {
                                id: targetModeValue
                                visible: stepRow.kind === "target_mode"
                                Layout.fillWidth: true; Layout.preferredHeight: 40
                                model: ["Todas las luces", "Sólo la selección"]
                                currentIndex: stepRow.value === "single" ? 1 : 0
                                onActivated: function(index) { actionDraft.setProperty(stepRow.index, "value", index === 1 ? "single" : "all") }
                                contentItem: Text { leftPadding: 11; text: targetModeValue.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12 }
                                background: Rectangle { color: Theme.card; radius: 10; border.width: 1; border.color: targetModeValue.activeFocus ? Theme.primary : Theme.stroke }
                            }
                            WizComboBox {
                                id: favoriteValue
                                visible: stepRow.kind === "favorite"
                                Layout.fillWidth: true; Layout.preferredHeight: 40
                                model: wizz.favoriteModel; textRole: "title"; valueRole: "uid"
                                currentIndex: Math.max(0, favoriteValue.indexOfValue(stepRow.value))
                                onActivated: actionDraft.setProperty(stepRow.index, "value", currentValue)
                                contentItem: Text { leftPadding: 11; text: favoriteValue.count ? favoriteValue.displayText : "Sin favoritos guardados"; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12; elide: Text.ElideRight }
                                background: Rectangle { color: Theme.card; radius: 10; border.width: 1; border.color: favoriteValue.activeFocus ? Theme.primary : Theme.stroke }
                            }
                            WizComboBox {
                                id: customSceneValue
                                visible: stepRow.kind === "custom_scene"
                                Layout.fillWidth: true; Layout.preferredHeight: 40
                                model: wizz.customSceneModel; textRole: "title"; valueRole: "uid"
                                currentIndex: Math.max(0, customSceneValue.indexOfValue(stepRow.value))
                                onActivated: actionDraft.setProperty(stepRow.index, "value", currentValue)
                                contentItem: Text { leftPadding: 11; text: customSceneValue.count ? customSceneValue.displayText : "Sin escenas personalizadas"; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12; elide: Text.ElideRight }
                                background: Rectangle { color: Theme.card; radius: 10; border.width: 1; border.color: customSceneValue.activeFocus ? Theme.primary : Theme.stroke }
                            }
                            WizComboBox {
                                id: nestedRoutineValue
                                visible: stepRow.kind === "routine"
                                Layout.fillWidth: true; Layout.preferredHeight: 40
                                model: wizz.routineModel; textRole: "title"; valueRole: "uid"
                                currentIndex: Math.max(0, nestedRoutineValue.indexOfValue(stepRow.value))
                                onActivated: actionDraft.setProperty(stepRow.index, "value", currentValue)
                                contentItem: Text { leftPadding: 11; text: nestedRoutineValue.count ? nestedRoutineValue.displayText : "Sin otras rutinas"; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12; elide: Text.ElideRight }
                                background: Rectangle { color: Theme.card; radius: 10; border.width: 1; border.color: nestedRoutineValue.activeFocus ? Theme.primary : Theme.stroke }
                            }
                            TextField {
                                id: actionValue
                                visible: ["turn_on", "turn_off", "toggle", "condition", "target_mode", "favorite", "custom_scene", "routine"].indexOf(stepRow.kind) < 0
                                Layout.fillWidth: true; Layout.preferredHeight: 40
                                text: stepRow.value; placeholderText: root.valueHint(stepRow.kind); placeholderTextColor: Theme.faint; color: Theme.text; leftPadding: 11; rightPadding: 11
                                onTextEdited: actionDraft.setProperty(stepRow.index, "value", text)
                                background: Rectangle { color: Theme.card; radius: 10; border.width: 1; border.color: actionValue.activeFocus ? Theme.primary : Theme.stroke }
                            }
                            PressSurface {
                                visible: stepRow.kind === "rgb" || stepRow.kind === "white_kelvin"
                                Layout.preferredWidth: visible ? 34 : 0; Layout.preferredHeight: 34; radius: 17
                                color: root.routinePreviewColor(stepRow.kind, stepRow.value); accentColor: Theme.primary
                                onClicked: routineValuePicker.openFor(stepRow.index, stepRow.kind, stepRow.value)
                                Text { anchors.centerIn: parent; text: "◉"; color: Qt.rgba(1, 1, 1, 0.9); font.pixelSize: 13 }
                            }
                            RowLayout {
                                visible: stepRow.kind === "wait"
                                Layout.preferredWidth: visible ? 150 : 0
                                spacing: 4
                                Repeater {
                                    model: [{label:"250ms", value:"250"}, {label:"1s", value:"1000"}, {label:"5s", value:"5000"}]
                                    delegate: PressSurface {
                                        required property var modelData
                                        Layout.preferredWidth: 42; Layout.preferredHeight: 28; radius: 14
                                        color: String(stepRow.value) === modelData.value ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.18) : Theme.card
                                        accentColor: Theme.primary
                                        onClicked: actionDraft.setProperty(stepRow.index, "value", modelData.value)
                                        Text { anchors.centerIn: parent; text: modelData.label; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 8; font.weight: Font.Bold }
                                    }
                                }
                            }
                            Item { visible: ["turn_on", "turn_off", "toggle"].indexOf(stepRow.kind) >= 0; Layout.fillWidth: true }
                            PressSurface { Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 15; color: "transparent"; enabled: stepRow.index > 0; opacity: enabled ? 1 : 0.3; onClicked: actionDraft.move(stepRow.index, stepRow.index - 1, 1); Text { anchors.centerIn: parent; text: "↑"; color: Theme.muted; font.pixelSize: 16 } }
                            PressSurface { Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 15; color: "transparent"; enabled: stepRow.index < actionDraft.count - 1; opacity: enabled ? 1 : 0.3; onClicked: actionDraft.move(stepRow.index, stepRow.index + 1, 1); Text { anchors.centerIn: parent; text: "↓"; color: Theme.muted; font.pixelSize: 16 } }
                            PressSurface { Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 15; color: "transparent"; accentColor: Theme.error; enabled: actionDraft.count > 1; opacity: enabled ? 1 : 0.3; onClicked: actionDraft.remove(stepRow.index); Text { anchors.centerIn: parent; text: "×"; color: Theme.error; font.pixelSize: 18 } }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 10
                PressSurface {
                    Layout.preferredWidth: 124; Layout.preferredHeight: 40; radius: 20; color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary
                    onClicked: actionDraft.append({ kind: "wait", value: "500" })
                    Text { anchors.centerIn: parent; text: "+  Agregar paso"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 11; font.weight: Font.Bold }
                }
                Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 94; Layout.preferredHeight: 40; radius: 20; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: editor.close(); Text { anchors.centerIn: parent; text: "Cancelar"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold } }
                PressSurface {
                    Layout.preferredWidth: 112; Layout.preferredHeight: 40; radius: 20; color: Theme.primary; accentColor: Theme.primary
                    onClicked: {
                        const result = wizz.upsertRoutine(root.editingUid, routineName.text, routineDescription.text, routineColor.text, root.serializedActions())
                        if (result) editor.close()
                    }
                    Text { anchors.centerIn: parent; text: "Guardar"; color: "white"; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                }
            }
        }
    }

    Popup {
        id: routineValuePicker
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(470, Overlay.overlay.width - 48); height: 300
        modal: true; focus: true; dim: true; padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        property int stepIndex: -1
        property string stepKind: "rgb"
        property string stepValue: "#5F91FF"
        function openFor(index, kind, value) {
            stepIndex = index; stepKind = kind; stepValue = value || root.defaultValue(kind); open()
        }
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 18; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 18; spacing: 10
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: routineValuePicker.stepKind === "rgb" ? "Color de este paso" : "Blanco de este paso"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 18; font.weight: Font.Bold }
                PressSurface { Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 15; color: "transparent"; onClicked: routineValuePicker.close(); Text { anchors.centerIn: parent; text: "×"; color: Theme.muted; font.pixelSize: 20 } }
            }
            WizPresetPicker {
                Layout.fillWidth: true
                mode: routineValuePicker.stepKind === "rgb" ? "rgb" : "white"
                selection: routineValuePicker.stepValue
                onPicked: function(value) { routineValuePicker.stepValue = value; actionDraft.setProperty(routineValuePicker.stepIndex, "value", value) }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 10
                color: root.routinePreviewColor(routineValuePicker.stepKind, routineValuePicker.stepValue)
                Text { anchors.centerIn: parent; text: routineValuePicker.stepKind === "rgb" ? routineValuePicker.stepValue.toUpperCase() : routineValuePicker.stepValue + "K"; color: Qt.color(parent.color).r * .299 + Qt.color(parent.color).g * .587 + Qt.color(parent.color).b * .114 > .72 ? Theme.bg : "white"; font.family: Theme.controlFont; font.pixelSize: 11; font.weight: Font.Bold }
            }
            Item { Layout.fillHeight: true }
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
            Text { text: "Eliminar rutina"; color: Theme.text; font.pixelSize: 21; font.weight: Font.Bold }
            Text { Layout.fillWidth: true; text: "¿Quieres eliminar “" + root.deletingName + "”?"; color: Theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true; spacing: 10; Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 40; radius: 20; color: "transparent"; border.color: Theme.stroke; onClicked: confirmDelete.close(); Text { anchors.centerIn: parent; text: "Cancelar"; color: Theme.text; font.pixelSize: 12 } }
                PressSurface { Layout.preferredWidth: 104; Layout.preferredHeight: 40; radius: 20; color: Theme.error; accentColor: Theme.error; onClicked: { wizz.deleteRoutine(root.deletingUid); confirmDelete.close() } Text { anchors.centerIn: parent; text: "Eliminar"; color: "white"; font.pixelSize: 12; font.weight: Font.Bold } }
            }
        }
    }
}
