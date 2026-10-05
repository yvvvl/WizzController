pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Window {
    id: panel
    // This popup is opened directly from the system tray while the main
    // window may be hidden. A nested Window otherwise inherits the main
    // window as transientParent and the window manager keeps it hidden.
    transientParent: null
    width: 368
    height: 480
    minimumWidth: 368
    maximumWidth: 368
    minimumHeight: 480
    maximumHeight: 480
    visible: false
    color: "transparent"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    title: "WizZ Quick Panel"
    property var ownerWindow: null
    property bool savePositionAfterDrag: false

    Timer {
        id: deactivateHideTimer
        interval: 400
        repeat: false
        onTriggered: {
            if (!panel.active && panel.visible && !panel.savePositionAfterDrag)
                panel.hide()
        }
    }

    function selectedQuickActionKeys() {
        const selected = []
        const actions = wizz.quickActions
        for (let index = 0; index < actions.length; ++index)
            selected.push(actions[index].key)
        return selected
    }

    function quickActionIsSelected(key) {
        const selected = selectedQuickActionKeys()
        return selected.indexOf(key) !== -1
    }

    function toggleQuickAction(key) {
        const selected = selectedQuickActionKeys()
        const index = selected.indexOf(key)
        if (index !== -1) {
            selected.splice(index, 1)
        } else {
            if (selected.length === 6)
                return
            selected.push(key)
        }
        wizz.setQuickActions(selected)
    }

    function showLightPage(page) {
        const maximum = Math.max(0, lightCarousel.contentWidth - lightCarousel.width)
        lightCarousel.contentX = Math.min(page * lightCarousel.width, maximum)
    }

    function finishDrag() {
        const area = wizz.quickPanelAvailableArea()
        const margin = 8
        const snapDistance = 32
        const minX = area.x + margin
        const minY = area.y + margin
        const maxX = Math.max(minX, area.x + area.width - width - margin)
        const maxY = Math.max(minY, area.y + area.height - height - margin)
        let nextX = Math.max(minX, Math.min(maxX, panel.x))
        let nextY = Math.max(minY, Math.min(maxY, panel.y))

        const distances = [
            { edge: "left", distance: Math.abs(nextX - minX) },
            { edge: "right", distance: Math.abs(maxX - nextX) },
            { edge: "top", distance: Math.abs(nextY - minY) },
            { edge: "bottom", distance: Math.abs(maxY - nextY) }
        ]
        let closest = distances[0]
        for (let index = 1; index < distances.length; ++index) {
            if (distances[index].distance < closest.distance)
                closest = distances[index]
        }
        if (closest.distance <= snapDistance) {
            if (closest.edge === "left") nextX = minX
            else if (closest.edge === "right") nextX = maxX
            else if (closest.edge === "top") nextY = minY
            else nextY = maxY
        }

        panel.x = nextX
        panel.y = nextY
        if (wizz.quickPanelCanRememberPosition)
            wizz.saveQuickPanelPosition(Math.round(nextX), Math.round(nextY))
    }

    function reveal() {
        // Use the native tray icon to identify the monitor and dock edge when
        // the desktop exposes it. QScreen's available area keeps the panel
        // beside the taskbar/dock and inside the work area.
        const area = wizz.quickPanelAvailableArea()
        const areaX = area.x
        const areaY = area.y
        const areaWidth = area.width
        const areaHeight = area.height
        const placement = wizz.quickPanelPlacement
        const maxX = areaX + Math.max(0, areaWidth - width)
        const maxY = areaY + Math.max(0, areaHeight - height)
        const savedPosition = wizz.quickPanelSavedPosition()
        if (wizz.quickPanelCanRememberPosition && savedPosition.valid) {
            x = Math.max(areaX + 8, Math.min(maxX - 8, savedPosition.x))
            y = Math.max(areaY + 8, Math.min(maxY - 8, savedPosition.y))
        } else if (area.edge === "top" || area.edge === "bottom") {
            const anchorX = area.tray_x + area.tray_width / 2
            x = Math.max(areaX + 8, Math.min(maxX - 8, anchorX - width / 2))
            y = area.edge === "top" ? areaY + 8 : maxY - 8
        } else if (area.edge === "left" || area.edge === "right") {
            const anchorY = area.tray_y + area.tray_height / 2
            x = area.edge === "left" ? areaX + 8 : maxX - 8
            y = Math.max(areaY + 8, Math.min(maxY - 8, anchorY - height / 2))
        } else {
            // Fallback for desktops (such as Wayland sessions) that don't
            // provide tray icon coordinates to Qt.
            x = (placement === "bottom-left" || placement === "top-left")
              ? areaX + 8 : maxX - 8
            y = (placement === "top-left" || placement === "top-right")
              ? areaY + 8 : maxY - 8
        }
        panelShell.opacity = 0
        panelShell.scale = 0.965
        show()
        requestActivate()
        Qt.callLater(function() { panelShell.opacity = 1; panelShell.scale = 1 })
    }

    function showMainApp() {
        placementPopup.close()
        panel.hide()
        if (ownerWindow) {
            ownerWindow.showNormal()
            ownerWindow.raise()
            ownerWindow.requestActivate()
        }
    }

    function quitApp() {
        placementPopup.close()
        panel.hide()
        wizz.quitApplication()
    }

    // A quick panel should behave like a menu, not a second application
    // window.  Clicking elsewhere hands focus back and dismisses it.
    onActiveChanged: {
        // Allow the pointer press to cross DragHandler's drag threshold before
        // dismissing on focus loss. System moves can also deactivate the window.
        if (active)
            deactivateHideTimer.stop()
        else if (visible)
            deactivateHideTimer.restart()
    }

    Rectangle {
        id: panelShell
        anchors.fill: parent
        radius: 20
        color: Theme.card
        border.width: 1
        border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.38)
        Behavior on opacity { NumberAnimation { duration: Theme.motionNormal; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: Theme.motionNormal; easing.type: Easing.OutCubic } }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Rectangle {
                    Layout.preferredWidth: 38; Layout.preferredHeight: 38; radius: 13
                    color: Theme.primary
                    AppIcon { anchors.centerIn: parent; width: 20; height: 20; name: "bulb"; color: "white" }
                }
                ColumnLayout {
                    spacing: 1
                    Text { text: wizz.language === "en" ? "Quick control" : "Control rápido"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 18; font.weight: Font.Bold }
                    Text { text: wizz.language === "en" ? wizz.selectedCount + " lights selected" : wizz.selectedCount + " luces seleccionadas"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize }
                }
                Item {
                    id: dragHandle
                    Layout.preferredWidth: 22; Layout.preferredHeight: 34
                    ToolTip.visible: dragHover.hovered
                    ToolTip.delay: 650
                    ToolTip.text: wizz.language === "en" ? "Drag to move" : "Arrastra para mover"
                    Column {
                        anchors.centerIn: parent
                        spacing: 3
                        Repeater {
                            model: 3
                            delegate: Row {
                                required property int index
                                spacing: 3
                                Repeater {
                                    model: 2
                                    delegate: Rectangle {
                                        width: 3; height: 3; radius: 2
                                        color: dragHover.hovered ? Theme.text : Theme.faint
                                    }
                                }
                            }
                        }
                    }
                    HoverHandler { id: dragHover }
                    DragHandler {
                        target: null
                        acceptedButtons: Qt.LeftButton
                        onActiveChanged: {
                            if (active) {
                                deactivateHideTimer.stop()
                                panel.savePositionAfterDrag = true
                                panel.startSystemMove()
                            } else if (panel.savePositionAfterDrag) {
                                panel.savePositionAfterDrag = false
                                panel.finishDrag()
                                // Native system moves can make the panel lose
                                // activation; restart dismissal once dragging
                                // ends instead of leaving it stuck open.
                                if (!panel.active)
                                    deactivateHideTimer.restart()
                            }
                        }
                    }
                }
                Item { Layout.fillWidth: true }
                PressSurface {
                    Layout.preferredWidth: 28; Layout.preferredHeight: 28; radius: 14
                    color: "transparent"; accentColor: Theme.primary
                    onClicked: placementPopup.open()
                    AppIcon { anchors.centerIn: parent; width: 15; height: 15; name: "settings"; color: Theme.muted }
                }
                PressSurface {
                    Layout.preferredWidth: 28; Layout.preferredHeight: 28; radius: 14
                    color: "transparent"; accentColor: Theme.error
                    onClicked: panel.hide()
                    AppIcon { anchors.centerIn: parent; width: 13; height: 13; name: "close"; color: Theme.muted }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 82
                radius: 14
                color: Theme.bg
                border.width: 1
                border.color: Theme.stroke
                ListView {
                    id: lightCarousel
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom
                    anchors.margins: 7; anchors.topMargin: 27
                    clip: true; orientation: ListView.Horizontal; spacing: 6
                    boundsBehavior: Flickable.StopAtBounds
                    model: wizz.lightModel
                    ScrollIndicator.horizontal: ScrollIndicator { }
                    delegate: PressSurface {
                        required property string displayName
                        required property string address
                        required property color lightColor
                        required property bool isSelected
                        required property bool isOnline
                        width: Math.max(94, (lightCarousel.width - 12) / 3)
                        height: lightCarousel.height
                        radius: 11
                        selected: isSelected
                        accentColor: isSelected ? lightColor : Theme.primary
                        color: isSelected ? Qt.rgba(lightColor.r, lightColor.g, lightColor.b, 0.14) : Theme.card
                        onClicked: wizz.toggleLight(address)
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter; y: 4
                            width: 20; height: 20; radius: 10
                            color: Qt.rgba(lightColor.r, lightColor.g, lightColor.b, isOnline ? 0.22 : 0.10)
                            border.width: isSelected ? 1 : 0
                            border.color: lightColor
                            AppIcon { anchors.centerIn: parent; width: 13; height: 13; name: "bulb"; color: lightColor }
                        }
                        Text {
                            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                            anchors.leftMargin: 6; anchors.rightMargin: 6; anchors.bottomMargin: 4
                            text: displayName; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold
                            horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight
                        }
                    }
                }
                Row {
                    id: carouselPages
                    anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.topMargin: 6
                    spacing: 4
                    Repeater {
                        model: Math.ceil(lightCarousel.count / 3)
                        delegate: PressSurface {
                            required property int index
                            width: 22; height: 15; radius: 7
                            selected: Math.floor((lightCarousel.contentX + lightCarousel.width / 2) / lightCarousel.width) === index
                            accentColor: Theme.primary
                            onClicked: panel.showLightPage(index)
                            Text { anchors.centerIn: parent; text: index + 1; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                        }
                    }
                }
            }

            PressSurface {
                Layout.fillWidth: true
                Layout.preferredHeight: 62
                accentColor: Theme.primary
                radius: 14
                color: Theme.bg
                onClicked: wizz.toggleMaster()
                RowLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 10
                    Rectangle {
                        Layout.preferredWidth: 38; Layout.preferredHeight: 38; radius: 12
                        color: wizz.powerOn ? Theme.primary : Theme.cardHi
                        AppIcon { anchors.centerIn: parent; width: 22; height: 22; name: "power"; color: Theme.text }
                    }
                    ColumnLayout {
                        spacing: 2
                        Text { text: wizz.language === "en" ? "Master control" : "Control maestro"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize }
                        Text { text: wizz.powerOn ? (wizz.language === "en" ? "ON" : "ENCENDIDO") : (wizz.language === "en" ? "OFF" : "APAGADO"); color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 15; font.weight: Theme.stateWeight }
                    }
                    Item { Layout.fillWidth: true }
                    AppIcon { Layout.preferredWidth: 18; Layout.preferredHeight: 18; name: "arrowRight"; color: Theme.accent }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 72
                radius: 14
                color: Theme.bg
                border.width: 1
                border.color: Theme.stroke
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 4
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: wizz.language === "en" ? "BRIGHTNESS" : "BRILLO"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
                        Item { Layout.fillWidth: true }
                        Text { text: Math.round(brightnessSlider.value) + "%"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 13; font.weight: Font.DemiBold }
                    }
                    Slider {
                        id: brightnessSlider
                        Layout.fillWidth: true
                        from: 10; to: 100; value: wizz.brightness
                        onMoved: wizz.queueBrightness(Math.round(value))
                        background: Rectangle {
                            x: brightnessSlider.leftPadding
                            y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2
                            width: brightnessSlider.availableWidth; height: 5; radius: 3; color: Theme.stroke
                            Rectangle { width: brightnessSlider.visualPosition * parent.width; height: parent.height; radius: parent.radius; color: Theme.primary }
                        }
                        handle: Rectangle {
                            x: brightnessSlider.leftPadding + brightnessSlider.visualPosition * (brightnessSlider.availableWidth - width)
                            y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2
                            width: 18; height: 18; radius: 9; color: Theme.text
                        }
                    }
                }
            }

            Text { text: wizz.language === "en" ? "QUICK ACTIONS" : "ACCESOS RÁPIDOS"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
            Text { visible: wizz.quickActions.length === 0; text: wizz.language === "en" ? "Choose actions from the menu above." : "Elige acciones en el menú superior."; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize }
            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 8; rowSpacing: 8
                Repeater {
                    model: wizz.quickActions
                    delegate: QuickAction {
                        required property var modelData
                        Layout.fillWidth: true
                        title: modelData.title; glyph: modelData.glyph; actionColor: modelData.color
                        onClicked: wizz.applyQuick(modelData.key)
                    }
                }
            }
            Item { Layout.fillHeight: true }
        }
    }

    Popup {
        id: placementPopup
        x: panel.width - width - 16; y: 52; width: 224; padding: 7
        modal: false; focus: true; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: Theme.card; radius: 13; border.width: 1; border.color: Theme.stroke }
        contentItem: Column {
            spacing: 3
            Repeater {
                model: [
                    {id:"bottom-right", label: wizz.language === "en" ? "Bottom right" : "Inferior derecha"}, {id:"bottom-left", label: wizz.language === "en" ? "Bottom left" : "Inferior izquierda"},
                    {id:"top-right", label: wizz.language === "en" ? "Top right" : "Superior derecha"}, {id:"top-left", label: wizz.language === "en" ? "Top left" : "Superior izquierda"}
                ]
                delegate: PressSurface {
                    required property var modelData
                    width: parent.width; height: 34; radius: 9; selected: wizz.quickPanelPlacement === modelData.id
                    accentColor: Theme.primary
                    onClicked: { wizz.setQuickPanelPlacement(modelData.id); placementPopup.close(); panel.reveal() }
                    Text { anchors.left: parent.left; anchors.leftMargin: 11; anchors.verticalCenter: parent.verticalCenter; text: modelData.label; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
                }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.stroke; opacity: 0.8 }
            PressSurface {
                width: parent.width; height: 36; radius: 9; accentColor: Theme.primary
                onClicked: { placementPopup.close(); quickActionsPopup.open() }
                Text { anchors.centerIn: parent; text: wizz.language === "en" ? "Edit quick actions" : "Editar accesos rápidos"; color: Theme.primary; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
            }
            PressSurface {
                width: parent.width; height: 36; radius: 9; accentColor: Theme.primary
                onClicked: panel.showMainApp()
                Text { anchors.centerIn: parent; text: wizz.language === "en" ? "Open WizZ Desktop" : "Abrir WizZ Desktop"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
            }
            PressSurface {
                width: parent.width; height: 36; radius: 9; accentColor: Theme.error
                onClicked: panel.quitApp()
                Text { anchors.centerIn: parent; text: wizz.language === "en" ? "Quit WizZ Desktop" : "Salir de WizZ Desktop"; color: Theme.error; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
            }
        }
    }

    Popup {
        id: quickActionsPopup
        x: 16; y: 52; width: panel.width - 32; padding: 12
        modal: false; focus: true; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: Theme.card; radius: 14; border.width: 1; border.color: Theme.stroke }
        contentItem: Column {
            spacing: 8
            Text { text: wizz.language === "en" ? "QUICK ACTIONS" : "ACCESOS RÁPIDOS"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 13; font.weight: Font.Bold }
            Text { text: wizz.language === "en" ? "Choose up to 6. They also appear on Home." : "Elige hasta 6. Se actualizarán también en Inicio."; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; wrapMode: Text.WordWrap; width: parent.width }
            Flickable {
                id: quickCatalogScroll
                width: parent.width
                height: Math.min(282, quickCatalogGrid.implicitHeight)
                contentWidth: width; contentHeight: quickCatalogGrid.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    width: 5
                    contentItem: Rectangle { radius: 3; color: Theme.muted; opacity: 0.55 }
                    background: Item {}
                }
                Grid {
                    id: quickCatalogGrid
                    width: quickCatalogScroll.width; columns: 2; spacing: 6
                    Repeater {
                        model: wizz.quickActionCatalog
                        delegate: PressSurface {
                            required property var modelData
                            width: (quickCatalogGrid.width - 6) / 2; height: 38; radius: 10
                            selected: panel.quickActionIsSelected(modelData.key)
                            accentColor: modelData.color
                            onClicked: panel.toggleQuickAction(modelData.key)
                            Row {
                                anchors.centerIn: parent; spacing: 6
                                AppIcon { width: 14; height: 14; glyph: modelData.glyph; color: modelData.color }
                                Text { text: modelData.title; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold; width: 116; elide: Text.ElideRight }
                            }
                        }
                    }
                }
            }
            PressSurface {
                width: parent.width; height: 35; radius: 10
                color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary
                onClicked: {
                    quickActionsPopup.close()
                    panel.showMainApp()
                    if (panel.ownerWindow) panel.ownerWindow.navigateTo(5)
                }
                Text { anchors.centerIn: parent; text: wizz.language === "en" ? "+ Create / edit custom actions" : "+ Crear / editar acciones propias"; color: Theme.primary; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold }
            }
        }
    }
}
