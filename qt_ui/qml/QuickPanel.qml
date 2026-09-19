pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Window {
    id: panel
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
            if (selected.length === 1)
                return
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

    function reveal() {
        // QScreen's available area is the exact safe area beside the Windows
        // taskbar (even when the taskbar lives on another edge or monitor).
        const area = wizz.quickPanelAvailableArea()
        const areaX = area.x
        const areaY = area.y
        const areaWidth = area.width
        const areaHeight = area.height
        const placement = wizz.quickPanelPlacement
        x = (placement === "bottom-left" || placement === "top-left")
          ? areaX + 8 : areaX + areaWidth - width - 8
        y = (placement === "top-left" || placement === "top-right")
          ? areaY + 8 : areaY + areaHeight - height
        panelShell.opacity = 0
        panelShell.scale = 0.965
        show()
        requestActivate()
        Qt.callLater(function() { panelShell.opacity = 1; panelShell.scale = 1 })
    }

    // A quick panel should behave like a menu, not a second application
    // window.  Clicking elsewhere hands focus back and dismisses it.
    onActiveChanged: if (!active && visible) hide()

    Rectangle {
        id: panelShell
        anchors.fill: parent
        radius: 20
        color: Theme.card
        border.width: 1
        border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.38)
        Behavior on opacity { NumberAnimation { duration: Theme.motionNormal; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: Theme.motionNormal; easing.type: Easing.OutBack } }

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
                    Text { anchors.centerIn: parent; text: "\uEA80"; font.family: Theme.iconFont; font.pixelSize: 19; color: "white" }
                }
                ColumnLayout {
                    spacing: 1
                    Text { text: wizz.language === "en" ? "Quick control" : "Control rápido"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 18; font.weight: Font.DemiBold }
                    Text { text: wizz.language === "en" ? wizz.selectedCount + " lights selected" : wizz.selectedCount + " luces seleccionadas"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11 }
                }
                Item { Layout.fillWidth: true }
                PressSurface {
                    Layout.preferredWidth: 28; Layout.preferredHeight: 28; radius: 14
                    color: "transparent"; accentColor: Theme.primary
                    onClicked: placementPopup.open()
                    Text { anchors.centerIn: parent; text: "\uE713"; color: Theme.muted; font.family: Theme.iconFont; font.pixelSize: 16 }
                }
                PressSurface {
                    Layout.preferredWidth: 28; Layout.preferredHeight: 28; radius: 14
                    color: "transparent"; accentColor: Theme.error
                    onClicked: panel.hide()
                    Text { anchors.centerIn: parent; text: "\uE711"; color: Theme.muted; font.family: Theme.iconFont; font.pixelSize: 15 }
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
                            Text { anchors.centerIn: parent; text: "\uEA80"; color: lightColor; font.family: Theme.iconFont; font.pixelSize: 13 }
                        }
                        Text {
                            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                            anchors.leftMargin: 6; anchors.rightMargin: 6; anchors.bottomMargin: 4
                            text: displayName; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 9; font.weight: Font.DemiBold
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
                            Text { anchors.centerIn: parent; text: index + 1; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 8; font.weight: Font.Bold }
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
                        Text { anchors.centerIn: parent; text: "\uE7E8"; color: Theme.text; font.family: Theme.iconFont; font.pixelSize: 23 }
                    }
                    ColumnLayout {
                        spacing: 2
                        Text { text: wizz.language === "en" ? "Master control" : "Control maestro"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 10 }
                        Text { text: wizz.powerOn ? (wizz.language === "en" ? "ON" : "ENCENDIDO") : (wizz.language === "en" ? "OFF" : "APAGADO"); color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 15; font.weight: Font.Bold }
                    }
                    Item { Layout.fillWidth: true }
                    Text { text: "\uE72A"; color: Theme.accent; font.family: Theme.iconFont; font.pixelSize: 18 }
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
                        Text { text: wizz.language === "en" ? "BRIGHTNESS" : "BRILLO"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11; font.weight: Font.DemiBold }
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
                            Rectangle { width: brightnessSlider.visualPosition * parent.width; height: parent.height; radius: parent.radius; color: Theme.accent }
                        }
                        handle: Rectangle {
                            x: brightnessSlider.leftPadding + brightnessSlider.visualPosition * (brightnessSlider.availableWidth - width)
                            y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2
                            width: 18; height: 18; radius: 9; color: Theme.text
                        }
                    }
                }
            }

            Text { text: wizz.language === "en" ? "QUICK ACTIONS" : "ACCESOS RÁPIDOS"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11; font.weight: Font.DemiBold }
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
                    Text { anchors.left: parent.left; anchors.leftMargin: 11; anchors.verticalCenter: parent.verticalCenter; text: modelData.label; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.DemiBold }
                }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.stroke; opacity: 0.8 }
            PressSurface {
                width: parent.width; height: 36; radius: 9; accentColor: Theme.primary
                onClicked: { placementPopup.close(); quickActionsPopup.open() }
                Text { anchors.centerIn: parent; text: wizz.language === "en" ? "Edit quick actions" : "Editar accesos rápidos"; color: Theme.primary; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold }
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
            Text { text: wizz.language === "en" ? "Choose up to 6. They also appear on Home." : "Elige hasta 6. Se actualizarán también en Inicio."; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 10; wrapMode: Text.WordWrap; width: parent.width }
            Grid {
                width: parent.width; columns: 2; spacing: 6
                Repeater {
                    model: wizz.quickActionCatalog
                    delegate: PressSurface {
                        required property var modelData
                        width: (parent.width - 6) / 2; height: 38; radius: 10
                        selected: panel.quickActionIsSelected(modelData.key)
                        accentColor: modelData.color
                        onClicked: panel.toggleQuickAction(modelData.key)
                        Row {
                            anchors.centerIn: parent; spacing: 6
                            Text { text: modelData.glyph; color: modelData.color; font.family: Theme.iconFont; font.pixelSize: 14 }
                            Text { text: modelData.title; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.DemiBold }
                        }
                    }
                }
            }
        }
    }
}
