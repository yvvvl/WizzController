import QtQuick
import QtQuick.Controls.Basic

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
    AppIcon {
        x: 31; y: 16
        width: 19; height: 19
        name: root.selected ? "check" : "circle"
        color: root.selected ? Theme.primary : Theme.muted
    }
    AppIcon {
        anchors.right: parent.right
        anchors.rightMargin: 18
        y: 16
        width: 18; height: 18
        name: "power"
        color: root.isOn ? root.lightColor : Theme.muted
    }

    Rectangle {
        x: 31; y: 57
        width: 76; height: 76; radius: 38
        color: root.isOn ? root.lightColor : Theme.faint
        layer.enabled: root.isOn
        BulbIcon {
            anchors.centerIn: parent
            width: 40; height: 40
            iconColor: "white"
        }
    }
    Column {
        x: 121; y: 78
        spacing: 4
        Text { width: Math.max(0, root.width - 137); text: root.displayName; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 16; font.weight: Font.Bold; elide: Text.ElideRight }
        Text { text: root.address; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize }
    }
    AppIcon {
        id: brightnessGlyph
        x: 31; y: 143
        width: 15; height: 15
        name: "sun"
        color: Theme.muted
    }
    Slider {
        id: individualBrightness
        anchors.left: parent.left; anchors.leftMargin: 55
        anchors.right: brightnessValue.left; anchors.rightMargin: 12
        anchors.verticalCenter: brightnessGlyph.verticalCenter
        height: 24
        from: 10; to: 100; value: root.brightness
        onMoved: wizz.queueLightBrightness(root.address, Math.round(value))
        background: Rectangle {
            x: individualBrightness.leftPadding
            y: individualBrightness.topPadding + individualBrightness.availableHeight / 2 - height / 2
            width: individualBrightness.availableWidth; height: 5; radius: 3; color: Theme.stroke
            Rectangle { width: individualBrightness.visualPosition * parent.width; height: parent.height; radius: parent.radius; color: Theme.primary }
        }
        handle: Rectangle {
            x: individualBrightness.leftPadding + individualBrightness.visualPosition * (individualBrightness.availableWidth - width)
            y: individualBrightness.topPadding + individualBrightness.availableHeight / 2 - height / 2
            width: 16; height: 16; radius: 8; color: Theme.text
            border.width: individualBrightness.pressed ? 2 : 0; border.color: Theme.primary
            Behavior on scale { NumberAnimation { duration: Theme.motionPress; easing.type: Easing.OutCubic } }
            scale: individualBrightness.pressed ? 1.12 : 1
        }
    }
    Text {
        id: brightnessValue
        anchors.right: parent.right; anchors.rightMargin: 16; y: 141
        width: 38; horizontalAlignment: Text.AlignRight
        text: root.brightness + "%"
        color: Theme.muted
        font.family: Theme.uiFont
        font.pixelSize: Theme.labelSize
        font.weight: Font.DemiBold
    }
}
