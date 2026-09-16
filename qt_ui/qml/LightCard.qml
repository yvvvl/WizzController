import QtQuick

PressSurface {
    id: root
    required property string displayName
    required property string address
    required property bool isOn
    required property int brightness
    required property color lightColor
    required property bool isSelected
    selected: isSelected
    implicitHeight: 176
    accentColor: Theme.primary

    Rectangle {
        visible: root.selected
        x: 15; y: 16
        width: 5; height: 24; radius: 3
        color: Theme.primary
    }
    Text {
        x: 31; y: 16
        text: root.selected ? "\uE73E" : "\uE739"
        font.family: Theme.iconFont
        font.pixelSize: 19
        color: root.selected ? Theme.primary : Theme.muted
    }
    Text {
        anchors.right: parent.right
        anchors.rightMargin: 18
        y: 16
        text: root.isOn ? "\uE7E8" : "\uE7E8"
        font.family: Theme.iconFont
        font.pixelSize: 18
        color: root.isOn ? root.lightColor : Theme.muted
    }

    Rectangle {
        x: 31; y: 57
        width: 76; height: 76; radius: 38
        color: root.isOn ? root.lightColor : Theme.faint
        layer.enabled: root.isOn
        Text {
            anchors.centerIn: parent
            text: "\uEA80"
            font.family: Theme.iconFont
            font.pixelSize: 32
            color: "white"
        }
    }
    Column {
        x: 121; y: 78
        spacing: 4
        Text { text: root.displayName; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 15; font.weight: Font.DemiBold }
        Text { text: root.address; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11 }
    }
    Text {
        id: brightnessGlyph
        x: 31; y: 143
        text: "\uE706"
        font.family: Theme.iconFont
        font.pixelSize: 15
        color: Theme.muted
    }
    Rectangle {
        anchors.left: parent.left; anchors.leftMargin: 55
        anchors.right: brightnessValue.left; anchors.rightMargin: 12
        anchors.verticalCenter: brightnessGlyph.verticalCenter
        height: 5; radius: 3
        color: Theme.stroke
        Rectangle { width: parent.width * root.brightness / 100; height: parent.height; radius: parent.radius; color: root.isOn ? root.lightColor : Theme.faint }
    }
    Text {
        id: brightnessValue
        anchors.right: parent.right; anchors.rightMargin: 16; y: 141
        width: 38; horizontalAlignment: Text.AlignRight
        text: root.brightness + "%"
        color: Theme.muted
        font.family: Theme.uiFont
        font.pixelSize: 11
    }
}
