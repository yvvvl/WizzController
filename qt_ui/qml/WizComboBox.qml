import QtQuick
import QtQuick.Controls.Basic

// One themed menu surface for every selector in the desktop shell.  Qt Basic
// otherwise renders the popup with the platform's white fallback palette.
ComboBox {
    id: control
    font.family: Theme.controlFont
    font.pixelSize: Theme.labelSize
    font.weight: Font.DemiBold
    // Opt-in search keeps compact selectors simple while large scene and
    // library catalogues become directly navigable.
    property bool searchable: false
    property string filterText: ""
    onFilterTextChanged: {
        wheelMotion.stop()
        if (popup.visible) filterPositionTimer.restart()
    }
    Timer {
        id: filterPositionTimer
        interval: 0
        onTriggered: {
            if (!control.popup.visible) return
            const selected = !control.filterText.trim() ? control.selectedVisibleIndex() : -1
            optionsView.currentIndex = selected >= 0 ? selected : (optionsView.count ? 0 : -1)
            if (selected >= 0) optionsView.positionViewAtIndex(selected, ListView.Center)
            else optionsView.positionViewAtBeginning()
        }
    }
    readonly property int matchingCount: visibleOptions.length
    // Models that carry this role render a quiet category header before the
    // first matching item. This turns large libraries into a scan-friendly
    // catalogue without changing the compact selector itself.
    property string sectionRole: ""

    function sectionAt(index) {
        if (!sectionRole || !model || index < 0)
            return ""
        const entry = model[index]
        return entry && entry[sectionRole] ? String(entry[sectionRole]) : ""
    }

    function matchesAt(index) {
        if (index < 0 || index >= count) return false
        const query = filterText.trim().toLowerCase()
        return !searchable || !query
            || textAt(index).toLowerCase().indexOf(query) >= 0
            || sectionAt(index).toLowerCase().indexOf(query) >= 0
    }

    readonly property var visibleOptions: {
        // Build a compact model instead of zero-height hidden delegates.  A
        // virtualized ListView cannot reliably calculate off-screen row
        // heights after filtering, which leaves blank space or stale scroll.
        void control.model
        const options = []
        let previousSection = ""
        for (let i = 0; i < control.count; ++i) {
            if (!control.matchesAt(i)) continue
            const section = control.sectionAt(i)
            options.push({ sourceIndex: i, label: control.textAt(i),
                           section: section, beginsSection: !!section && section !== previousSection })
            previousSection = section
        }
        return options
    }

    function selectedVisibleIndex() {
        for (let i = 0; i < visibleOptions.length; ++i)
            if (visibleOptions[i].sourceIndex === currentIndex) return i
        return -1
    }

    function activateVisibleIndex(index) {
        if (index < 0 || index >= visibleOptions.length) return
        const sourceIndex = visibleOptions[index].sourceIndex
        currentIndex = sourceIndex
        activated(sourceIndex)
        popup.close()
    }

    function moveHighlight(direction) {
        if (!visibleOptions.length) return
        optionsView.currentIndex = Math.max(0, Math.min(visibleOptions.length - 1,
                                                       optionsView.currentIndex + direction))
        optionsView.positionViewAtIndex(optionsView.currentIndex, ListView.Contain)
    }

    popup: Popup {
        y: {
            const window = control.Window.window
            if (!window) return control.height + 6
            const top = control.mapToItem(null, 0, 0).y
            const below = window.height - top - control.height - 12
            const above = top - 12
            return below < Math.min(200, implicitHeight) && above > below
                ? -implicitHeight - 6 : control.height + 6
        }
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 12, 350)
        padding: 6
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        onOpened: {
            wheelMotion.stop()
            control.filterText = ""
            filterField.text = ""
            if (control.searchable) filterField.forceActiveFocus()
            else optionsView.forceActiveFocus()
            filterPositionTimer.restart()
        }
        background: Rectangle {
            color: Theme.card
            radius: 12
            border.width: 1
            border.color: Theme.stroke
        }
        contentItem: Column {
            spacing: 6
            TextField {
                id: filterField
                visible: control.searchable
                width: parent.width; height: 34
                placeholderText: wizz.language === "en" ? "Search…" : "Buscar…"; placeholderTextColor: Theme.faint
                color: Theme.text; font: control.font; leftPadding: 10; rightPadding: 10
                onTextEdited: control.filterText = text
                Keys.onDownPressed: (event) => { control.moveHighlight(1); event.accepted = true }
                Keys.onUpPressed: (event) => { control.moveHighlight(-1); event.accepted = true }
                Keys.onReturnPressed: (event) => { control.activateVisibleIndex(optionsView.currentIndex); event.accepted = true }
                Keys.onEnterPressed: (event) => { control.activateVisibleIndex(optionsView.currentIndex); event.accepted = true }
                background: Rectangle { color: Theme.bg; radius: 9; border.width: 1; border.color: filterField.activeFocus ? Theme.primary : Theme.stroke }
            }
            Text {
                visible: control.searchable
                width: parent.width; height: visible ? 16 : 0
                leftPadding: 4
                text: control.matchingCount + (wizz.language === "en" ? " options" : " opciones")
                color: Theme.faint
                font.family: Theme.controlFont
                font.pixelSize: Theme.captionSize
                font.weight: Font.Medium
            }
            ListView {
                id: optionsView
                objectName: "wizzComboOptionsView"
                property real wheelTargetY: 0
                width: parent.width
                height: Math.min(contentHeight, control.searchable ? 262 : 320)
                clip: true
                model: control.popup.visible ? control.visibleOptions : []
                spacing: 0
                boundsBehavior: Flickable.StopAtBounds
                maximumFlickVelocity: 1500
                flickDeceleration: 4200
                onContentYChanged: if (!wheelMotion.running) wheelTargetY = contentY
                onDraggingChanged: if (dragging) { wheelMotion.stop(); wheelTargetY = contentY }
                NumberAnimation {
                    id: wheelMotion
                    target: optionsView
                    property: "contentY"
                    duration: Theme.reduceMotion ? 0 : 170
                    easing.type: Easing.OutCubic
                }
                WheelHandler {
                    target: null
                    acceptedDevices: PointerDevice.Mouse
                    onWheel: (event) => {
                        const maximum = Math.max(0, optionsView.contentHeight - optionsView.height)
                        if (maximum <= 0) { event.accepted = true; return }
                        const step = event.angleDelta.y / 120 * 72
                        const next = Math.max(0, Math.min(maximum, optionsView.wheelTargetY - step))
                        wheelMotion.stop()
                        optionsView.wheelTargetY = next
                        wheelMotion.from = optionsView.contentY
                        wheelMotion.to = next
                        wheelMotion.start()
                        event.accepted = true
                    }
                }
                Keys.onDownPressed: (event) => { control.moveHighlight(1); event.accepted = true }
                Keys.onUpPressed: (event) => { control.moveHighlight(-1); event.accepted = true }
                Keys.onReturnPressed: (event) => { control.activateVisibleIndex(currentIndex); event.accepted = true }
                Keys.onEnterPressed: (event) => { control.activateVisibleIndex(currentIndex); event.accepted = true }
                delegate: ItemDelegate {
                    id: optionDelegate
                    required property int index
                    required property var modelData
                    width: ListView.view.width
                    height: 43 + (modelData.beginsSection ? 25 : 0)
                    padding: 0
                    onClicked: control.activateVisibleIndex(index)
                    contentItem: Item {
                        Text {
                            visible: optionDelegate.modelData.beginsSection
                            x: 13; y: 1; width: parent.width - 26; height: 23
                            text: optionDelegate.modelData.section.toUpperCase()
                            color: Theme.primary
                            font.family: Theme.controlFont
                            font.pixelSize: Theme.captionSize
                            font.weight: Font.Bold
                            font.letterSpacing: 0.7
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        Rectangle {
                            x: 3; y: optionDelegate.modelData.beginsSection ? 25 : 2
                            width: parent.width - 6; height: 38; radius: 9
                            color: optionDelegate.modelData.sourceIndex === control.currentIndex
                                ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.22)
                                : optionDelegate.index === optionsView.currentIndex
                                    ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.11)
                                    : optionDelegate.hovered ? Theme.cardHi : "transparent"
                            Text {
                                anchors.left: parent.left; anchors.leftMargin: 12
                                anchors.right: selectedMark.left; anchors.rightMargin: 8
                                height: parent.height
                                text: optionDelegate.modelData.label
                                color: Theme.text
                                font.family: control.font.family
                                font.pixelSize: control.font.pixelSize + 1
                                font.weight: optionDelegate.modelData.sourceIndex === control.currentIndex ? Font.Bold : Font.DemiBold
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                            Text {
                                id: selectedMark
                                anchors.right: parent.right; anchors.rightMargin: 12
                                height: parent.height
                                visible: optionDelegate.modelData.sourceIndex === control.currentIndex
                                text: "✓"
                                color: Theme.primary
                                font.family: Theme.controlFont
                                font.pixelSize: Theme.labelSize
                                font.weight: Font.Bold
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                    background: Item { }
                }
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    implicitWidth: 9
                    opacity: active || hovered || pressed ? 1 : 0.45
                    Behavior on opacity { NumberAnimation { duration: Theme.motionFast } }
                    background: Rectangle { implicitWidth: 9; radius: 5; color: Qt.rgba(Theme.text.r, Theme.text.g, Theme.text.b, 0.05) }
                    contentItem: Rectangle {
                        implicitWidth: 7; radius: 4
                        color: parent.hovered || parent.pressed ? Theme.primary : Theme.muted
                        Behavior on color { ColorAnimation { duration: Theme.motionFast } }
                    }
                }
            }
            Text {
                visible: control.searchable && control.matchingCount === 0
                width: parent.width; height: visible ? 44 : 0
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                text: wizz.language === "en" ? "No matching options" : "No hay coincidencias"
                color: Theme.muted
                font.family: Theme.controlFont
                font.pixelSize: Theme.labelSize
            }
        }
    }
}
