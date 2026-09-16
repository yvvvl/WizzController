import QtQuick

PressSurface {
    id: root
    property string glyph: ""
    property string title: ""
    property bool compact: false

    implicitWidth: 80
    implicitHeight: compact ? 54 : 64
    radius: 17
    antialiasing: true
    accentColor: Theme.primary
    showTopHighlight: false
    outlined: false
    color: selected ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.19) : "transparent"
    // Navigation is a rail, not a stack of outlined chips. Selection is
    // communicated by the filled halo and stronger label, which keeps the
    // vertical rhythm clean at every window height.
    border.width: 0

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.compact ? 3 : 5
        width: root.compact ? 48 : 54; height: root.compact ? 33 : 39; radius: 16
        antialiasing: true
        color: root.selected
            ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.14)
            : root.mouseArea.containsMouse
                ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.08)
                : "transparent"
        Behavior on color { ColorAnimation { duration: 220; easing.type: Easing.OutCubic } }
        Text {
            anchors.centerIn: parent
            text: root.glyph
            color: root.selected ? Theme.text : Theme.muted
            font.family: Theme.iconFont
            font.pixelSize: root.compact ? 18 : 20
            Behavior on color { ColorAnimation { duration: 220 } }
        }
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: root.compact ? 5 : 6
        text: root.title
        color: root.selected ? Theme.text : Theme.muted
        font.family: Theme.controlFont
        font.pixelSize: root.compact ? 10 : 11
        font.weight: root.selected ? Font.Bold : Font.DemiBold
        Behavior on color { ColorAnimation { duration: 220 } }
    }
}
