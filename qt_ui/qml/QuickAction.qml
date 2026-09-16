import QtQuick

PressSurface {
    id: root
    property string title: ""
    property string glyph: ""
    property color actionColor: Theme.primary
    implicitWidth: 132
    implicitHeight: 68
    accentColor: actionColor
    radius: 14
    color: Theme.bg

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 8
        width: 30; height: 30; radius: 10
        color: Qt.rgba(root.actionColor.r, root.actionColor.g, root.actionColor.b, 0.15)
        Text {
            anchors.centerIn: parent
            text: root.glyph
            font.family: Theme.iconFont
            font.pixelSize: 16
            color: root.actionColor
        }
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 7
        text: root.title
        color: Theme.text
        font.family: Theme.controlFont
        font.pixelSize: 12
        font.weight: Font.Bold
    }
}
