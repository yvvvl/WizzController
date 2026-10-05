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
        AppIcon {
            anchors.centerIn: parent
            width: 18; height: 18
            glyph: root.glyph
            color: root.actionColor
        }
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 7
        width: parent.width - 12
        text: root.title
        color: Theme.text
        font.family: Theme.controlFont
        font.pixelSize: Theme.labelSize
        font.weight: Font.Bold
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
    }
}
