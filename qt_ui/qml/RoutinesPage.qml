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
    property bool openScheduleEditorOnLoad: false
    property bool openScheduleTargetOnLoad: false
    property string editingScheduleUid: ""
    property string deletingScheduleUid: ""
    property var scheduleDays: [0, 1, 2, 3, 4, 5, 6]

    function t(spanish, english) { return wizz.language === "en" ? english : spanish }

    function scheduleTargets() {
        const options = [{label: root.t("Todas las luces", "All lights"), value: "all"}]
        const groups = wizz.routineGroups
        for (let i = 0; i < groups.length; ++i)
            options.push({label: root.t("Grupo: ", "Group: ") + groups[i].label, value: groups[i].value})
        const bulbs = wizz.routineBulbs
        for (let i = 0; i < bulbs.length; ++i)
            options.push({label: bulbs[i].label, value: bulbs[i].value})
        return options
    }

    function scheduleDayLabel(day) {
        const es = ["L", "M", "X", "J", "V", "S", "D"]
        const en = ["M", "T", "W", "T", "F", "S", "S"]
        return wizz.language === "en" ? en[day] : es[day]
    }

    function scheduleTargetLabel(value) {
        const choices = root.scheduleTargets()
        for (let i = 0; i < choices.length; ++i)
            if (choices[i].value === value) return choices[i].label
        return root.t("Destino no disponible", "Target unavailable")
    }

    function scheduleStatus(status) {
        if (status === "running") return root.t("En ejecución", "Running")
        if (status === "succeeded") return root.t("Última ejecución correcta", "Last run succeeded")
        if (status === "routine_deleted") return root.t("Rutina eliminada; horario desactivado", "Routine deleted; schedule disabled")
        if (String(status).startsWith("failed:")) return root.t("Falló la última ejecución", "Last run failed")
        return root.t("Aún no se ejecuta", "Not run yet")
    }

    function openNewSchedule() {
        editingScheduleUid = ""
        scheduleDays = [0, 1, 2, 3, 4, 5, 6]
        scheduleTime.text = "07:00"
        scheduleRoutine.currentIndex = 0
        scheduleTarget.currentIndex = 0
        scheduleEnabled.checked = true
        scheduleFeedback.text = ""
        scheduleEditor.open()
    }

    function openEditSchedule(row) {
        editingScheduleUid = row.id
        scheduleDays = Array.from(row.days)
        scheduleTime.text = row.time
        scheduleRoutine.currentIndex = scheduleRoutine.indexOfValue(row.routine_id)
        scheduleTarget.currentIndex = scheduleTarget.indexOfValue(row.target)
        scheduleEnabled.checked = row.enabled
        scheduleFeedback.text = ""
        scheduleEditor.open()
    }

    function supportsStepTarget(kind) {
        return ["turn_on", "turn_off", "toggle", "brightness", "brightness_delta", "rgb", "white_kelvin", "white_percent", "scene"].indexOf(kind) >= 0
    }

    function draftTarget(value) {
        return Array.isArray(value) ? "multi:" + JSON.stringify(value) : String(value || "")
    }

    function decodedTarget(value) {
        if (String(value).startsWith("multi:")) {
            try {
                const members = JSON.parse(String(value).slice(6))
                return Array.isArray(members) ? members : []
            } catch (error) { return [] }
        }
        return String(value || "")
    }

    function groupForTarget(value) {
        const groups = wizz.routineGroups
        for (let i = 0; i < groups.length; ++i)
            if (groups[i].value === value) return groups[i]
        return null
    }

    function bulbForTarget(value) {
        const bulbs = wizz.routineBulbs
        for (let i = 0; i < bulbs.length; ++i)
            if (bulbs[i].value === value) return bulbs[i]
        return null
    }

    function targetMembers(value) {
        const decoded = root.decodedTarget(value)
        if (Array.isArray(decoded)) return decoded
        if (decoded.startsWith("group:")) {
            const group = root.groupForTarget(decoded)
            return group ? group.members : []
        }
        return decoded.startsWith("mac:") || decoded.startsWith("ip:") ? [decoded] : []
    }

    function targetOptions(savedTarget) {
        const options = [
            {label: root.t("Selección actual", "Current selection"), value: ""},
            {label: root.t("Todas las luces", "All lights"), value: "all"}
        ]
        const groups = wizz.routineGroups
        for (let i = 0; i < groups.length; ++i)
            options.push({label: root.t("Grupo: ", "Group: ") + groups[i].label, value: groups[i].value})
        const bulbs = wizz.routineBulbs
        let found = savedTarget === "" || savedTarget === "all"
        for (let i = 0; i < bulbs.length; ++i) {
            const bulb = bulbs[i]
            options.push({label: bulb.label + (bulb.online ? "" : root.t(" (sin conexión)", " (offline)")), value: bulb.value})
            if (bulb.value === savedTarget) found = true
        }
        if (String(savedTarget).startsWith("group:")) found = root.groupForTarget(savedTarget) !== null
        if (String(savedTarget).startsWith("multi:")) {
            const count = root.targetMembers(savedTarget).length
            options.push({label: count + root.t(" ampolletas elegidas", " selected lights"), value: savedTarget})
            found = true
        }
        if (!found) options.push({label: root.t("Destino no disponible", "Unavailable target"), value: savedTarget})
        return options
    }

    function routinePreviewColor(kind, value) {
        if (kind === "rgb" && /^#[0-9a-fA-F]{6}$/.test(value)) return value
        const point = Math.max(0, Math.min(1, (Number(value || 4000) - 2200) / 4300))
        return Qt.rgba(1 - 0.16 * point, 0.847 + 0.09 * point, 0.584 + 0.416 * point, 1)
    }

    ListModel { id: actionDraft }

    Component.onCompleted: {
        if (openEditorOnLoad) Qt.callLater(root.openNew)
        if (openScheduleEditorOnLoad) Qt.callLater(function() {
            root.openNewSchedule()
            if (openScheduleTargetOnLoad) Qt.callLater(function() { scheduleTarget.popup.open() })
        })
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
            turn_on: root.t("Encender", "Turn on"), turn_off: root.t("Apagar", "Turn off"), toggle: root.t("Alternar encendido", "Toggle power"),
            brightness: root.t("Brillo", "Brightness"), brightness_delta: root.t("Ajustar brillo", "Adjust brightness"), rgb: root.t("Color RGB", "RGB color"),
            white_kelvin: root.t("Blanco Kelvin", "Kelvin white"), white_percent: root.t("Blanco porcentual", "White percentage"),
            scene: root.t("Escena WiZ", "WiZ scene"), favorite: root.t("Aplicar favorito", "Apply favorite"), custom_scene: root.t("Escena personalizada", "Custom scene"),
            routine: root.t("Ejecutar rutina", "Run routine"), target_mode: root.t("Cambiar destino", "Change target"), wait: root.t("Esperar", "Wait"), condition: root.t("Condición", "Condition")
        }
        return labels[kind] || kind
    }

    function valueHint(kind) {
        if (kind === "wait") return root.t("Milisegundos", "Milliseconds")
        if (kind === "brightness") return "10–100%"
        if (kind === "brightness_delta") return root.t("Ej.: +10 o -10", "E.g. +10 or -10")
        if (kind === "rgb") return "#RRGGBB"
        if (kind === "white_kelvin") return "2200–6500K"
        if (kind === "white_percent") return "0–100%"
        if (kind === "scene") return "Scene ID"
        if (["favorite", "custom_scene", "routine"].indexOf(kind) >= 0) return root.t("Valor guardado", "Saved value")
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
            actionDraft.append({ kind: String(action.type || "wait"), value: value === undefined ? "" : String(value), target: root.draftTarget(action.target) })
        }
        if (actionDraft.count === 0) actionDraft.append({ kind: "turn_on", value: "", target: "" })
        return data
    }

    function openNew() {
        editingUid = ""
        routineName.text = root.t("Nueva rutina", "New routine")
        routineDescription.text = ""
        routineColor.text = "#5F91FF"
        actionDraft.clear()
        actionDraft.append({ kind: "turn_on", value: "", target: "" })
        actionDraft.append({ kind: "wait", value: "500", target: "" })
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
            if (root.supportsStepTarget(step.kind) && step.target) item.target = root.decodedTarget(step.target)
            actions.push(item)
        }
        return JSON.stringify(actions)
    }

    Column {
        id: pageContent
        width: parent.width
        spacing: 16

        Item {
            id: routinesHeader
            objectName: "routinesHeader"
            width: parent.width; height: width < 830 ? 100 : 48
            Column {
                id: headerText
                objectName: "routinesHeaderText"
                width: routinesHeader.width < 830 ? routinesHeader.width : Math.max(0, routinesHeader.width - headerActions.width - 12)
                anchors.left: parent.left; anchors.top: parent.top; spacing: 3
                Text { text: root.t("Rutinas", "Routines"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: Theme.pageTitleSize; font.weight: Theme.pageTitleWeight }
                Text { width: headerText.width; elide: Text.ElideRight; text: root.t("Secuencias visuales para acciones rápidas y hotkeys", "Visual sequences for quick actions and hotkeys"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 13 }
            }
            Row {
                id: headerActions
                objectName: "routinesHeaderActions"
                x: routinesHeader.width - width; y: routinesHeader.width < 830 ? 58 : 5; spacing: 10
            PressSurface {
                width: 150; height: 38; radius: 19
                color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary
                onClicked: { if (wizz.captureCurrentRoutine()) root.feedback = root.t("Estado actual guardado como rutina.", "Current state saved as a routine.") }
                Text { anchors.centerIn: parent; text: root.t("Capturar estado", "Capture state"); color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
            }
            PressSurface {
                width: 154; height: 38; radius: 19
                color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.accent
                onClicked: wizz.resetRoutineDefaults()
                Text { anchors.centerIn: parent; text: root.t("Restaurar valores", "Restore defaults"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
            }
            PressSurface {
                width: 108; height: 38; radius: 19
                color: Theme.primary; accentColor: Theme.primary
                onClicked: root.openNew()
                Text { anchors.centerIn: parent; text: "+  " + root.t("Nueva", "New"); color: "white"; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.Bold }
            }
            }
        }

        Rectangle {
            width: parent.width; height: 56; radius: Theme.radiusMedium
            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.10)
            border.width: 1; border.color: Theme.stroke
            RowLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 12
                AppIcon { Layout.preferredWidth: 16; Layout.preferredHeight: 16; name: "info"; color: Theme.primary }
                Text {
                    Layout.fillWidth: true
                    text: root.feedback || root.t("Combina color, blanco, brillo, escenas, esperas y condiciones sin editar JSON.", "Combine color, white, brightness, scenes, waits, and conditions without editing JSON.")
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
                            AppIcon { anchors.centerIn: parent; width: 22; height: 22; name: "routines"; color: routineCard.entryColor }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 3
                            Text { Layout.fillWidth: true; text: routineCard.title; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 16; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { Layout.fillWidth: true; text: routineCard.subtitle; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; elide: Text.ElideRight }
                        }
                        PressSurface {
                            Layout.preferredWidth: 108; Layout.preferredHeight: 38; radius: 19; color: Theme.primary; accentColor: Theme.primary
                            onClicked: wizz.runRoutine(routineCard.uid)
                            Text { anchors.centerIn: parent; text: root.t("Aplicar", "Apply"); color: "white"; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                        }
                        PressSurface {
                            Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18; color: "transparent"; accentColor: Theme.primary
                            onClicked: root.openEdit(routineCard.uid, routineCard.title, routineCard.entryColor, routineCard.rawValue)
                            AppIcon { anchors.centerIn: parent; width: 15; height: 15; name: "edit"; color: Theme.primary }
                        }
                        PressSurface {
                            Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18; color: "transparent"; accentColor: Theme.accent
                            onClicked: wizz.duplicateRoutine(routineCard.uid)
                            AppIcon { anchors.centerIn: parent; width: 15; height: 15; name: "duplicate"; color: Theme.accent }
                        }
                        PressSurface {
                            Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18; color: "transparent"; accentColor: Theme.error
                            onClicked: { root.deletingUid = routineCard.uid; root.deletingName = routineCard.title; confirmDelete.open() }
                            AppIcon { anchors.centerIn: parent; width: 15; height: 15; name: "trash"; color: Theme.error }
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width; height: schedulesContent.implicitHeight + 32
            radius: Theme.radiusMedium; color: Theme.card
            border.width: 1; border.color: Theme.stroke
            ColumnLayout {
                id: schedulesContent
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                anchors.margins: 16; spacing: 12
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 3
                        Text { text: root.t("HORARIOS LOCALES", "LOCAL SCHEDULES"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 14; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("Ejecuta rutinas a la hora de este equipo. WizZ debe permanecer abierto, incluso en la bandeja.", "Run routines using this computer's clock. WizZ must stay open, including in the tray."); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; wrapMode: Text.WordWrap }
                    }
                    PressSurface {
                        Layout.preferredWidth: 154; Layout.preferredHeight: 38; radius: 19
                        color: Theme.primary; accentColor: Theme.primary
                        onClicked: root.openNewSchedule()
                        Text { anchors.centerIn: parent; text: root.t("+ Nuevo horario", "+ New schedule"); color: "white"; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                    }
                }
                Text { visible: wizz.routineScheduleError.length > 0; Layout.fillWidth: true; text: wizz.routineScheduleError; color: Theme.error; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; wrapMode: Text.WordWrap }
                Text { visible: wizz.routineSchedules.length === 0; text: root.t("Todavía no hay horarios. Crea uno para automatizar una rutina.", "No schedules yet. Create one to automate a routine."); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize }
                Repeater {
                    model: wizz.routineSchedules
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true; Layout.preferredHeight: 72
                        radius: 12; color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 10
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 4
                                Text { Layout.fillWidth: true; text: modelData.time + "  ·  " + modelData.routine_name; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 14; font.weight: Font.Bold; elide: Text.ElideRight }
                                Text { Layout.fillWidth: true; text: modelData.days.map(root.scheduleDayLabel).join(" ") + "  ·  " + root.scheduleTargetLabel(modelData.target) + "  ·  " + root.scheduleStatus(modelData.last_status); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; elide: Text.ElideRight }
                            }
                            PressSurface { Layout.preferredWidth: 88; Layout.preferredHeight: 34; radius: 17; color: modelData.enabled ? Theme.primary : Theme.card; accentColor: Theme.primary; onClicked: wizz.setRoutineScheduleEnabled(modelData.id, !modelData.enabled)
                                Text { anchors.centerIn: parent; text: modelData.enabled ? root.t("Activo", "On") : root.t("Pausado", "Paused"); color: modelData.enabled ? "white" : Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                            }
                            PressSurface { Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17; color: "transparent"; onClicked: root.openEditSchedule(modelData)
                                AppIcon { anchors.centerIn: parent; width: 15; height: 15; name: "edit"; color: Theme.primary }
                            }
                            PressSurface { Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17; color: "transparent"; onClicked: { root.deletingScheduleUid = modelData.id; confirmScheduleDelete.open() }
                                AppIcon { anchors.centerIn: parent; width: 15; height: 15; name: "trash"; color: Theme.error }
                            }
                        }
                    }
                }
                Text { Layout.fillWidth: true; text: root.t("Si el equipo está apagado o suspendido a esa hora, se omite la ejecución. Cada horario se ejecuta como máximo una vez por minuto y día local.", "Runs missed while the computer is off or asleep are skipped. Each schedule fires at most once per local day and minute."); color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; wrapMode: Text.WordWrap }
            }
        }
    }

    Popup {
        id: scheduleEditor
        parent: Overlay.overlay; anchors.centerIn: parent
        width: Math.min(490, Overlay.overlay.width - 40); height: 490
        modal: true; focus: true; dim: true; padding: 20
        closePolicy: Popup.CloseOnEscape
        Overlay.modal: Rectangle { color: "#a3000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            spacing: 12
            Text { text: root.editingScheduleUid ? root.t("Editar horario", "Edit schedule") : root.t("Nuevo horario", "New schedule"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 21; font.weight: Font.Bold }
            Text { Layout.fillWidth: true; text: root.t("La hora usa el reloj local de este equipo (formato 24 h).", "Time uses this computer's local clock (24-hour format)."); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; wrapMode: Text.WordWrap }
            Text { text: root.t("Rutina", "Routine"); color: Theme.text; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
            ComboBox {
                id: scheduleRoutine; Layout.fillWidth: true; Layout.preferredHeight: 40
                model: wizz.routineModel; textRole: "title"; valueRole: "uid"
                contentItem: Text { leftPadding: 12; rightPadding: 25; text: scheduleRoutine.displayText; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                background: Rectangle { color: Theme.cardHi; radius: 9; border.width: 1; border.color: scheduleRoutine.activeFocus ? Theme.primary : Theme.stroke }
                delegate: ItemDelegate {
                    required property int index
                    width: scheduleRoutine.width; text: scheduleRoutine.textAt(index)
                    contentItem: Text { text: parent.text; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                    background: Rectangle { color: parent.highlighted ? Theme.cardHi : Theme.card }
                }
                popup: Popup {
                    y: scheduleRoutine.height; width: scheduleRoutine.width
                    implicitHeight: Math.min(250, contentItem.implicitHeight + 8); padding: 4
                    contentItem: ListView { clip: true; implicitHeight: contentHeight; model: scheduleRoutine.popup.visible ? scheduleRoutine.delegateModel : null; currentIndex: scheduleRoutine.highlightedIndex; ScrollIndicator.vertical: ScrollIndicator {} }
                    background: Rectangle { color: Theme.card; radius: 9; border.width: 1; border.color: Theme.stroke }
                }
            }
            RowLayout { Layout.fillWidth: true; spacing: 12
                ColumnLayout { Layout.fillWidth: true; spacing: 4
                    Text { text: root.t("Hora (HH:MM)", "Time (HH:MM)"); color: Theme.text; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
                    TextField { id: scheduleTime; Layout.fillWidth: true; Layout.preferredHeight: 40; text: "07:00"; maximumLength: 5; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 16; background: Rectangle { color: Theme.cardHi; radius: 9; border.width: 1; border.color: scheduleTime.activeFocus ? Theme.primary : Theme.stroke } }
                }
                ColumnLayout { Layout.fillWidth: true; spacing: 4
                    Text { text: root.t("Destino predeterminado", "Default target"); color: Theme.text; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
                    ComboBox {
                        id: scheduleTarget; Layout.fillWidth: true; Layout.preferredHeight: 40
                        model: root.scheduleTargets(); textRole: "label"; valueRole: "value"
                        contentItem: Text { leftPadding: 12; rightPadding: 25; text: scheduleTarget.displayText; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                        background: Rectangle { color: Theme.cardHi; radius: 9; border.width: 1; border.color: scheduleTarget.activeFocus ? Theme.primary : Theme.stroke }
                        delegate: ItemDelegate {
                            required property int index
                            width: scheduleTarget.width; text: scheduleTarget.textAt(index)
                            contentItem: Text { text: parent.text; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                            background: Rectangle { color: parent.highlighted ? Theme.cardHi : Theme.card }
                        }
                        popup: Popup {
                            y: scheduleTarget.height; width: scheduleTarget.width
                            implicitHeight: Math.min(250, contentItem.implicitHeight + 8); padding: 4
                            contentItem: ListView { clip: true; implicitHeight: contentHeight; model: scheduleTarget.popup.visible ? scheduleTarget.delegateModel : null; currentIndex: scheduleTarget.highlightedIndex; ScrollIndicator.vertical: ScrollIndicator {} }
                            background: Rectangle { color: Theme.card; radius: 9; border.width: 1; border.color: Theme.stroke }
                        }
                    }
                }
            }
            Text { text: root.t("Días de la semana", "Days of the week"); color: Theme.text; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
            RowLayout { Layout.fillWidth: true; spacing: 6
                Repeater { model: 7; delegate: PressSurface {
                    required property int index
                    Layout.fillWidth: true; Layout.preferredHeight: 36; radius: 18
                    color: root.scheduleDays.indexOf(index) >= 0 ? Theme.primary : Theme.cardHi
                    accentColor: Theme.primary
                    onClicked: { const next = Array.from(root.scheduleDays); const pos = next.indexOf(index); if (pos >= 0) next.splice(pos, 1); else next.push(index); root.scheduleDays = next }
                    Text { anchors.centerIn: parent; text: root.scheduleDayLabel(index); color: root.scheduleDays.indexOf(index) >= 0 ? "white" : Theme.text; font.pixelSize: 13; font.weight: Font.Bold }
                } }
            }
            CheckBox {
                id: scheduleEnabled; checked: true; text: root.t("Horario activo", "Schedule enabled")
                indicator: Rectangle { x: 0; anchors.verticalCenter: parent.verticalCenter; width: 20; height: 20; radius: 5; color: scheduleEnabled.checked ? Theme.primary : Theme.cardHi; border.width: 1; border.color: Theme.primary
                    AppIcon { visible: scheduleEnabled.checked; anchors.centerIn: parent; width: 13; height: 13; name: "check"; color: "white" }
                }
                contentItem: Text { leftPadding: 29; text: scheduleEnabled.text; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; verticalAlignment: Text.AlignVCenter }
            }
            Text { Layout.fillWidth: true; text: root.t("Los destinos específicos de los pasos de la rutina tienen prioridad sobre este destino.", "Targets set on individual routine steps take priority over this default target."); color: Theme.faint; font.pixelSize: Theme.captionSize; wrapMode: Text.WordWrap }
            Text { id: scheduleFeedback; Layout.fillWidth: true; color: Theme.error; font.pixelSize: Theme.labelSize; wrapMode: Text.WordWrap }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; spacing: 8
                Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 90; Layout.preferredHeight: 38; radius: 19; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: scheduleEditor.close()
                    Text { anchors.centerIn: parent; text: root.t("Cancelar", "Cancel"); color: Theme.text; font.pixelSize: Theme.labelSize }
                }
                PressSurface { Layout.preferredWidth: 100; Layout.preferredHeight: 38; radius: 19; color: Theme.primary; accentColor: Theme.primary
                    onClicked: {
                        const uid = wizz.upsertRoutineSchedule(root.editingScheduleUid, String(scheduleRoutine.currentValue || ""), scheduleTime.text.trim(), JSON.stringify(root.scheduleDays), String(scheduleTarget.currentValue || ""), scheduleEnabled.checked)
                        if (uid) scheduleEditor.close()
                        else scheduleFeedback.text = wizz.routineScheduleError || root.t("No se pudo guardar el horario.", "Could not save the schedule.")
                    }
                    Text { anchors.centerIn: parent; text: root.t("Guardar", "Save"); color: "white"; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                }
            }
        }
    }

    Popup {
        id: confirmScheduleDelete
        parent: Overlay.overlay; anchors.centerIn: parent
        width: Math.min(390, Overlay.overlay.width - 48); height: 180
        modal: true; focus: true; dim: true; padding: 20
        closePolicy: Popup.CloseOnEscape
        Overlay.modal: Rectangle { color: "#a3000000" }
        background: Rectangle { color: Theme.card; radius: 18; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            spacing: 12
            Text { text: root.t("¿Eliminar este horario?", "Delete this schedule?"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 19; font.weight: Font.Bold }
            Text { Layout.fillWidth: true; text: root.t("La rutina seguirá disponible; solo se borrará su programación.", "The routine will remain available; only its schedule will be removed."); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; wrapMode: Text.WordWrap }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; spacing: 8
                Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 90; Layout.preferredHeight: 36; radius: 18; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: confirmScheduleDelete.close()
                    Text { anchors.centerIn: parent; text: root.t("Cancelar", "Cancel"); color: Theme.text; font.pixelSize: Theme.labelSize }
                }
                PressSurface { Layout.preferredWidth: 100; Layout.preferredHeight: 36; radius: 18; color: Theme.error; accentColor: Theme.error
                    onClicked: { if (wizz.deleteRoutineSchedule(root.deletingScheduleUid)) confirmScheduleDelete.close() }
                    Text { anchors.centerIn: parent; text: root.t("Eliminar", "Delete"); color: "white"; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
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
                    Text { text: root.editingUid ? root.t("Editar rutina", "Edit routine") : root.t("Nueva rutina", "New routine"); color: Theme.text; font.pixelSize: 22; font.weight: Font.Bold }
                    Text { text: root.t("Construye la secuencia y ordena cada paso visualmente.", "Build the sequence and arrange each step visually."); color: Theme.muted; font.pixelSize: 12 }
                }
                PressSurface { id: closeRoutine; width: 34; height: 34; anchors.right: parent.right; anchors.top: parent.top; radius: 17; color: "transparent"; onClicked: editor.close(); AppIcon { anchors.centerIn: parent; width: 14; height: 14; name: "close"; color: Theme.muted } }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 10
                TextField {
                    id: routineName
                    Layout.fillWidth: true; Layout.preferredHeight: 44
                    placeholderText: root.t("Nombre de la rutina", "Routine name"); placeholderTextColor: Theme.faint; color: Theme.text; leftPadding: 13; rightPadding: 13
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
                placeholderText: root.t("Descripción corta", "Short description"); placeholderTextColor: Theme.faint; color: Theme.text; leftPadding: 13; rightPadding: 13
                background: Rectangle { color: Theme.cardHi; radius: 11; border.width: 1; border.color: routineDescription.activeFocus ? Theme.primary : Theme.stroke }
            }

            RowLayout {
                Layout.fillWidth: true
                Text { text: root.t("PASOS", "STEPS"); color: Theme.muted; font.pixelSize: Theme.captionSize; font.weight: Font.Bold; font.letterSpacing: 1 }
                Item { Layout.fillWidth: true }
                Text { text: actionDraft.count + (actionDraft.count === 1 ? root.t(" paso", " step") : root.t(" pasos", " steps")); color: Theme.faint; font.pixelSize: Theme.labelSize }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(380, Math.max(132, actionDraft.count * (wizz.totalCount > 1 ? 107 : 65) + 16))
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
                        required property string target
                        readonly property bool showTarget: root.supportsStepTarget(kind) && (wizz.totalCount > 1 || target.length > 0)
                        width: stepList.width; height: showTarget ? 102 : 58; radius: 11
                        color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 7; spacing: 8
                            RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 42; spacing: 8
                            Rectangle { Layout.preferredWidth: 28; Layout.preferredHeight: 28; radius: 9; color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.16); Text { anchors.centerIn: parent; text: String(stepRow.index + 1); color: Theme.primary; font.pixelSize: Theme.labelSize; font.weight: Font.Bold } }
                            WizComboBox {
                                id: actionType
                                Layout.preferredWidth: 176; Layout.preferredHeight: 40
                                searchable: true
                                sectionRole: "section"
                                model: [
                                    {label:root.t("Encender", "Turn on"), value:"turn_on", section:root.t("Control", "Control")}, {label:root.t("Apagar", "Turn off"), value:"turn_off", section:root.t("Control", "Control")}, {label:root.t("Alternar", "Toggle"), value:"toggle", section:root.t("Control", "Control")},
                                    {label:root.t("Brillo", "Brightness"), value:"brightness", section:root.t("Color y ambiente", "Color and ambience")}, {label:root.t("Ajustar brillo", "Adjust brightness"), value:"brightness_delta", section:root.t("Color y ambiente", "Color and ambience")}, {label:root.t("Color RGB", "RGB color"), value:"rgb", section:root.t("Color y ambiente", "Color and ambience")}, {label:root.t("Blanco Kelvin", "Kelvin white"), value:"white_kelvin", section:root.t("Color y ambiente", "Color and ambience")}, {label:root.t("Blanco porcentual", "White percentage"), value:"white_percent", section:root.t("Color y ambiente", "Color and ambience")}, {label:root.t("Escena WiZ", "WiZ scene"), value:"scene", section:root.t("Color y ambiente", "Color and ambience")},
                                    {label:root.t("Aplicar favorito", "Apply favorite"), value:"favorite", section:root.t("Biblioteca", "Library")}, {label:root.t("Escena personalizada", "Custom scene"), value:"custom_scene", section:root.t("Biblioteca", "Library")}, {label:root.t("Ejecutar rutina", "Run routine"), value:"routine", section:root.t("Biblioteca", "Library")},
                                    {label:root.t("Esperar", "Wait"), value:"wait", section:root.t("Flujo", "Flow")}, {label:root.t("Condición", "Condition"), value:"condition", section:root.t("Flujo", "Flow")}
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
                                    if (!root.supportsStepTarget(nextKind)) actionDraft.setProperty(stepRow.index, "target", "")
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
                                model: [root.t("Todas las luces", "All lights"), root.t("Sólo la selección", "Selected lights only")]
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
                                contentItem: Text { leftPadding: 11; text: favoriteValue.count ? favoriteValue.displayText : root.t("Sin favoritos guardados", "No saved favorites"); color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12; elide: Text.ElideRight }
                                background: Rectangle { color: Theme.card; radius: 10; border.width: 1; border.color: favoriteValue.activeFocus ? Theme.primary : Theme.stroke }
                            }
                            WizComboBox {
                                id: customSceneValue
                                visible: stepRow.kind === "custom_scene"
                                Layout.fillWidth: true; Layout.preferredHeight: 40
                                model: wizz.customSceneModel; textRole: "title"; valueRole: "uid"
                                currentIndex: Math.max(0, customSceneValue.indexOfValue(stepRow.value))
                                onActivated: actionDraft.setProperty(stepRow.index, "value", currentValue)
                                contentItem: Text { leftPadding: 11; text: customSceneValue.count ? customSceneValue.displayText : root.t("Sin escenas personalizadas", "No custom scenes"); color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12; elide: Text.ElideRight }
                                background: Rectangle { color: Theme.card; radius: 10; border.width: 1; border.color: customSceneValue.activeFocus ? Theme.primary : Theme.stroke }
                            }
                            WizComboBox {
                                id: nestedRoutineValue
                                visible: stepRow.kind === "routine"
                                Layout.fillWidth: true; Layout.preferredHeight: 40
                                model: wizz.routineModel; textRole: "title"; valueRole: "uid"
                                currentIndex: Math.max(0, nestedRoutineValue.indexOfValue(stepRow.value))
                                onActivated: actionDraft.setProperty(stepRow.index, "value", currentValue)
                                contentItem: Text { leftPadding: 11; text: nestedRoutineValue.count ? nestedRoutineValue.displayText : root.t("Sin otras rutinas", "No other routines"); color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12; elide: Text.ElideRight }
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
                                AppIcon { anchors.centerIn: parent; width: 14; height: 14; name: "target"; color: Qt.rgba(1, 1, 1, 0.9) }
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
                                        Text { anchors.centerIn: parent; text: modelData.label; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                                    }
                                }
                            }
                            Item { visible: ["turn_on", "turn_off", "toggle"].indexOf(stepRow.kind) >= 0; Layout.fillWidth: true }
                            PressSurface { Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 15; color: "transparent"; enabled: stepRow.index > 0; opacity: enabled ? 1 : 0.3; onClicked: actionDraft.move(stepRow.index, stepRow.index - 1, 1); AppIcon { anchors.centerIn: parent; width: 12; height: 12; name: "arrowUp"; color: Theme.muted } }
                            PressSurface { Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 15; color: "transparent"; enabled: stepRow.index < actionDraft.count - 1; opacity: enabled ? 1 : 0.3; onClicked: actionDraft.move(stepRow.index, stepRow.index + 1, 1); AppIcon { anchors.centerIn: parent; width: 12; height: 12; name: "arrowDown"; color: Theme.muted } }
                            PressSurface { Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 15; color: "transparent"; accentColor: Theme.error; enabled: actionDraft.count > 1; opacity: enabled ? 1 : 0.3; onClicked: actionDraft.remove(stepRow.index); AppIcon { anchors.centerIn: parent; width: 13; height: 13; name: "close"; color: Theme.error } }
                            }
                            RowLayout {
                                visible: stepRow.showTarget
                                Layout.fillWidth: true; Layout.preferredHeight: visible ? 36 : 0; spacing: 8
                                Text { text: root.t("DESTINO", "TARGET"); color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold; Layout.preferredWidth: 56 }
                                WizComboBox {
                                    id: stepTarget
                                    Layout.fillWidth: true; Layout.preferredHeight: 34
                                    model: root.targetOptions(stepRow.target)
                                    textRole: "label"; valueRole: "value"
                                    currentIndex: Math.max(0, stepTarget.indexOfValue(stepRow.target))
                                    onActivated: actionDraft.setProperty(stepRow.index, "target", String(currentValue))
                                    contentItem: Text { leftPadding: 11; text: stepTarget.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: Theme.labelSize; elide: Text.ElideRight }
                                    background: Rectangle { color: Theme.card; radius: 9; border.width: 1; border.color: stepTarget.activeFocus ? Theme.primary : Theme.stroke }
                                }
                                PressSurface {
                                    Layout.preferredWidth: 82; Layout.preferredHeight: 34; radius: 9
                                    color: Theme.card; accentColor: Theme.primary
                                    onClicked: multiTargetPicker.openFor(stepRow.index, stepRow.target)
                                    Text { anchors.centerIn: parent; text: stepRow.target.startsWith("group:") || stepRow.target.startsWith("multi:") ? root.t("Editar", "Edit") : root.t("Varias…", "Multiple…"); color: Theme.primary; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true; spacing: 10
                PressSurface {
                    Layout.preferredWidth: 124; Layout.preferredHeight: 40; radius: 20; color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary
                    onClicked: actionDraft.append({ kind: "wait", value: "500", target: "" })
                    Text { anchors.centerIn: parent; text: "+  " + root.t("Agregar paso", "Add step"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                }
                Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 94; Layout.preferredHeight: 40; radius: 20; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: editor.close(); Text { anchors.centerIn: parent; text: root.t("Cancelar", "Cancel"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold } }
                PressSurface {
                    Layout.preferredWidth: 112; Layout.preferredHeight: 40; radius: 20; color: Theme.primary; accentColor: Theme.primary
                    onClicked: {
                        const result = wizz.upsertRoutine(root.editingUid, routineName.text, routineDescription.text, routineColor.text, root.serializedActions())
                        if (result) editor.close()
                    }
                    Text { anchors.centerIn: parent; text: root.t("Guardar", "Save"); color: "white"; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                }
            }
        }
    }

    Popup {
        id: multiTargetPicker
        objectName: "multiTargetPicker"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(510, Overlay.overlay.width - 40)
        height: Math.min(Overlay.overlay.height - 40, Math.min(570, Math.max(450, 325 + Math.min(250, multiTargetPicker.bulbChoices().length * 46 + 12))))
        modal: true; focus: true; dim: true; padding: 0
        closePolicy: Popup.CloseOnEscape
        property int stepIndex: -1
        property var selectedMembers: []
        property string editingGroupUid: ""
        property string feedback: ""
        property bool groupDeletePending: false

        function openFor(index, target) {
            stepIndex = index
            const group = root.groupForTarget(target)
            const members = root.targetMembers(target)
            selectedMembers = Array.from(members)
            editingGroupUid = group ? String(target).slice(6) : ""
            groupName.text = group ? group.label : ""
            feedback = ""
            groupDeletePending = false
            open()
        }

        function bulbChoices() {
            const choices = Array.from(wizz.routineBulbs)
            for (let i = 0; i < selectedMembers.length; ++i) {
                if (!root.bulbForTarget(selectedMembers[i]))
                    choices.push({label: root.t("No disponible: ", "Unavailable: ") + selectedMembers[i], value: selectedMembers[i], online: false})
            }
            return choices
        }

        function toggleMember(value) {
            const next = Array.from(selectedMembers)
            const index = next.indexOf(value)
            if (index >= 0) next.splice(index, 1)
            else next.push(value)
            selectedMembers = next
            feedback = ""
            groupDeletePending = false
        }

        function applySelection() {
            if (!selectedMembers.length) {
                feedback = root.t("Elige al menos una ampolleta.", "Choose at least one light.")
                return
            }
            const target = selectedMembers.length === 1 ? selectedMembers[0] : "multi:" + JSON.stringify(selectedMembers)
            actionDraft.setProperty(stepIndex, "target", target)
            close()
        }

        function saveGroup() {
            if (!selectedMembers.length || !groupName.text.trim()) {
                feedback = root.t("Pon un nombre y elige al menos una ampolleta.", "Name the group and choose at least one light.")
                return
            }
            const uid = wizz.upsertRoutineGroup(editingGroupUid, groupName.text, JSON.stringify(selectedMembers))
            if (!uid) {
                feedback = root.t("No se pudo guardar. Revisa si ya existe ese nombre.", "Could not save. Check whether that name already exists.")
                return
            }
            actionDraft.setProperty(stepIndex, "target", "group:" + uid)
            close()
        }

        background: Rectangle { color: Theme.card; radius: 18; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 20; spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Column {
                    Layout.fillWidth: true; spacing: 3
                    Text { text: root.t("Elegir ampolletas", "Choose lights"); color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 20; font.weight: Font.Bold }
                    Text { text: root.t("Esta selección afecta solo a este paso.", "This selection applies only to this step."); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize }
                }
                PressSurface { Layout.preferredWidth: 32; Layout.preferredHeight: 32; radius: 16; color: "transparent"; onClicked: multiTargetPicker.close(); AppIcon { anchors.centerIn: parent; width: 14; height: 14; name: "close"; color: Theme.muted } }
            }
            Text { text: multiTargetPicker.selectedMembers.length + root.t(" seleccionadas", " selected"); color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize }
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: Math.min(250, Math.max(60, multiTargetPicker.bulbChoices().length * 46 + 12))
                radius: 12; color: Theme.bg; border.width: 1; border.color: Theme.stroke
                ListView {
                    anchors.fill: parent; anchors.margins: 6; clip: true; spacing: 4
                    model: multiTargetPicker.bulbChoices()
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                    delegate: PressSurface {
                        required property var modelData
                        width: ListView.view.width; height: 42; radius: 9
                        color: multiTargetPicker.selectedMembers.indexOf(modelData.value) >= 0 ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.13) : Theme.cardHi
                        accentColor: Theme.primary
                        onClicked: multiTargetPicker.toggleMember(modelData.value)
                        Rectangle {
                            x: 10; anchors.verticalCenter: parent.verticalCenter
                            width: 19; height: 19; radius: 5
                            color: multiTargetPicker.selectedMembers.indexOf(modelData.value) >= 0 ? Theme.primary : "transparent"
                            border.width: 1; border.color: Theme.primary
                            AppIcon { visible: multiTargetPicker.selectedMembers.indexOf(modelData.value) >= 0; anchors.centerIn: parent; width: 12; height: 12; name: "check"; color: "white" }
                        }
                        Text { x: 39; width: parent.width - 49; anchors.verticalCenter: parent.verticalCenter; text: modelData.label; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; elide: Text.ElideRight }
                    }
                }
            }
            Text { text: root.t("GUARDAR COMO GRUPO REUTILIZABLE", "SAVE AS A REUSABLE GROUP"); color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                TextField {
                    id: groupName
                    objectName: "routineGroupName"
                    Layout.fillWidth: true; Layout.preferredHeight: 40
                    maximumLength: 80
                    placeholderText: root.t("Ej.: Sala de estar", "E.g. Living room")
                    placeholderTextColor: Theme.faint; color: Theme.text; leftPadding: 11; rightPadding: 11
                    background: Rectangle { color: Theme.bg; radius: 9; border.width: 1; border.color: groupName.activeFocus ? Theme.primary : Theme.stroke }
                }
                PressSurface {
                    Layout.preferredWidth: 104; Layout.preferredHeight: 40; radius: 10
                    color: Theme.cardHi; accentColor: Theme.primary
                    onClicked: multiTargetPicker.saveGroup()
                    Text { anchors.centerIn: parent; text: multiTargetPicker.editingGroupUid ? root.t("Actualizar", "Update") : root.t("Crear grupo", "Create group"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                }
            }
            Text { visible: multiTargetPicker.feedback.length > 0; Layout.fillWidth: true; text: multiTargetPicker.feedback; color: Theme.error; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; wrapMode: Text.Wrap }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                PressSurface {
                    visible: multiTargetPicker.editingGroupUid.length > 0
                    Layout.preferredWidth: visible ? (multiTargetPicker.groupDeletePending ? 160 : 112) : 0
                    Layout.preferredHeight: 38; radius: 10; color: "transparent"; accentColor: Theme.error
                    onClicked: {
                        if (!multiTargetPicker.groupDeletePending) {
                            multiTargetPicker.groupDeletePending = true
                            multiTargetPicker.feedback = root.t("Las rutinas que lo usen quedarán sin destino hasta editarlas.", "Routines using this group will have no target until edited.")
                        } else if (wizz.deleteRoutineGroup(multiTargetPicker.editingGroupUid)) {
                            multiTargetPicker.applySelection()
                        }
                    }
                    Text { anchors.centerIn: parent; text: multiTargetPicker.groupDeletePending ? root.t("Confirmar borrado", "Confirm delete") : root.t("Borrar grupo", "Delete group"); color: Theme.error; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                }
                Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 86; Layout.preferredHeight: 38; radius: 10; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: multiTargetPicker.close(); Text { anchors.centerIn: parent; text: root.t("Cancelar", "Cancel"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize } }
                PressSurface { Layout.preferredWidth: 142; Layout.preferredHeight: 38; radius: 10; color: Theme.primary; accentColor: Theme.primary; onClicked: multiTargetPicker.applySelection(); Text { anchors.centerIn: parent; text: root.t("Usar selección", "Use selection"); color: "white"; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold } }
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
                Text { Layout.fillWidth: true; text: routineValuePicker.stepKind === "rgb" ? root.t("Color de este paso", "Color for this step") : root.t("Blanco de este paso", "White for this step"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 18; font.weight: Font.Bold }
                PressSurface { Layout.preferredWidth: 30; Layout.preferredHeight: 30; radius: 15; color: "transparent"; onClicked: routineValuePicker.close(); AppIcon { anchors.centerIn: parent; width: 13; height: 13; name: "close"; color: Theme.muted } }
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
                Text { anchors.centerIn: parent; text: routineValuePicker.stepKind === "rgb" ? routineValuePicker.stepValue.toUpperCase() : routineValuePicker.stepValue + "K"; color: Qt.color(parent.color).r * .299 + Qt.color(parent.color).g * .587 + Qt.color(parent.color).b * .114 > .72 ? Theme.bg : "white"; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
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
            Text { text: root.t("Eliminar rutina", "Delete routine"); color: Theme.text; font.pixelSize: 21; font.weight: Font.Bold }
            Text { Layout.fillWidth: true; text: root.t("¿Quieres eliminar “", "Do you want to delete “") + root.deletingName + "”?"; color: Theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true; spacing: 10; Item { Layout.fillWidth: true }
                PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 40; radius: 20; color: "transparent"; border.color: Theme.stroke; onClicked: confirmDelete.close(); Text { anchors.centerIn: parent; text: root.t("Cancelar", "Cancel"); color: Theme.text; font.pixelSize: 12 } }
                PressSurface { Layout.preferredWidth: 104; Layout.preferredHeight: 40; radius: 20; color: Theme.error; accentColor: Theme.error; onClicked: { wizz.deleteRoutine(root.deletingUid); confirmDelete.close() } Text { anchors.centerIn: parent; text: root.t("Eliminar", "Delete"); color: "white"; font.pixelSize: 12; font.weight: Font.Bold } }
            }
        }
    }
}
